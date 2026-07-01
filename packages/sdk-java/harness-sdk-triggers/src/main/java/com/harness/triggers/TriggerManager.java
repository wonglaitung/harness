package com.harness.triggers;

import com.harness.loop.GoalLoop;
import com.harness.loop.types.GoalConfig;
import com.harness.loop.types.GoalResult;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Semaphore;
import java.util.concurrent.CompletableFuture;

/**
 * Central manager for triggers.
 *
 * <p>Handles:</p>
 * <ul>
 *   <li>Registration and unregistration of triggers</li>
 *   <li>Starting and stopping all triggers</li>
 *   <li>Executing goals when triggers fire</li>
 *   <li>Error handling and retries</li>
 * </ul>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * TriggerManager manager = new TriggerManager(agentRunner, 3);
 *
 * // Register a trigger
 * CronTrigger trigger = new CronTrigger(
 *     "0 9 * * *",
 *     new TriggerAction.Builder()
 *         .goal("Generate daily report")
 *         .build()
 * );
 * String triggerId = manager.register(trigger);
 *
 * // Start all triggers
 * manager.start().join();
 *
 * // Later, stop all triggers
 * manager.stop().join();
 * }</pre>
 */
public class TriggerManager {
    private static final Logger logger = LoggerFactory.getLogger(TriggerManager.class);

    private final GoalLoop.AgentRunner agentRunner;
    private final int maxConcurrentGoals;
    private final Map<String, TriggerRegistration> registrations = new ConcurrentHashMap<>();
    private final ExecutorService executor;
    private final Semaphore semaphore;

    private volatile boolean running = false;

    /**
     * Create a new TriggerManager.
     *
     * @param agentRunner Agent runner for goal execution
     */
    public TriggerManager(GoalLoop.AgentRunner agentRunner) {
        this(agentRunner, 5);
    }

    /**
     * Create a new TriggerManager.
     *
     * @param agentRunner Agent runner for goal execution
     * @param maxConcurrentGoals Maximum number of goals to execute concurrently
     */
    public TriggerManager(GoalLoop.AgentRunner agentRunner, int maxConcurrentGoals) {
        this.agentRunner = agentRunner;
        this.maxConcurrentGoals = maxConcurrentGoals;
        this.executor = Executors.newCachedThreadPool();
        this.semaphore = new Semaphore(maxConcurrentGoals);
    }

    /**
     * Register a trigger.
     *
     * @param trigger Trigger to register
     * @return Trigger ID
     */
    public String register(Trigger trigger) {
        return register(trigger, null, true);
    }

    /**
     * Register a trigger.
     *
     * @param trigger Trigger to register
     * @param action Action to execute (optional if trigger has action)
     * @return Trigger ID
     */
    public String register(Trigger trigger, TriggerAction action) {
        return register(trigger, action, true);
    }

    /**
     * Register a trigger.
     *
     * @param trigger Trigger to register
     * @param action Action to execute (optional if trigger has action)
     * @param enabled Whether to enable the trigger immediately
     * @return Trigger ID
     */
    public String register(Trigger trigger, TriggerAction action, boolean enabled) {
        TriggerAction triggerAction = action != null ? action : trigger.getAction();
        if (triggerAction == null) {
            throw new IllegalArgumentException(
                    "No action provided for trigger " + trigger.getId() + ". " +
                    "Either pass an action or set trigger.action.");
        }

        // Generate ID if not set
        if (trigger.getId() == null || trigger.getId().isEmpty()) {
            trigger.setId("trigger_" + UUID.randomUUID().toString().substring(0, 8));
        }

        registrations.put(trigger.getId(), new TriggerRegistration(trigger, triggerAction, enabled));
        logger.info("Registered trigger {} of type {}", trigger.getId(), trigger.getTriggerType().getValue());

        return trigger.getId();
    }

    /**
     * Unregister a trigger.
     *
     * @param triggerId ID of trigger to unregister
     * @return True if trigger was found and removed
     */
    public boolean unregister(String triggerId) {
        TriggerRegistration reg = registrations.remove(triggerId);
        if (reg == null) {
            return false;
        }

        // Stop trigger if running
        if (reg.getTrigger().isRunning()) {
            reg.getTrigger().stop();
        }

        logger.info("Unregistered trigger {}", triggerId);
        return true;
    }

    /**
     * Enable a registered trigger.
     *
     * @param triggerId ID of trigger to enable
     * @return True if trigger was found and enabled
     */
    public boolean enable(String triggerId) {
        TriggerRegistration reg = registrations.get(triggerId);
        if (reg == null) {
            return false;
        }
        reg.setEnabled(true);
        logger.debug("Enabled trigger {}", triggerId);
        return true;
    }

    /**
     * Disable a registered trigger.
     *
     * @param triggerId ID of trigger to disable
     * @return True if trigger was found and disabled
     */
    public boolean disable(String triggerId) {
        TriggerRegistration reg = registrations.get(triggerId);
        if (reg == null) {
            return false;
        }
        reg.setEnabled(false);
        logger.debug("Disabled trigger {}", triggerId);
        return true;
    }

    /**
     * Start all registered and enabled triggers.
     *
     * @return CompletableFuture that completes when all triggers are started
     */
    public CompletableFuture<Void> start() {
        if (running) {
            logger.warn("TriggerManager is already running");
            return CompletableFuture.completedFuture(null);
        }

        running = true;

        // Start all enabled triggers
        List<CompletableFuture<Void>> futures = new ArrayList<>();
        for (TriggerRegistration reg : registrations.values()) {
            if (reg.isEnabled()) {
                futures.add(reg.getTrigger().start(event -> handleEvent(event)));
            }
        }

        logger.info("TriggerManager started with {} triggers", registrations.size());
        return CompletableFuture.allOf(futures.toArray(new CompletableFuture[0]));
    }

    /**
     * Stop all triggers.
     *
     * @return CompletableFuture that completes when all triggers are stopped
     */
    public CompletableFuture<Void> stop() {
        if (!running) {
            return CompletableFuture.completedFuture(null);
        }

        running = false;

        // Stop all triggers
        List<CompletableFuture<Void>> futures = new ArrayList<>();
        for (TriggerRegistration reg : registrations.values()) {
            futures.add(reg.getTrigger().stop());
        }

        logger.info("TriggerManager stopped");
        return CompletableFuture.allOf(futures.toArray(new CompletableFuture[0]));
    }

    /**
     * Handle a trigger event.
     *
     * @param event Event to handle
     */
    private void handleEvent(TriggerEvent event) {
        executor.submit(() -> {
            try {
                semaphore.acquire();
                try {
                    executeGoal(event);
                } finally {
                    semaphore.release();
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        });
    }

    /**
     * Execute goal for a trigger event.
     *
     * @param event Event to handle
     */
    private void executeGoal(TriggerEvent event) {
        String triggerId = event.getTriggerId();
        TriggerRegistration reg = registrations.get(triggerId);

        if (reg == null) {
            logger.warn("Received event for unknown trigger {}", triggerId);
            return;
        }

        if (!reg.isEnabled()) {
            logger.debug("Ignoring event for disabled trigger {}", triggerId);
            return;
        }

        logger.info("Executing goal for trigger {}", triggerId);

        try {
            // Build goal config
            GoalConfig goalConfig = reg.getAction().toGoalConfig(event);

            // Create and run goal loop
            GoalLoop loop = new GoalLoop(agentRunner, goalConfig);
            GoalResult result = loop.run().join();

            // Update statistics
            reg.setLastFired(Instant.now());
            reg.incrementFireCount();

            if (result.achieved()) {
                logger.info("Trigger {} goal achieved in {} iterations", triggerId, result.totalIterations());
            } else {
                logger.warn("Trigger {} goal not achieved: {}", triggerId, result.status().getValue());
            }

        } catch (Exception e) {
            reg.incrementErrorCount();
            reg.setLastError(e.getMessage());
            logger.error("Error executing trigger {}: {}", triggerId, e.getMessage());
        }
    }

    /**
     * List all registered triggers with their status.
     *
     * @return List of trigger info maps
     */
    public List<Map<String, Object>> listTriggers() {
        List<Map<String, Object>> result = new ArrayList<>();
        for (Map.Entry<String, TriggerRegistration> entry : registrations.entrySet()) {
            TriggerRegistration reg = entry.getValue();
            Map<String, Object> info = new java.util.HashMap<>();
            info.put("id", entry.getKey());
            info.put("type", reg.getTrigger().getTriggerType().getValue());
            info.put("state", reg.getTrigger().getState().getValue());
            info.put("enabled", reg.isEnabled());
            info.put("last_fired", reg.getLastFired() != null ? reg.getLastFired().toString() : null);
            info.put("fire_count", reg.getFireCount());
            info.put("error_count", reg.getErrorCount());
            info.put("last_error", reg.getLastError());
            result.add(info);
        }
        return result;
    }

    /**
     * Get a trigger registration by ID.
     *
     * @param triggerId Trigger ID
     * @return TriggerRegistration or null if not found
     */
    public TriggerRegistration getTrigger(String triggerId) {
        return registrations.get(triggerId);
    }

    /**
     * Check if the manager is running.
     */
    public boolean isRunning() {
        return running;
    }

    /**
     * Get the number of registered triggers.
     */
    public int getTriggerCount() {
        return registrations.size();
    }
}
