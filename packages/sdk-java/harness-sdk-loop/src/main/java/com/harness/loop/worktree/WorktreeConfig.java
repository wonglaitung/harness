package com.harness.loop.worktree;

import com.harness.loop.types.GoalResult;

import java.util.function.Function;
import java.util.regex.Pattern;

/**
 * Configuration for a worktree-based goal execution.
 *
 * <p>Each WorktreeConfig represents an isolated execution environment
 * with its own git worktree and optional branch.</p>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * WorktreeConfig config = WorktreeConfig.builder()
 *     .name("feature-auth")
 *     .goal("Implement user authentication")
 *     .baseBranch("main")
 *     .createBranch(true)
 *     .build();
 * }</pre>
 */
public class WorktreeConfig {
    private static final Pattern SAFE_NAME_PATTERN = Pattern.compile("^[\\w\\-/.]+$");
    public static final String WORKTREES_DIR = ".worktrees";

    private final String name;
    private final String goal;
    private final String baseBranch;
    private final boolean createBranch;
    private final String branchName;
    private final int maxIterations;
    private final int timeoutSeconds;
    private final Function<GoalResult, Boolean> customVerifier;
    private final boolean autoCleanup;
    private final boolean autoMerge;

    private WorktreeConfig(Builder builder) {
        this.name = builder.name;
        this.goal = builder.goal;
        this.baseBranch = builder.baseBranch;
        this.createBranch = builder.createBranch;
        this.branchName = builder.branchName;
        this.maxIterations = builder.maxIterations;
        this.timeoutSeconds = builder.timeoutSeconds;
        this.customVerifier = builder.customVerifier;
        this.autoCleanup = builder.autoCleanup;
        this.autoMerge = builder.autoMerge;

        validate();
    }

    private void validate() {
        if (name == null || name.isEmpty()) {
            throw new IllegalArgumentException("Worktree name cannot be empty");
        }

        if (goal == null || goal.isEmpty()) {
            throw new IllegalArgumentException("Goal cannot be empty");
        }

        if (!SAFE_NAME_PATTERN.matcher(name).matches()) {
            throw new IllegalArgumentException(
                    "Invalid worktree name '" + name + "': " +
                    "must contain only alphanumeric, dash, underscore, slash, or dot");
        }
    }

    /**
     * Get the effective branch name for this worktree.
     */
    public String getEffectiveBranchName() {
        if (branchName != null && !branchName.isEmpty()) {
            return branchName;
        }
        return createBranch ? name : baseBranch;
    }

    // Getters

    public String getName() {
        return name;
    }

    public String getGoal() {
        return goal;
    }

    public String getBaseBranch() {
        return baseBranch;
    }

    public boolean isCreateBranch() {
        return createBranch;
    }

    public String getBranchName() {
        return branchName;
    }

    public int getMaxIterations() {
        return maxIterations;
    }

    public int getTimeoutSeconds() {
        return timeoutSeconds;
    }

    public Function<GoalResult, Boolean> getCustomVerifier() {
        return customVerifier;
    }

    public boolean isAutoCleanup() {
        return autoCleanup;
    }

    public boolean isAutoMerge() {
        return autoMerge;
    }

    /**
     * Create a builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * Builder for WorktreeConfig.
     */
    public static class Builder {
        private String name;
        private String goal;
        private String baseBranch = "main";
        private boolean createBranch = true;
        private String branchName;
        private int maxIterations = 50;
        private int timeoutSeconds = 3600;
        private Function<GoalResult, Boolean> customVerifier;
        private boolean autoCleanup = true;
        private boolean autoMerge = false;

        public Builder name(String name) {
            this.name = name;
            return this;
        }

        public Builder goal(String goal) {
            this.goal = goal;
            return this;
        }

        public Builder baseBranch(String baseBranch) {
            this.baseBranch = baseBranch;
            return this;
        }

        public Builder createBranch(boolean createBranch) {
            this.createBranch = createBranch;
            return this;
        }

        public Builder branchName(String branchName) {
            this.branchName = branchName;
            return this;
        }

        public Builder maxIterations(int maxIterations) {
            this.maxIterations = maxIterations;
            return this;
        }

        public Builder timeoutSeconds(int timeoutSeconds) {
            this.timeoutSeconds = timeoutSeconds;
            return this;
        }

        public Builder customVerifier(Function<GoalResult, Boolean> customVerifier) {
            this.customVerifier = customVerifier;
            return this;
        }

        public Builder autoCleanup(boolean autoCleanup) {
            this.autoCleanup = autoCleanup;
            return this;
        }

        public Builder autoMerge(boolean autoMerge) {
            this.autoMerge = autoMerge;
            return this;
        }

        public WorktreeConfig build() {
            return new WorktreeConfig(this);
        }
    }
}
