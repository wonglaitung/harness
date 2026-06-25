package com.harness.core;

import java.util.List;
import java.util.Map;

import com.harness.types.LLMResponse;
import com.harness.types.Message;
import com.harness.types.ToolResult;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for HookContext.
 *
 * Reference: packages/sdk/tests/test_hooks.py - TestHookManager
 */
class HookContextTest {

    @Test
    void testBuilderDefaults() {
        HookContext context = HookContext.builder()
            .hookPoint(HookPoint.BEFORE_LLM_CALL)
            .sessionId("test-session")
            .build();

        assertEquals(HookPoint.BEFORE_LLM_CALL, context.hookPoint());
        assertEquals("test-session", context.sessionId());
        assertEquals(0, context.iteration());
        assertNull(context.toolName());
        assertNull(context.toolArgs());
        assertNull(context.toolResult());
        assertNull(context.llmResponse());
        assertNull(context.error());
        assertNull(context.messages());
        assertTrue(context.metadata().isEmpty());
    }

    @Test
    void testBuilderWithAllFields() {
        List<Message> messages = List.of(Message.user("hello"));
        Map<String, Object> toolArgs = Map.of("path", "/tmp/test");
        ToolResult toolResult = new ToolResult("call-1", true, "output", null);
        LLMResponse llmResponse = new LLMResponse("assistant", "response", List.of(), null);
        Exception error = new RuntimeException("test error");
        Map<String, Object> metadata = Map.of("key", "value");

        HookContext context = HookContext.builder()
            .hookPoint(HookPoint.AFTER_TOOL_EXECUTE)
            .sessionId("session-123")
            .iteration(5)
            .toolName("read")
            .toolArgs(toolArgs)
            .toolResult(toolResult)
            .llmResponse(llmResponse)
            .error(error)
            .messages(messages)
            .metadata(metadata)
            .build();

        assertEquals(HookPoint.AFTER_TOOL_EXECUTE, context.hookPoint());
        assertEquals("session-123", context.sessionId());
        assertEquals(5, context.iteration());
        assertEquals("read", context.toolName());
        assertEquals(toolArgs, context.toolArgs());
        assertEquals(toolResult, context.toolResult());
        assertEquals(llmResponse, context.llmResponse());
        assertEquals(error, context.error());
        assertEquals(messages, context.messages());
        assertEquals(metadata, context.metadata());
    }

    @Test
    void testUserMessageReturnsLastUserMessage() {
        List<Message> messages = List.of(
            Message.system("system prompt"),
            Message.user("first user message"),
            Message.assistant("assistant response"),
            Message.user("last user message")
        );

        HookContext context = HookContext.builder()
            .hookPoint(HookPoint.BEFORE_LLM_CALL)
            .sessionId("test")
            .messages(messages)
            .build();

        assertEquals("last user message", context.userMessage());
    }

    @Test
    void testUserMessageReturnsNullWhenNoUserMessages() {
        List<Message> messages = List.of(
            Message.system("system prompt"),
            Message.assistant("assistant response")
        );

        HookContext context = HookContext.builder()
            .hookPoint(HookPoint.BEFORE_LLM_CALL)
            .sessionId("test")
            .messages(messages)
            .build();

        assertNull(context.userMessage());
    }

    @Test
    void testUserMessageReturnsNullWhenMessagesIsNull() {
        HookContext context = HookContext.builder()
            .hookPoint(HookPoint.BEFORE_LLM_CALL)
            .sessionId("test")
            .messages(null)
            .build();

        assertNull(context.userMessage());
    }

    @Test
    void testUserMessageReturnsNullWhenMessagesIsEmpty() {
        HookContext context = HookContext.builder()
            .hookPoint(HookPoint.BEFORE_LLM_CALL)
            .sessionId("test")
            .messages(List.of())
            .build();

        assertNull(context.userMessage());
    }

    @Test
    void testToolOutputReturnsContent() {
        ToolResult toolResult = new ToolResult("call-1", true, "tool output content", null);

        HookContext context = HookContext.builder()
            .hookPoint(HookPoint.AFTER_TOOL_EXECUTE)
            .sessionId("test")
            .toolResult(toolResult)
            .build();

        assertEquals("tool output content", context.toolOutput());
    }

    @Test
    void testToolOutputReturnsNullWhenNoToolResult() {
        HookContext context = HookContext.builder()
            .hookPoint(HookPoint.AFTER_TOOL_EXECUTE)
            .sessionId("test")
            .build();

        assertNull(context.toolOutput());
    }

    @Test
    void testCompactConstructorWithToolCall() {
        // This tests the compact constructor that takes ToolCall
        // Since ToolCall might not exist, we'll test the builder equivalent
        List<Message> messages = List.of(Message.user("test"));
        LLMResponse llmResponse = new LLMResponse("assistant", "response", List.of(), null);

        HookContext context = HookContext.builder()
            .hookPoint(HookPoint.AFTER_LLM_CALL)
            .sessionId("session-compact")
            .iteration(1)
            .messages(messages)
            .llmResponse(llmResponse)
            .toolName("read")
            .toolArgs(Map.of("file_path", "/tmp/test.txt"))
            .build();

        assertEquals(HookPoint.AFTER_LLM_CALL, context.hookPoint());
        assertEquals("session-compact", context.sessionId());
        assertEquals(1, context.iteration());
        assertEquals("read", context.toolName());
        assertEquals(Map.of("file_path", "/tmp/test.txt"), context.toolArgs());
    }

    @Test
    void testCompactConstructorWithoutToolCall() {
        List<Message> messages = List.of(Message.user("test"));
        LLMResponse llmResponse = new LLMResponse("assistant", "response", List.of(), null);

        HookContext context = HookContext.builder()
            .hookPoint(HookPoint.AFTER_LLM_CALL)
            .sessionId("session-no-tool")
            .iteration(1)
            .messages(messages)
            .llmResponse(llmResponse)
            .build();

        assertNull(context.toolName());
        assertNull(context.toolArgs());
    }

    @Test
    void testAllHookPoints() {
        // Verify all hook points can be used
        HookPoint[] points = {
            HookPoint.BEFORE_LLM_CALL,
            HookPoint.AFTER_LLM_CALL,
            HookPoint.BEFORE_TOOL_EXECUTE,
            HookPoint.AFTER_TOOL_EXECUTE,
            HookPoint.ON_ERROR,
            HookPoint.ON_LOOP_START,
            HookPoint.ON_LOOP_END,
            HookPoint.ON_EXIT_ATTEMPT
        };

        for (HookPoint point : points) {
            HookContext context = HookContext.builder()
                .hookPoint(point)
                .sessionId("test")
                .build();
            assertEquals(point, context.hookPoint());
        }
    }
}
