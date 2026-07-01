package com.harness.recording;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;

/**
 * A recorded interaction (LLM request/response, tool call, etc.).
 */
public class RecordedInteraction {
    private final String type;
    private final Instant timestamp;
    private final Map<String, Object> data;

    private RecordedInteraction(Builder builder) {
        this.type = builder.type;
        this.timestamp = builder.timestamp != null ? builder.timestamp : Instant.now();
        this.data = builder.data;
    }

    public String getType() {
        return type;
    }

    public Instant getTimestamp() {
        return timestamp;
    }

    public Map<String, Object> getData() {
        return data;
    }

    public static class Builder {
        private String type;
        private Instant timestamp;
        private Map<String, Object> data = new HashMap<>();

        public Builder type(String type) {
            this.type = type;
            return this;
        }

        public Builder timestamp(Instant timestamp) {
            this.timestamp = timestamp;
            return this;
        }

        public Builder data(Map<String, Object> data) {
            this.data = data != null ? new HashMap<>(data) : new HashMap<>();
            return this;
        }

        public Builder addData(String key, Object value) {
            this.data.put(key, value);
            return this;
        }

        public RecordedInteraction build() {
            if (type == null || type.isEmpty()) {
                throw new IllegalArgumentException("type is required");
            }
            return new RecordedInteraction(this);
        }
    }
}
