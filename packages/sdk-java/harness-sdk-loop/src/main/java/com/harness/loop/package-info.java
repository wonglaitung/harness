/**
 * Loop Engineering module - Goal-driven execution for AI agents.
 *
 * <p>This module implements the Loop Engineering paradigm, where agents
 * run autonomously until a goal is achieved, rather than requiring
 * manual prompting at each step.</p>
 *
 * <h2>Core components</h2>
 * <ul>
 *   <li>{@link com.harness.loop.types.GoalConfig} - Configuration for goal-driven execution</li>
 *   <li>{@link com.harness.loop.types.GoalResult} - Result of goal execution</li>
 *   <li>{@link com.harness.loop.types.GoalStatus} - Status of goal achievement</li>
 *   <li>{@link com.harness.loop.GoalVerifier} - Verifies if a goal has been achieved</li>
 *   <li>{@link com.harness.loop.GoalLoop} - Executes the goal-driven loop</li>
 *   <li>{@link com.harness.loop.automation.Automation} - Simplified API for scheduled/periodic execution</li>
 *   <li>{@link com.harness.loop.worktree.WorktreeOrchestrator} - Parallel execution in isolated worktrees</li>
 * </ul>
 *
 * <h2>Example usage</h2>
 * <pre>{@code
 * Harness agent = new Harness(config);
 *
 * GoalResult result = agent.runGoal(
 *     "Fix all type errors in src/",
 *     GoalConfig.builder()
 *         .maxIterations(50)
 *         .build()
 * );
 *
 * if (result.status() == GoalStatus.ACHIEVED) {
 *     System.out.println("Goal achieved!");
 * }
 * }</pre>
 *
 * @see com.harness.loop.types.GoalConfig
 * @see com.harness.loop.types.GoalResult
 * @see com.harness.loop.types.GoalStatus
 */
package com.harness.loop;
