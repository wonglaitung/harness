package com.harness.loop.worktree;

import com.harness.loop.types.GoalResult;

import java.time.Duration;
import java.time.Instant;
import java.util.HashMap;
import java.util.Map;

/**
 * Result of a worktree execution.
 *
 * <p>Contains both the goal execution result and git-specific information.</p>
 */
public class WorktreeResult {
    private final String name;
    private final GoalResult goalResult;
    private final String worktreePath;
    private final String branchName;
    private final int commitsMade;
    private final boolean cleanupDone;
    private final Instant createdAt;
    private final Instant completedAt;

    private WorktreeResult(Builder builder) {
        this.name = builder.name;
        this.goalResult = builder.goalResult;
        this.worktreePath = builder.worktreePath;
        this.branchName = builder.branchName;
        this.commitsMade = builder.commitsMade;
        this.cleanupDone = builder.cleanupDone;
        this.createdAt = builder.createdAt;
        this.completedAt = builder.completedAt;
    }

    /**
     * Check if the goal was achieved.
     */
    public boolean isAchieved() {
        return goalResult != null && goalResult.achieved();
    }

    /**
     * Calculate execution duration in seconds.
     */
    public double getDurationSeconds() {
        if (createdAt != null && completedAt != null) {
            return Duration.between(createdAt, completedAt).toMillis() / 1000.0;
        }
        return 0.0;
    }

    /**
     * Serialize to map.
     */
    public Map<String, Object> toMap() {
        Map<String, Object> map = new HashMap<>();
        map.put("name", name);
        map.put("achieved", isAchieved());
        map.put("worktree_path", worktreePath);
        map.put("branch_name", branchName);
        map.put("commits_made", commitsMade);
        map.put("cleanup_done", cleanupDone);
        map.put("duration_seconds", getDurationSeconds());
        map.put("goal_result", goalResult != null ? goalResult.toMap() : null);
        return map;
    }

    // Getters

    public String getName() {
        return name;
    }

    public GoalResult getGoalResult() {
        return goalResult;
    }

    public String getWorktreePath() {
        return worktreePath;
    }

    public String getBranchName() {
        return branchName;
    }

    public int getCommitsMade() {
        return commitsMade;
    }

    public boolean isCleanupDone() {
        return cleanupDone;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getCompletedAt() {
        return completedAt;
    }

    @Override
    public String toString() {
        return "WorktreeResult{" +
                "name='" + name + '\'' +
                ", achieved=" + isAchieved() +
                ", branchName='" + branchName + '\'' +
                '}';
    }

    /**
     * Create a builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * Builder for WorktreeResult.
     */
    public static class Builder {
        private String name;
        private GoalResult goalResult;
        private String worktreePath = "";
        private String branchName = "";
        private int commitsMade = 0;
        private boolean cleanupDone = false;
        private Instant createdAt;
        private Instant completedAt;

        public Builder name(String name) {
            this.name = name;
            return this;
        }

        public Builder goalResult(GoalResult goalResult) {
            this.goalResult = goalResult;
            return this;
        }

        public Builder worktreePath(String worktreePath) {
            this.worktreePath = worktreePath;
            return this;
        }

        public Builder branchName(String branchName) {
            this.branchName = branchName;
            return this;
        }

        public Builder commitsMade(int commitsMade) {
            this.commitsMade = commitsMade;
            return this;
        }

        public Builder cleanupDone(boolean cleanupDone) {
            this.cleanupDone = cleanupDone;
            return this;
        }

        public Builder createdAt(Instant createdAt) {
            this.createdAt = createdAt;
            return this;
        }

        public Builder completedAt(Instant completedAt) {
            this.completedAt = completedAt;
            return this;
        }

        public WorktreeResult build() {
            return new WorktreeResult(this);
        }
    }
}
