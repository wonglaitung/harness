package com.harness.types;

/**
 * Type of streaming chunk.
 */
public enum ChunkType {
    TEXT,               // Text content chunk
    TOOL_CALL_START,    // Start of a tool call
    TOOL_CALL_DELTA,    // Tool call argument delta
    TOOL_CALL_END,      // End of a tool call
    ERROR,              // Error chunk
    DONE                // Stream finished
}
