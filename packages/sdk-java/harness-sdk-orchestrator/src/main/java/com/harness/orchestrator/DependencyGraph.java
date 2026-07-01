package com.harness.orchestrator;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Step dependency graph.
 *
 * <p>Manages dependencies between workflow steps and supports:</p>
 * <ul>
 *   <li>Topological ordering for execution</li>
 *   <li>Circular dependency (deadlock) detection</li>
 *   <li>Cascading skip operations for conditional execution</li>
 *   <li>Runtime state tracking (completed, skipped)</li>
 * </ul>
 *
 * <h2>State Management</h2>
 * <ul>
 *   <li>_completed: Steps that have finished (success or failure)</li>
 *   <li>_skipped: Steps that were skipped (condition not met or dependency skipped)</li>
 * </ul>
 */
public class DependencyGraph {
    private static final Logger logger = LoggerFactory.getLogger(DependencyGraph.class);

    private final Map<String, WorkflowStep> steps = new HashMap<>();
    private final Map<String, Set<String>> dependencies = new HashMap<>();
    private final Set<String> completed = new HashSet<>();
    private final Set<String> skipped = new HashSet<>();

    /**
     * Add a step to the graph.
     */
    public void addStep(WorkflowStep step) {
        steps.put(step.getName(), step);
        if (!dependencies.containsKey(step.getName())) {
            dependencies.put(step.getName(), new HashSet<>());
        }
    }

    /**
     * Add a dependency relationship.
     *
     * @param stepName   Step that has the dependency
     * @param dependsOn  Step that must complete first
     */
    public void addDependency(String stepName, String dependsOn) {
        dependencies.computeIfAbsent(stepName, k -> new HashSet<>()).add(dependsOn);
    }

    /**
     * Check if there are pending steps.
     */
    public boolean hasPending() {
        int resolved = completed.size() + skipped.size();
        return resolved < steps.size();
    }

    /**
     * Check if all pending steps depend on skipped steps.
     *
     * <p>This indicates we should gracefully end execution rather than
     * raising a deadlock error.</p>
     */
    public boolean hasOnlySkippedPending() {
        for (Map.Entry<String, WorkflowStep> entry : steps.entrySet()) {
            String name = entry.getKey();
            if (completed.contains(name) || skipped.contains(name)) {
                continue;
            }

            Set<String> deps = dependencies.getOrDefault(name, Set.of());
            if (deps.isEmpty() || !skipped.containsAll(deps)) {
                return false;
            }
        }
        return true;
    }

    /**
     * Get steps that are ready to execute.
     *
     * <p>A step is ready if:</p>
     * <ul>
     *   <li>It hasn't been completed or skipped</li>
     *   <li>All its dependencies have been completed (not skipped)</li>
     * </ul>
     *
     * <p>Note: Steps with skipped dependencies are NOT returned here,
     * they should be handled by the cascade skip logic.</p>
     */
    public List<WorkflowStep> getReadySteps() {
        return steps.values().stream()
                .filter(step -> !completed.contains(step.getName()))
                .filter(step -> !skipped.contains(step.getName()))
                .filter(step -> {
                    Set<String> deps = dependencies.getOrDefault(step.getName(), Set.of());
                    // If any dependency was skipped, this step should be skipped too
                    if (!skipped.isEmpty() && deps.stream().anyMatch(skipped::contains)) {
                        return false;
                    }
                    // All dependencies completed
                    return completed.containsAll(deps);
                })
                .toList();
    }

    /**
     * Mark a step as completed.
     */
    public void markCompleted(String stepName) {
        completed.add(stepName);
        logger.debug("Step '{}' marked as completed", stepName);
    }

    /**
     * Mark a step as skipped and cascade to dependent steps.
     *
     * <p>When a step is skipped, all steps that depend on it should
     * also be skipped (cascade skip). This is done recursively to
     * handle transitive dependencies.</p>
     */
    public void markSkipped(String stepName) {
        if (skipped.contains(stepName)) {
            return; // Already skipped
        }

        skipped.add(stepName);
        logger.debug("Step '{}' marked as skipped", stepName);

        // Find and skip all direct dependents
        Set<String> dependents = getDependents(stepName);
        for (String dependent : dependents) {
            if (!completed.contains(dependent) && !skipped.contains(dependent)) {
                markSkipped(dependent);
            }
        }
    }

    /**
     * Detect circular dependencies (deadlock).
     *
     * <p>Uses depth-first search to detect cycles in the dependency graph.</p>
     */
    public boolean detectDeadlock() {
        Set<String> visited = new HashSet<>();
        Set<String> recStack = new HashSet<>();

        for (String stepName : steps.keySet()) {
            if (!visited.contains(stepName)) {
                if (hasCycle(stepName, visited, recStack)) {
                    return true;
                }
            }
        }
        return false;
    }

    private boolean hasCycle(String node, Set<String> visited, Set<String> recStack) {
        visited.add(node);
        recStack.add(node);

        for (String dep : dependencies.getOrDefault(node, Set.of())) {
            if (!visited.contains(dep)) {
                if (hasCycle(dep, visited, recStack)) {
                    return true;
                }
            } else if (recStack.contains(dep)) {
                logger.warn("Deadlock detected: cycle involving '{}' -> '{}'", node, dep);
                return true;
            }
        }

        recStack.remove(node);
        return false;
    }

    /**
     * Get a step by name.
     */
    public WorkflowStep getStep(String stepName) {
        return steps.get(stepName);
    }

    /**
     * Get dependencies for a step.
     */
    public Set<String> getDependencies(String stepName) {
        return new HashSet<>(dependencies.getOrDefault(stepName, Set.of()));
    }

    /**
     * Get steps that depend on the given step.
     */
    public Set<String> getDependents(String stepName) {
        Set<String> dependents = new HashSet<>();
        for (Map.Entry<String, Set<String>> entry : dependencies.entrySet()) {
            if (entry.getValue().contains(stepName)) {
                dependents.add(entry.getKey());
            }
        }
        return dependents;
    }

    /**
     * Check if a step is completed.
     */
    public boolean isCompleted(String stepName) {
        return completed.contains(stepName);
    }

    /**
     * Check if a step is skipped.
     */
    public boolean isSkipped(String stepName) {
        return skipped.contains(stepName);
    }

    /**
     * Check if a step is resolved (completed or skipped).
     */
    public boolean isResolved(String stepName) {
        return completed.contains(stepName) || skipped.contains(stepName);
    }

    /**
     * Get a summary of the graph status.
     */
    public Map<String, Integer> getStatusSummary() {
        Map<String, Integer> summary = new HashMap<>();
        summary.put("total", steps.size());
        summary.put("completed", completed.size());
        summary.put("skipped", skipped.size());
        summary.put("pending", steps.size() - completed.size() - skipped.size());
        return summary;
    }

    /**
     * Reset the graph state (keep step definitions).
     */
    public void reset() {
        completed.clear();
        skipped.clear();
    }
}
