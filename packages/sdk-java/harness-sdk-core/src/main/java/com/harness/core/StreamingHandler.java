package com.harness.core;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Consumer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.types.Chunk;
import com.harness.types.ChunkType;
import com.harness.types.ProgressEvent;
import com.harness.types.ProgressEventType;

/**
 * Handles streaming output with buffer management and backpressure control.
 *
 * Features:
 * - Buffer management with configurable size
 * - Backpressure detection and handling
 * - Progress event emission on backpressure
 * - Support for different chunk types
 *
 * Example:
 * <pre>
 * StreamingHandler handler = new StreamingHandler();
 *
 * // Process chunks
 * for (Chunk chunk : chunks) {
 *     handler.handle(chunk);
 *     if (handler.shouldPause()) {
 *         Thread.sleep(100);
 *     }
 * }
 *
 * String content = handler.getFullContent();
 * </pre>
 */
public class StreamingHandler {

    private static final Logger logger = LoggerFactory.getLogger(StreamingHandler.class);

    private final StreamingConfig config;
    private final Consumer<ProgressEvent> onProgress;
    private final Consumer<Chunk> onChunk;

    // Buffer for chunks
    private final List<Chunk> buffer;
    private int bufferStart = 0;

    // State
    private boolean isPaused = false;
    private final StreamingStats stats = new StreamingStats();

    // Accumulated content
    private final StringBuilder textContent = new StringBuilder();
    private final Map<String, Map<String, Object>> toolCalls = new LinkedHashMap<>();

    public StreamingHandler() {
        this(StreamingConfig.defaults(), null, null);
    }

    public StreamingHandler(StreamingConfig config) {
        this(config, null, null);
    }

    public StreamingHandler(StreamingConfig config, Consumer<ProgressEvent> onProgress, Consumer<Chunk> onChunk) {
        this.config = config;
        this.onProgress = onProgress;
        this.onChunk = onChunk;
        this.buffer = new ArrayList<>(config.bufferSize());
    }

    /**
     * Get current buffer size.
     */
    public int getBufferSize() {
        return buffer.size() - bufferStart;
    }

    /**
     * Get buffer usage ratio (0.0 to 1.0).
     */
    public double getBufferUsage() {
        return (double) getBufferSize() / config.bufferSize();
    }

    /**
     * Check if upstream should pause due to backpressure.
     */
    public boolean shouldPause() {
        return isPaused || getBufferUsage() >= config.backpressureThreshold();
    }

    /**
     * Get streaming statistics.
     */
    public StreamingStats getStats() {
        return stats;
    }

    /**
     * Handle an incoming chunk.
     */
    public void handle(Chunk chunk) {
        stats.incrementChunksReceived();

        // Add to buffer
        buffer.add(chunk);

        // Update high watermark
        stats.updateHighWatermark(getBufferSize());

        // Process chunk
        processChunk(chunk);

        // Call custom handler
        if (onChunk != null) {
            onChunk.accept(chunk);
        }

        stats.incrementChunksProcessed();
    }

    /**
     * Apply backpressure by pausing.
     * In Java, this is a blocking call - use carefully.
     */
    public void applyBackpressure() {
        isPaused = true;
        stats.incrementBackpressureEvents();

        // Emit progress event
        if (onProgress != null) {
            onProgress.accept(ProgressEvent.of(
                ProgressEventType.STREAM_BACKPRESSURE,
                String.format("Backpressure applied: buffer at %.0f%%", getBufferUsage() * 100),
                Map.of(
                    "bufferSize", getBufferSize(),
                    "bufferMax", config.bufferSize(),
                    "usage", getBufferUsage()
                )
            ));
        }

        // Wait for buffer to drain
        long pauseStart = System.currentTimeMillis();

        while (getBufferUsage() > config.backpressureThreshold() * 0.5) {
            try {
                Thread.sleep(10);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }

            // Check max pause duration
            long elapsed = System.currentTimeMillis() - pauseStart;
            if (elapsed > config.maxPauseDuration() * 1000) {
                logger.warn("Max pause duration exceeded, resuming");
                break;
            }
        }

        double pauseTime = (System.currentTimeMillis() - pauseStart) / 1000.0;
        stats.addPauseTime(pauseTime);
        isPaused = false;
    }

    /**
     * Get accumulated text content.
     */
    public String getFullContent() {
        return textContent.toString();
    }

    /**
     * Get accumulated tool calls.
     */
    public List<Map<String, Object>> getToolCalls() {
        List<Map<String, Object>> result = new ArrayList<>();
        for (Map.Entry<String, Map<String, Object>> entry : toolCalls.entrySet()) {
            Map<String, Object> toolCall = new HashMap<>();
            toolCall.put("id", entry.getKey());
            toolCall.putAll(entry.getValue());
            result.add(toolCall);
        }
        return result;
    }

    /**
     * Clear buffer and accumulated content.
     */
    public void clear() {
        buffer.clear();
        bufferStart = 0;
        textContent.setLength(0);
        toolCalls.clear();
        isPaused = false;
    }

    /**
     * Check if currently paused.
     */
    public boolean isPaused() {
        return isPaused;
    }

    // === Private Methods ===

    private void processChunk(Chunk chunk) {
        if (chunk.type() == ChunkType.TEXT) {
            if (chunk.content() != null) {
                textContent.append(chunk.content());
            }
        } else if (chunk.type() == ChunkType.TOOL_CALL_START) {
            String id = chunk.toolCallId() != null ? chunk.toolCallId() : "";
            Map<String, Object> toolCall = new HashMap<>();
            toolCall.put("name", chunk.toolName());
            toolCall.put("arguments", new HashMap<String, Object>());
            toolCalls.put(id, toolCall);
        } else if (chunk.type() == ChunkType.TOOL_CALL_DELTA) {
            String id = chunk.toolCallId();
            if (id != null && toolCalls.containsKey(id)) {
                @SuppressWarnings("unchecked")
                Map<String, Object> args = (Map<String, Object>) toolCalls.get(id).get("arguments");
                if (args != null && chunk.toolArguments() != null) {
                    args.putAll(chunk.toolArguments());
                }
            }
        } else if (chunk.type() == ChunkType.ERROR) {
            logger.error("Stream error: {}", chunk.content());
        }
    }

    @Override
    public String toString() {
        return String.format("<StreamingHandler buffer=%d/%d usage=%.0f%%>",
            getBufferSize(), config.bufferSize(), getBufferUsage() * 100);
    }
}
