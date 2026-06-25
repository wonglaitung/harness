package com.harness.core;

/**
 * Circuit breaker states.
 */
public enum CircuitState {
    CLOSED,       // Normal operation
    OPEN,         // Blocking calls
    HALF_OPEN     // Testing if recovered
}
