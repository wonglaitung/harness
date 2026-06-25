package com.harness.core;

/**
 * Actions to take when an error occurs.
 */
public enum ErrorAction {
    RETRY,              // Retry the operation
    COMPRESS_CONTEXT,   // Compress context and retry
    ABORT,              // Stop execution
    SKIP,               // Skip and continue
    ESCALATE            // Escalate to user
}
