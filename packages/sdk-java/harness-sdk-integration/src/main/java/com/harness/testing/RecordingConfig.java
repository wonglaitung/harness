package com.harness.testing;

import java.nio.file.Path;

/**
 * Configuration for recording harness.
 */
public class RecordingConfig {

    private final boolean enabled;
    private final Path recordingDir;
    private final String recordingName;
    private final boolean recordToolCalls;
    private final boolean recordLLMCalls;
    private final int maxRecordingSize;

    private RecordingConfig(Builder builder) {
        this.enabled = builder.enabled;
        this.recordingDir = builder.recordingDir;
        this.recordingName = builder.recordingName;
        this.recordToolCalls = builder.recordToolCalls;
        this.recordLLMCalls = builder.recordLLMCalls;
        this.maxRecordingSize = builder.maxRecordingSize;
    }

    public boolean isEnabled() { return enabled; }
    public Path recordingDir() { return recordingDir; }
    public String recordingName() { return recordingName; }
    public boolean recordToolCalls() { return recordToolCalls; }
    public boolean recordLLMCalls() { return recordLLMCalls; }
    public int maxRecordingSize() { return maxRecordingSize; }

    public static RecordingConfig defaults() {
        return builder().build();
    }

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private boolean enabled = true;
        private Path recordingDir = Path.of(".harness/recordings");
        private String recordingName = null;
        private boolean recordToolCalls = true;
        private boolean recordLLMCalls = true;
        private int maxRecordingSize = 1_000_000;

        public Builder enabled(boolean v) { this.enabled = v; return this; }
        public Builder recordingDir(Path v) { this.recordingDir = v; return this; }
        public Builder recordingName(String v) { this.recordingName = v; return this; }
        public Builder recordToolCalls(boolean v) { this.recordToolCalls = v; return this; }
        public Builder recordLLMCalls(boolean v) { this.recordLLMCalls = v; return this; }
        public Builder maxRecordingSize(int v) { this.maxRecordingSize = v; return this; }

        public RecordingConfig build() {
            return new RecordingConfig(this);
        }
    }
}
