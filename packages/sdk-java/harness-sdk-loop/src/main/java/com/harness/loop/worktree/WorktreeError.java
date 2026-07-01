package com.harness.loop.worktree;

/**
 * Exception raised for worktree operation failures.
 *
 * <p>Common scenarios:</p>
 * <ul>
 *   <li>Failed to create worktree (git error)</li>
 *   <li>Failed to cleanup worktree</li>
 *   <li>Merge conflict in main repository</li>
 *   <li>Invalid repository state</li>
 * </ul>
 */
public class WorktreeError extends RuntimeException {

    public WorktreeError(String message) {
        super(message);
    }

    public WorktreeError(String message, Throwable cause) {
        super(message, cause);
    }
}
