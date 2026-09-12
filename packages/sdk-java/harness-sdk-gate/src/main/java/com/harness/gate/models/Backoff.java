package com.harness.gate.models;

/**
 * Retry backoff strategy.
 */
public enum Backoff {
    CONSTANT("constant"),
    LINEAR("linear"),
    EXPONENTIAL("exponential");

    private final String value;

    Backoff(String value) {
        this.value = value;
    }

    public String value() {
        return value;
    }
}
