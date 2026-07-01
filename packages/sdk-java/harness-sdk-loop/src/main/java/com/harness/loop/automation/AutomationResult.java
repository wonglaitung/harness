package com.harness.loop.automation;

import com.harness.loop.types.GoalResult;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;

/**
 * Result of an Automation execution.
 *
 * <p>Tracks the status and statistics of an automation.</p>
 */
public class AutomationResult {
    private final String automationName;
    private AutomationStatus status;
    private GoalResult goalResult;
    private Instant lastRun;
    private int runCount;
    private int errorCount;
    private String errorMessage;

    /**
     * Create a new AutomationResult.
     *
     * @param automationName Name of the automation
     */
    public AutomationResult(String automationName) {
        this.automationName = automationName;
        this.status = AutomationStatus.PENDING;
        this.runCount = 0;
        this.errorCount = 0;
    }

    // Getters

    public String getAutomationName() {
        return automationName;
    }

    public AutomationStatus getStatus() {
        return status;
    }

    public GoalResult getGoalResult() {
        return goalResult;
    }

    public Instant getLastRun() {
        return lastRun;
    }

    public int getRunCount() {
        return runCount;
    }

    public int getErrorCount() {
        return errorCount;
    }

    public String getErrorMessage() {
        return errorMessage;
    }

    // Setters (package-private)

    void setStatus(AutomationStatus status) {
        this.status = status;
    }

    void setGoalResult(GoalResult goalResult) {
        this.goalResult = goalResult;
    }

    void setLastRun(Instant lastRun) {
        this.lastRun = lastRun;
    }

    void incrementRunCount() {
        this.runCount++;
    }

    void incrementErrorCount() {
        this.errorCount++;
    }

    void setErrorMessage(String errorMessage) {
        this.errorMessage = errorMessage;
    }

    /**
     * Record a successful execution.
     */
    void recordSuccess(GoalResult result) {
        this.goalResult = result;
        this.lastRun = Instant.now();
        this.runCount++;
        this.errorMessage = null;
    }

    /**
     * Record a failed execution.
     */
    void recordError(String error) {
        this.errorCount++;
        this.errorMessage = error;
        this.lastRun = Instant.now();
    }

    /**
     * Serialize to map for logging/storage.
     */
    public Map<String, Object> toMap() {
        Map<String, Object> map = new HashMap<>();
        map.put("automation_name", automationName);
        map.put("status", status.getValue());
        map.put("last_run", lastRun != null ? lastRun.toString() : null);
        map.put("run_count", runCount);
        map.put("error_count", errorCount);
        map.put("error_message", errorMessage);
        return map;
    }

    @Override
    public String toString() {
        return "AutomationResult{" +
                "automationName='" + automationName + '\'' +
                ", status=" + status +
                ", runCount=" + runCount +
                ", errorCount=" + errorCount +
                '}';
    }
}
