package com.harness.types;

import java.util.Map;

/**
 * Progress event types for tracking agent execution.
 */
public enum ProgressEventType {
    LOOP_START,            // Agent 循环开始
    LOOP_END,              // Agent 循环结束
    STATE_CHANGE,          // 状态变化
    TOOL_CALL,             // 工具调用开始
    TOOL_RESULT,           // 工具调用结果
    LLM_CALL,              // LLM 调用开始
    LLM_RESPONSE,          // LLM 响应接收
    TEXT_CHUNK,            // 流式文本块
    ITERATION,             // 迭代计数
    ERROR,                 // 错误发生
    STREAM_BACKPRESSURE,   // 流式输出背压
    STUCK_DETECTED,        // 检测到停滞状态
    ROUTER_DECISION;       // 路由决策（CPU Router）

    /**
     * Get the string value of this event type.
     */
    public String getValue() {
        return name().toLowerCase();
    }

    // Factory methods for common events

    /**
     * Create loop start event.
     */
    public static ProgressEvent loopStart(String sessionId) {
        return ProgressEvent.of(LOOP_START, "Loop started for session: " + sessionId,
            Map.of("sessionId", sessionId));
    }

    /**
     * Create loop end event.
     */
    public static ProgressEvent loopEnd(String sessionId, int iterations) {
        return ProgressEvent.of(LOOP_END, "Loop ended after " + iterations + " iterations",
            Map.of("sessionId", sessionId, "iterations", iterations));
    }

    /**
     * Create LLM call start event.
     */
    public static ProgressEvent llmCallStart(int iteration) {
        return ProgressEvent.of(LLM_CALL, "LLM call starting",
            Map.of("iteration", iteration));
    }

    /**
     * Create LLM call end event.
     */
    public static ProgressEvent llmCallEnd(int iteration, LLMResponse response) {
        return ProgressEvent.of(LLM_RESPONSE, "LLM response received",
            Map.of("iteration", iteration,
                   "toolUse", response.isToolUse(),
                   "tokens", response.usage() != null ? response.usage().totalTokens() : 0));
    }

    /**
     * Create tool execute start event.
     */
    public static ProgressEvent toolExecuteStart(String toolName) {
        return ProgressEvent.of(TOOL_CALL, "Executing tool: " + toolName,
            Map.of("toolName", toolName));
    }

    /**
     * Create tool execute end event.
     */
    public static ProgressEvent toolExecuteEnd(String toolName, ToolResult result) {
        return ProgressEvent.of(TOOL_RESULT, "Tool result: " + toolName,
            Map.of("toolName", toolName,
                   "success", result.success(),
                   "contentLength", result.content() != null ? result.content().length() : 0));
    }

    /**
     * Create error event.
     */
    public static ProgressEvent error(String message) {
        return ProgressEvent.of(ERROR, message);
    }
}
