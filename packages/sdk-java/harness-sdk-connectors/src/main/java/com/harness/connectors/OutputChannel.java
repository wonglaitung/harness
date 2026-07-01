package com.harness.connectors;

import java.util.HashMap;
import java.util.Map;

/**
 * Output channel configuration.
 *
 * <p>Defines how to send results to external systems.</p>
 */
public class OutputChannel {
    private final String type;
    private final String name;
    private final Map<String, Object> config;

    private OutputChannel(Builder builder) {
        this.type = builder.type;
        this.name = builder.name;
        this.config = new HashMap<>(builder.config);
    }

    // Getters

    public String getType() {
        return type;
    }

    public String getName() {
        return name;
    }

    public Map<String, Object> getConfig() {
        return new HashMap<>(config);
    }

    /**
     * Create a builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * Builder for OutputChannel.
     */
    public static class Builder {
        private String type;
        private String name;
        private Map<String, Object> config = new HashMap<>();

        public Builder type(String type) {
            this.type = type;
            return this;
        }

        public Builder name(String name) {
            this.name = name;
            return this;
        }

        public Builder config(Map<String, Object> config) {
            this.config = new HashMap<>(config);
            return this;
        }

        public Builder addConfig(String key, Object value) {
            this.config.put(key, value);
            return this;
        }

        public OutputChannel build() {
            return new OutputChannel(this);
        }
    }

    @Override
    public String toString() {
        return "OutputChannel{type='" + type + "', name='" + name + "'}";
    }
}
