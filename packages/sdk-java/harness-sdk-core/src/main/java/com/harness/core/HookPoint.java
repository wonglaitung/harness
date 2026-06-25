package com.harness.core;

/**
 * Points in the agent loop where hooks can be triggered.
 *
 * Hooks allow custom logic to be injected at key points:
 * - Before/after LLM calls
 * - Before/after tool execution
 * - On errors
 * - On loop start/end
 * - On exit attempts (for Ralph Loop)
 */
public enum HookPoint {
    BEFORE_LLM_CALL,        // LLM 调用前
    AFTER_LLM_CALL,         // LLM 调用后
    BEFORE_TOOL_EXECUTE,    // 工具执行前
    AFTER_TOOL_EXECUTE,     // 工具执行后
    ON_ERROR,               // 错误发生时
    ON_LOOP_START,          // 循环开始
    ON_LOOP_END,            // 循环结束
    ON_EXIT_ATTEMPT         // 尝试退出时（Ralph Loop）
}
