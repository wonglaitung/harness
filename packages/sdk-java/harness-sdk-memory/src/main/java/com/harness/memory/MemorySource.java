package com.harness.memory;

/**
 * Source of memory entry.
 */
public enum MemorySource {
    USER_INPUT,          // Explicitly provided by user
    AGENT_OBSERVATION,   // Learned by agent during execution
    EXPLICIT_SAVE        // Saved through explicit API call
}