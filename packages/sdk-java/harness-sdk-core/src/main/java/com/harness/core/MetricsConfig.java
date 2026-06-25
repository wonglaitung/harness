package com.harness.core;

/**
 * Configuration for Prometheus metrics.
 */
public record MetricsConfig(
    boolean enabled,
    String prefix,
    double[] durationBuckets
) {

    public MetricsConfig() {
        this(true, "harness", new double[]{0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0});
    }

    /**
     * Create default configuration.
     */
    public static MetricsConfig defaults() {
        return new MetricsConfig();
    }

    /**
     * Create builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private boolean enabled = true;
        private String prefix = "harness";
        private double[] durationBuckets = new double[]{0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0};

        public Builder enabled(boolean value) {
            this.enabled = value;
            return this;
        }

        public Builder prefix(String value) {
            this.prefix = value;
            return this;
        }

        public Builder durationBuckets(double[] value) {
            this.durationBuckets = value;
            return this;
        }

        public MetricsConfig build() {
            return new MetricsConfig(enabled, prefix, durationBuckets);
        }
    }
}
