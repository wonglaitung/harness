package com.harness.loop.worktree;

import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Result of merge operations.
 *
 * <p>Returned by WorktreeOrchestrator.merge_successful() to indicate
 * which branches were successfully merged, which had conflicts,
 * and which were skipped due to failed goals.</p>
 */
public class MergeResult {
    private final List<String> merged;
    private final List<String> conflicts;
    private final List<String> skipped;
    private final String error;
    private final Instant mergedAt;

    private MergeResult(Builder builder) {
        this.merged = new ArrayList<>(builder.merged);
        this.conflicts = new ArrayList<>(builder.conflicts);
        this.skipped = new ArrayList<>(builder.skipped);
        this.error = builder.error;
        this.mergedAt = builder.mergedAt;
    }

    /**
     * Check if all merges were successful.
     */
    public boolean isSuccess() {
        return conflicts.isEmpty() && error == null;
    }

    /**
     * Total branches attempted to merge.
     */
    public int getTotalAttempted() {
        return merged.size() + conflicts.size();
    }

    /**
     * Serialize to map.
     */
    public Map<String, Object> toMap() {
        Map<String, Object> map = new HashMap<>();
        map.put("merged", merged);
        map.put("conflicts", conflicts);
        map.put("skipped", skipped);
        map.put("success", isSuccess());
        map.put("error", error);
        return map;
    }

    // Getters

    public List<String> getMerged() {
        return new ArrayList<>(merged);
    }

    public List<String> getConflicts() {
        return new ArrayList<>(conflicts);
    }

    public List<String> getSkipped() {
        return new ArrayList<>(skipped);
    }

    public String getError() {
        return error;
    }

    public Instant getMergedAt() {
        return mergedAt;
    }

    @Override
    public String toString() {
        return "MergeResult{" +
                "merged=" + merged.size() +
                ", conflicts=" + conflicts.size() +
                ", skipped=" + skipped.size() +
                ", success=" + isSuccess() +
                '}';
    }

    /**
     * Create a builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * Builder for MergeResult.
     */
    public static class Builder {
        private List<String> merged = new ArrayList<>();
        private List<String> conflicts = new ArrayList<>();
        private List<String> skipped = new ArrayList<>();
        private String error;
        private Instant mergedAt;

        public Builder merged(List<String> merged) {
            this.merged = new ArrayList<>(merged);
            return this;
        }

        public Builder addMerged(String branch) {
            this.merged.add(branch);
            return this;
        }

        public Builder conflicts(List<String> conflicts) {
            this.conflicts = new ArrayList<>(conflicts);
            return this;
        }

        public Builder addConflict(String branch) {
            this.conflicts.add(branch);
            return this;
        }

        public Builder skipped(List<String> skipped) {
            this.skipped = new ArrayList<>(skipped);
            return this;
        }

        public Builder addSkipped(String branch) {
            this.skipped.add(branch);
            return this;
        }

        public Builder error(String error) {
            this.error = error;
            return this;
        }

        public Builder mergedAt(Instant mergedAt) {
            this.mergedAt = mergedAt;
            return this;
        }

        public MergeResult build() {
            return new MergeResult(this);
        }
    }
}
