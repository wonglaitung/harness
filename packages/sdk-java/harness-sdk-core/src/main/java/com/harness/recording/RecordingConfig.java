package com.harness.recording;

import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * Configuration for recording.
 */
public class RecordingConfig {
    private final Path recordingDir;
    private final boolean autoSave;
    private final boolean includeMetadata;
    private final int maxRecordingSize;

    private RecordingConfig(Builder builder) {
        this.recordingDir = builder.recordingDir;
        this.autoSave = builder.autoSave;
        this.includeMetadata = builder.includeMetadata;
        this.maxRecordingSize = builder.maxRecordingSize;
    }

    public Path getRecordingDir() {
        return recordingDir;
    }

    public boolean isAutoSave() {
        return autoSave;
    }

    public boolean isIncludeMetadata() {
        return includeMetadata;
    }

    public int getMaxRecordingSize() {
        return maxRecordingSize;
    }

    public static class Builder {
        private Path recordingDir = Paths.get(".harness_recordings");
        private boolean autoSave = true;
        private boolean includeMetadata = true;
        private int maxRecordingSize = 100;

        public Builder recordingDir(Path recordingDir) {
            this.recordingDir = recordingDir;
            return this;
        }

        public Builder autoSave(boolean autoSave) {
            this.autoSave = autoSave;
            return this;
        }

        public Builder includeMetadata(boolean includeMetadata) {
            this.includeMetadata = includeMetadata;
            return this;
        }

        public Builder maxRecordingSize(int maxRecordingSize) {
            this.maxRecordingSize = maxRecordingSize;
            return this;
        }

        public RecordingConfig build() {
            return new RecordingConfig(this);
        }
    }
}
