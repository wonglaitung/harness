package com.harness.orchestrator;

/**
 * Team coordination mode.
 *
 * <p>Defines how multiple agents coordinate within a team:</p>
 * <ul>
 *   <li>BROADCAST: All agents execute same task simultaneously</li>
 *   <li>SEQUENTIAL: Agents execute in sequence, passing outputs</li>
 *   <li>HIERARCHICAL: Leader assigns tasks to workers</li>
 * </ul>
 */
public enum CoordinationMode {
    BROADCAST("broadcast"),
    SEQUENTIAL("sequential"),
    HIERARCHICAL("hierarchical");

    private final String value;

    CoordinationMode(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}
