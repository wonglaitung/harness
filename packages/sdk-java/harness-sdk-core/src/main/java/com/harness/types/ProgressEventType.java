package com.harness.types;

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
    ROUTER_DECISION        // 路由决策（CPU Router）
}
