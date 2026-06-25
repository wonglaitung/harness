package com.harness.core;

/**
 * Actions a hook can request.
 *
 * - CONTINUE: Normal execution continues
 * - ABORT: Stop execution immediately
 * - RETRY: Retry the current operation
 * - INJECT_MESSAGE: Add a message to the context
 * - MODIFY_ARGS: Modify tool arguments (before execution)
 * - MODIFY_RESULT: Modify tool result (after execution)
 * - REINJECT: Clear context and reinject a prompt (for Ralph Loop)
 */
public enum HookAction {
    CONTINUE,
    ABORT,
    RETRY,
    INJECT_MESSAGE,
    MODIFY_ARGS,
    MODIFY_RESULT,
    REINJECT
}
