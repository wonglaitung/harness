package com.harness.core;

/**
 * Configuration for OpenTelemetry tracing.
 */
public record TracingConfig(
    boolean enabled,
    String serviceName,
    String serviceVersion,
    boolean exportConsole,
    boolean exportOtlp,
    String otlpEndpoint,
    double sampleRate
) {

    public TracingConfig() {
        this(true, "harness-agent", "1.0.0", false, false, "http://localhost:4317", 1.0);
    }

    /**
     * Create default configuration.
     */
    public static TracingConfig defaults() {
        return new TracingConfig();
    }

    /**
     * Create builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private boolean enabled = true;
        private String serviceName = "harness-agent";
        private String serviceVersion = "1.0.0";
        private boolean exportConsole = false;
        private boolean exportOtlp = false;
        private String otlpEndpoint = "http://localhost:4317";
        private double sampleRate = 1.0;

        public Builder enabled(boolean value) {
            this.enabled = value;
            return this;
        }

        public Builder serviceName(String value) {
            this.serviceName = value;
            return this;
        }

        public Builder serviceVersion(String value) {
            this.serviceVersion = value;
            return this;
        }

        public Builder exportConsole(boolean value) {
            this.exportConsole = value;
            return this;
        }

        public Builder exportOtlp(boolean value) {
            this.exportOtlp = value;
            return this;
        }

        public Builder otlpEndpoint(String value) {
            this.otlpEndpoint = value;
            return this;
        }

        public Builder sampleRate(double value) {
            this.sampleRate = value;
            return this;
        }

        public TracingConfig build() {
            return new TracingConfig(
                enabled, serviceName, serviceVersion,
                exportConsole, exportOtlp, otlpEndpoint, sampleRate
            );
        }
    }
}
