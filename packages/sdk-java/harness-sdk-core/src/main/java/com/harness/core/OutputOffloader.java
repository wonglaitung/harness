package com.harness.core;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.types.ToolResult;

/**
 * Manages offloading of large tool outputs to temporary files.
 *
 * When tool outputs are too large, they are offloaded to temporary files
 * to keep context windows manageable. The context retains a summary/reference
 * instead of the full content.
 *
 * Example:
 * <pre>
 * OutputOffloader offloader = new OutputOffloader(config);
 *
 * if (offloader.shouldOffload(content, sessionId)) {
 *     OffloadedOutput offloaded = offloader.offload(content, "read", toolCallId, sessionId);
 *     String reference = offloaded.getReferenceString();
 * }
 * </pre>
 */
public class OutputOffloader {

    private static final Logger logger = LoggerFactory.getLogger(OutputOffloader.class);

    private final OffloadConfig config;
    private final Path tempDir;

    // Track offloaded outputs per session
    private final Map<String, java.util.List<OffloadedOutput>> sessionOutputs = new ConcurrentHashMap<>();
    private int totalOutputs = 0;

    public OutputOffloader() {
        this(OffloadConfig.defaults());
    }

    public OutputOffloader(OffloadConfig config) {
        this.config = config;
        this.tempDir = config.tempDir() != null
            ? config.tempDir()
            : Path.of(System.getProperty("user.dir")).resolve(".harness").resolve("offload");

        try {
            Files.createDirectories(tempDir);
        } catch (Exception e) {
            logger.warn("Failed to create offload directory: {}", e.getMessage());
        }
    }

    /**
     * Check if content should be offloaded.
     */
    public boolean shouldOffload(String content, String sessionId) {
        if (content == null || content.isEmpty()) {
            return false;
        }

        int size = content.length();

        // Check size threshold
        if (size < config.sizeThresholdChars()) {
            return false;
        }

        // Check session limit
        java.util.List<OffloadedOutput> outputs = sessionOutputs.get(sessionId);
        int sessionCount = outputs != null ? outputs.size() : 0;
        if (sessionCount >= config.maxOutputsPerSession()) {
            logger.warn("Session {} has reached max outputs limit ({})", sessionId, config.maxOutputsPerSession());
            return false;
        }

        return true;
    }

    /**
     * Offload content to a temporary file.
     */
    public OffloadedOutput offload(String content, String toolName, String toolCallId, String sessionId) {
        return offload(content, toolName, toolCallId, sessionId, null);
    }

    /**
     * Offload content to a temporary file.
     */
    public OffloadedOutput offload(String content, String toolName, String toolCallId, String sessionId, String summary) {
        // Generate unique filename
        String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
        String filename = String.format("%s_%s_%s_%s.txt",
            sanitizeFilename(sessionId),
            sanitizeFilename(toolName),
            sanitizeFilename(toolCallId),
            timestamp);

        Path filePath = tempDir.resolve(filename);

        try {
            Files.writeString(filePath, content);
        } catch (Exception e) {
            logger.error("Failed to write offload file: {}", e.getMessage());
            throw new RuntimeException("Failed to offload content", e);
        }

        // Extract preview
        int previewLen = Math.min(config.previewLength(), content.length());
        String preview = content.substring(0, previewLen);
        if (content.length() > config.previewLength()) {
            preview += "...";
        }

        // Create record
        OffloadedOutput output = new OffloadedOutput(
            filePath,
            toolName,
            toolCallId,
            content.length(),
            preview,
            summary,
            LocalDateTime.now(),
            sessionId != null ? sessionId : ""
        );

        // Track output
        sessionOutputs.computeIfAbsent(sessionId, k -> new java.util.ArrayList<>()).add(output);
        totalOutputs++;

        logger.info("Offloaded {} chars from {} to {}", content.length(), toolName, filePath);

        return output;
    }

    /**
     * Create a ToolResult with offloaded content reference.
     */
    public ToolResult createOffloadedResult(ToolResult originalResult, String sessionId) {
        if (originalResult.content() == null || originalResult.content().isEmpty()) {
            return originalResult;
        }

        OffloadedOutput offloaded = offload(
            originalResult.content(),
            originalResult.toolName() != null ? originalResult.toolName() : "unknown",
            originalResult.toolCallId(),
            sessionId,
            null
        );

        return new ToolResult(
            originalResult.toolCallId(),
            originalResult.success(),
            offloaded.getReferenceString(),
            originalResult.error(),
            Map.of(
                "offloaded", true,
                "offload_path", offloaded.filePath().toString(),
                "original_size", offloaded.originalSize()
            )
        );
    }

    /**
     * Load content from an offloaded file.
     */
    public String loadOffloaded(Path filePath) {
        try {
            return Files.readString(filePath);
        } catch (Exception e) {
            throw new RuntimeException("Failed to read offloaded file: " + filePath, e);
        }
    }

    /**
     * Clean up all offloaded outputs for a session.
     */
    public int cleanupSession(String sessionId) {
        java.util.List<OffloadedOutput> outputs = sessionOutputs.remove(sessionId);
        if (outputs == null) {
            return 0;
        }

        int deleted = 0;
        for (OffloadedOutput output : outputs) {
            try {
                if (Files.exists(output.filePath())) {
                    Files.delete(output.filePath());
                    deleted++;
                }
            } catch (Exception e) {
                logger.warn("Failed to delete {}: {}", output.filePath(), e.getMessage());
            }
        }

        logger.info("Cleaned up {} offloaded files for session {}", deleted, sessionId);
        return deleted;
    }

    /**
     * Clean up all offloaded outputs.
     */
    public int cleanupAll() {
        int deleted = 0;
        for (String sessionId : java.util.List.copyOf(sessionOutputs.keySet())) {
            deleted += cleanupSession(sessionId);
        }
        return deleted;
    }

    /**
     * Get offloader statistics.
     */
    public Map<String, Object> getStats() {
        int totalFiles = sessionOutputs.values().stream()
            .mapToInt(java.util.List::size)
            .sum();

        long totalSize = sessionOutputs.values().stream()
            .flatMap(java.util.List::stream)
            .mapToLong(OffloadedOutput::originalSize)
            .sum();

        return Map.of(
            "totalOutputs", totalOutputs,
            "activeFiles", totalFiles,
            "totalOriginalSize", totalSize,
            "sessionsWithOutputs", sessionOutputs.size(),
            "tempDir", tempDir.toString()
        );
    }

    private String sanitizeFilename(String name) {
        if (name == null) return "unknown";
        return name.replaceAll("[/\\\\]", "_");
    }
}
