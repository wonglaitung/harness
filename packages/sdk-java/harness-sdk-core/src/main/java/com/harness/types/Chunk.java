package com.harness.types;

import java.util.Map;

/**
 * A chunk of streaming output from LLM.
 *
 * @param type Type of chunk
 * @param content Text content (for TEXT and ERROR types)
 * @param toolCallId Tool call ID (for TOOL_CALL_* types)
 * @param toolName Tool name (for TOOL_CALL_START)
 * @param toolArguments Tool arguments (for TOOL_CALL_DELTA)
 */
public record Chunk(
    ChunkType type,
    String content,
    String toolCallId,
    String toolName,
    Map<String, Object> toolArguments
) {

    /**
     * Create a text chunk.
     */
    public static Chunk text(String content) {
        return new Chunk(ChunkType.TEXT, content, null, null, Map.of());
    }

    /**
     * Create a tool call start chunk.
     */
    public static Chunk toolCallStart(String toolCallId, String toolName) {
        return new Chunk(ChunkType.TOOL_CALL_START, null, toolCallId, toolName, Map.of());
    }

    /**
     * Create a tool call delta chunk.
     */
    public static Chunk toolCallDelta(String toolCallId, Map<String, Object> arguments) {
        return new Chunk(ChunkType.TOOL_CALL_DELTA, null, toolCallId, null, arguments);
    }

    /**
     * Create an error chunk.
     */
    public static Chunk error(String message) {
        return new Chunk(ChunkType.ERROR, message, null, null, Map.of());
    }

    /**
     * Create a done chunk.
     */
    public static Chunk done() {
        return new Chunk(ChunkType.DONE, null, null, null, Map.of());
    }
}
