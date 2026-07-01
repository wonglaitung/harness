package com.harness.connectors;

/**
 * Supported connector types.
 */
public enum ConnectorType {
    WEBHOOK("webhook"),
    SLACK("slack"),
    GITHUB("github"),
    DISCORD("discord"),
    EMAIL("email"),
    CUSTOM("custom");

    private final String value;

    ConnectorType(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }

    public static ConnectorType fromValue(String value) {
        for (ConnectorType type : values()) {
            if (type.value.equalsIgnoreCase(value)) {
                return type;
            }
        }
        return CUSTOM;
    }
}
