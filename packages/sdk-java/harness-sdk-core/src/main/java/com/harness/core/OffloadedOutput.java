package com.harness.core;

import java.nio.file.Path;
import java.time.LocalDateTime;

/**
 * Record of an offloaded tool output.
 */
public record OffloadedOutput(
    Path filePath,
    String toolName,
    String toolCallId,
    int originalSize,
    String preview,
    String summary,
    LocalDateTime createdAt,
    String sessionId
) {

    /**
     * Get a reference string to include in context.
     */
    public String getReferenceString() {
        StringBuilder sb = new StringBuilder();
        sb.append("[Output from ").append(toolName).append(" (").append(originalSize).append(" chars)]\n");

        if (summary != null && !summary.isEmpty()) {
            sb.append("Summary: ").append(summary).append("\n");
        }

        sb.append("Preview: ").append(preview).append("\n");
        sb.append("Full output saved to: ").append(filePath);

        return sb.toString();
    }
}
