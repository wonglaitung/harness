package com.harness.loop.automation;

import com.harness.loop.GoalLoop;
import com.harness.loop.types.GoalConfig;
import com.harness.loop.types.GoalResult;
import com.harness.loop.types.GoalStatus;
import com.harness.loop.types.VerificationMethod;
import com.harness.types.LoopResult;
import com.harness.types.Session;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.Consumer;

/**
 * Automation - Simplified API for scheduled goal execution.
 *
 * <p>Automation combines a trigger (cron or interval) with a goal configuration,
 * providing a simple interface for scheduled and periodic task execution.</p>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * // Create a daily automation
 * Automation automation = Automation.builder()
 *     .name("daily-report")
 *     .goal("Generate daily report")
 *     .schedule("0 9 * * *")  // Daily at 9:00
 *     .build();
 *
 * // Start it
 * automation.start(agentRunner).join();
 *
 * // Check status
 * System.out.println(automation.getStatus());
 *
 * // Stop it
 * automation.stop().join();
 * }</pre>
 */
public class Automation {
    private static final Logger logger = LoggerFactory.getLogger(Automation.class);

    private final AutomationConfig config;
    private final AtomicReference<AutomationStatus> status;
    private final AutomationResult result;

    private GoalLoop.AgentRunner agent;
    private ScheduledExecutorService scheduler;
    private ScheduledFuture<?> scheduledFuture;
    private Consumer<Object> progressCallback;

    /**
     * Create an Automation with configuration.
     *
     * @param config Automation configuration
     */
    public Automation(AutomationConfig config) {
        this.config = config;
        this.status = new AtomicReference<>(AutomationStatus.PENDING);
        this.result = new AutomationResult(config.getName());
    }

    /**
     * Create an Automation with name and goal.
     *
     * @param name Automation name
     * @param goal Goal description
     */
    public Automation(String name, String goal) {
        this(AutomationConfig.builder()
                .name(name)
                .goal(goal)
                .intervalSeconds(60) // Default interval
                .build());
    }

    /**
     * Create a builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * Get the automation name.
     */
    public String getName() {
        return config.getName();
    }

    /**
     * Get the automation configuration.
     */
    public AutomationConfig getConfig() {
        return config;
    }

    /**
     * Get the current status.
     */
    public AutomationStatus getStatus() {
        return status.get();
    }

    /**
     * Get the execution result.
     */
    public AutomationResult getResult() {
        return result;
    }

    /**
     * Check if automation is running.
     */
    public boolean isRunning() {
        return status.get() == AutomationStatus.RUNNING;
    }

    /**
     * Set progress callback.
     *
     * @param callback Progress callback
     * @return this
     */
    public Automation withProgressCallback(Consumer<Object> callback) {
        this.progressCallback = callback;
        return this;
    }

    /**
     * Start the automation.
     *
     * @param agent Agent runner to execute goals
     * @return CompletableFuture that completes when started
     */
    public CompletableFuture<Void> start(GoalLoop.AgentRunner agent) {
        if (status.get() == AutomationStatus.RUNNING) {
            logger.warn("Automation {} is already running", getName());
            return CompletableFuture.completedFuture(null);
        }

        this.agent = agent;
        this.scheduler = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "automation-" + getName());
            t.setDaemon(true);
            return t;
        });

        if (config.isCronBased()) {
            return startCronBased();
        } else {
            return startIntervalBased();
        }
    }

    private CompletableFuture<Void> startCronBased() {
        // Parse cron expression (simplified - just use interval for now)
        // Full cron support would require a library like Quartz
        String cron = config.getSchedule();
        long intervalMillis = parseCronToInterval(cron);

        logger.info("Starting automation {} with cron schedule: {} (interval: {}ms)",
                getName(), cron, intervalMillis);

        scheduledFuture = scheduler.scheduleAtFixedRate(
                this::executeGoal,
                0,
                intervalMillis,
                TimeUnit.MILLISECONDS
        );

        status.set(AutomationStatus.RUNNING);
        return CompletableFuture.completedFuture(null);
    }

    private CompletableFuture<Void> startIntervalBased() {
        long intervalMillis = config.getIntervalSeconds() * 1000L;

        logger.info("Starting automation {} with interval: {}s",
                getName(), config.getIntervalSeconds());

        scheduledFuture = scheduler.scheduleAtFixedRate(
                this::executeGoal,
                0,
                intervalMillis,
                TimeUnit.MILLISECONDS
        );

        status.set(AutomationStatus.RUNNING);
        return CompletableFuture.completedFuture(null);
    }

    /**
     * Stop the automation.
     *
     * @return CompletableFuture that completes when stopped
     */
    public CompletableFuture<Void> stop() {
        if (scheduledFuture != null) {
            scheduledFuture.cancel(false);
            scheduledFuture = null;
        }

        if (scheduler != null) {
            scheduler.shutdown();
            try {
                if (!scheduler.awaitTermination(5, TimeUnit.SECONDS)) {
                    scheduler.shutdownNow();
                }
            } catch (InterruptedException e) {
                scheduler.shutdownNow();
                Thread.currentThread().interrupt();
            }
            scheduler = null;
        }

        status.set(AutomationStatus.STOPPED);
        logger.info("Automation {} stopped after {} runs", getName(), result.getRunCount());

        return CompletableFuture.completedFuture(null);
    }

    /**
     * Pause the automation.
     */
    public void pause() {
        if (status.get() != AutomationStatus.RUNNING) {
            logger.warn("Automation {} is not running", getName());
            return;
        }

        if (scheduledFuture != null) {
            scheduledFuture.cancel(false);
        }

        status.set(AutomationStatus.PAUSED);
        logger.info("Automation {} paused", getName());
    }

    /**
     * Resume a paused automation.
     */
    public void resume() {
        if (status.get() != AutomationStatus.PAUSED) {
            logger.warn("Automation {} is not paused", getName());
            return;
        }

        // Restart scheduler
        this.scheduler = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "automation-" + getName());
            t.setDaemon(true);
            return t;
        });

        if (config.isCronBased()) {
            long intervalMillis = parseCronToInterval(config.getSchedule());
            scheduledFuture = scheduler.scheduleAtFixedRate(
                    this::executeGoal,
                    0,
                    intervalMillis,
                    TimeUnit.MILLISECONDS
            );
        } else {
            scheduledFuture = scheduler.scheduleAtFixedRate(
                    this::executeGoal,
                    0,
                    config.getIntervalSeconds() * 1000L,
                    TimeUnit.MILLISECONDS
            );
        }

        status.set(AutomationStatus.RUNNING);
        logger.info("Automation {} resumed", getName());
    }

    /**
     * Execute the goal manually (outside of schedule).
     *
     * @return CompletableFuture with the goal result
     */
    public CompletableFuture<GoalResult> executeNow() {
        if (agent == null) {
            return CompletableFuture.failedFuture(
                    new IllegalStateException("Agent not set. Call start() first."));
        }

        return doExecuteGoal();
    }

    private void executeGoal() {
        if (status.get() != AutomationStatus.RUNNING) {
            return;
        }

        try {
            GoalResult goalResult = doExecuteGoal().join();

            if (goalResult.achieved()) {
                logger.info("Automation {} goal achieved in {} iterations",
                        getName(), goalResult.totalIterations());
            } else {
                logger.warn("Automation {} goal not achieved: {}",
                        getName(), goalResult.status().getValue());
            }

            handleOutput(goalResult);

        } catch (Exception e) {
            result.recordError(e.getMessage());
            result.setStatus(AutomationStatus.ERROR);
            logger.error("Automation {} error: {}", getName(), e.getMessage());
        }
    }

    private CompletableFuture<GoalResult> doExecuteGoal() {
        logger.info("Automation {} executing goal", getName());

        // Build goal config
        GoalConfig.Builder configBuilder = new GoalConfig.Builder()
                .description(config.getGoal())
                .workspaceDir(config.getWorkspaceDir())
                .maxIterations(config.getMaxIterations())
                .timeoutSeconds(config.getTimeoutSeconds());

        // Only use CUSTOM verification if customVerifier is provided
        if (config.getCustomVerifier() != null) {
            configBuilder.verificationMethod(VerificationMethod.CUSTOM);
            configBuilder.customVerifier(config.getCustomVerifier());
        }

        GoalConfig goalConfig = configBuilder.build();

        GoalLoop loop = new GoalLoop(agent, goalConfig, progressCallback);

        return loop.run().thenApply(goalResult -> {
            result.recordSuccess(goalResult);
            return goalResult;
        });
    }

    private void handleOutput(GoalResult goalResult) {
        for (String channel : config.getOutputChannels()) {
            try {
                switch (channel.toLowerCase()) {
                    case "console":
                        System.out.println("[" + getName() + "] " +
                                (goalResult.finalResponse() != null ? goalResult.finalResponse() : ""));
                        break;
                    case "log":
                        logger.info("[{}] {}", getName(), goalResult.finalResponse());
                        break;
                    default:
                        logger.warn("Unknown output channel: {}", channel);
                }
            } catch (Exception e) {
                logger.warn("Failed to output to {}: {}", channel, e.getMessage());
            }
        }
    }

    /**
     * Parse a simple cron expression to interval in milliseconds.
     *
     * <p>Supports simple formats:</p>
     * <ul>
     *   <li>"*\/N * * * *" - Every N minutes</li>
     *   <li>"0 * * * *" - Hourly</li>
     *   <li>"0 0 * * *" - Daily at midnight</li>
     * </ul>
     */
    private long parseCronToInterval(String cron) {
        String[] parts = cron.trim().split("\\s+");
        if (parts.length != 5) {
            logger.warn("Invalid cron format: {}, defaulting to 1 hour", cron);
            return TimeUnit.HOURS.toMillis(1);
        }

        String minute = parts[0];
        String hour = parts[1];

        // Every N minutes: "*/N * * * *"
        if (minute.startsWith("*/") && hour.equals("*")) {
            try {
                int interval = Integer.parseInt(minute.substring(2));
                return TimeUnit.MINUTES.toMillis(interval);
            } catch (NumberFormatException e) {
                // Fall through
            }
        }

        // Hourly: "0 * * * *"
        if (minute.equals("0") && hour.equals("*")) {
            return TimeUnit.HOURS.toMillis(1);
        }

        // Daily: "0 0 * * *" or specific hour
        if (minute.equals("0") && !hour.equals("*")) {
            return TimeUnit.HOURS.toMillis(24);
        }

        // Default: 1 hour
        logger.warn("Unsupported cron format: {}, defaulting to 1 hour", cron);
        return TimeUnit.HOURS.toMillis(1);
    }

    @Override
    public String toString() {
        return "Automation{" +
                "name='" + getName() + '\'' +
                ", status=" + status.get() +
                ", runs=" + result.getRunCount() +
                '}';
    }

    /**
     * Builder for Automation.
     */
    public static class Builder {
        private String name;
        private String goal;
        private String schedule;
        private Integer intervalSeconds;
        private String workspaceDir = ".";
        private int maxIterations = 50;
        private int timeoutSeconds = 3600;
        private java.util.function.Function<GoalResult, Boolean> customVerifier;
        private List<String> skills = new ArrayList<>();
        private List<String> outputChannels = new ArrayList<>();
        private int maxRetries = 3;
        private double retryDelaySeconds = 5.0;

        public Builder name(String name) {
            this.name = name;
            return this;
        }

        public Builder goal(String goal) {
            this.goal = goal;
            return this;
        }

        public Builder schedule(String schedule) {
            this.schedule = schedule;
            return this;
        }

        public Builder intervalSeconds(Integer intervalSeconds) {
            this.intervalSeconds = intervalSeconds;
            return this;
        }

        public Builder workspaceDir(String workspaceDir) {
            this.workspaceDir = workspaceDir;
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

        public Builder customVerifier(java.util.function.Function<GoalResult, Boolean> customVerifier) {
            this.customVerifier = customVerifier;
            return this;
        }

        public Builder skills(List<String> skills) {
            this.skills = new ArrayList<>(skills);
            return this;
        }

        public Builder addSkill(String skill) {
            this.skills.add(skill);
            return this;
        }

        public Builder outputChannels(List<String> outputChannels) {
            this.outputChannels = new ArrayList<>(outputChannels);
            return this;
        }

        public Builder addOutputChannel(String channel) {
            this.outputChannels.add(channel);
            return this;
        }

        public Builder maxRetries(int maxRetries) {
            this.maxRetries = maxRetries;
            return this;
        }

        public Builder retryDelaySeconds(double retryDelaySeconds) {
            this.retryDelaySeconds = retryDelaySeconds;
            return this;
        }

        public Automation build() {
            AutomationConfig.Builder configBuilder = AutomationConfig.builder()
                    .name(name)
                    .goal(goal)
                    .workspaceDir(workspaceDir)
                    .maxIterations(maxIterations)
                    .timeoutSeconds(timeoutSeconds)
                    .customVerifier(customVerifier)
                    .skills(skills)
                    .outputChannels(outputChannels)
                    .maxRetries(maxRetries)
                    .retryDelaySeconds(retryDelaySeconds);

            if (schedule != null) {
                configBuilder.schedule(schedule);
            } else if (intervalSeconds != null) {
                configBuilder.intervalSeconds(intervalSeconds);
            } else {
                throw new IllegalArgumentException("Either schedule or intervalSeconds is required");
            }

            return new Automation(configBuilder.build());
        }
    }
}
