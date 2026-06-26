package com.harness.llm;

import static org.junit.jupiter.api.Assertions.*;

import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;

import com.harness.types.StopReason;

/**
 * Tests for MockResponse.
 */
class MockResponseTest {

    @Test
    void testTextResponse() {
        MockResponse response = MockResponse.text("Hello, world!");

        assertEquals("Hello, world!", response.getContent());
        assertTrue(response.getToolCalls().isEmpty());
        assertEquals(StopReason.END_TURN, response.getStopReason());
    }

    @Test
    void testToolUseResponse() {
        MockResponse response = MockResponse.toolUse(
            "call_123",
            "read_file",
            Map.of("path", "/test.txt")
        );

        assertEquals("", response.getContent());
        assertEquals(1, response.getToolCalls().size());
        assertEquals(StopReason.TOOL_USE, response.getStopReason());

        Map<String, Object> toolCall = response.getToolCalls().get(0);
        assertEquals("call_123", toolCall.get("id"));
        assertEquals("read_file", toolCall.get("name"));
    }

    @Test
    void testBuilderWithContent() {
        MockResponse response = MockResponse.builder()
            .content("Test response")
            .stopReason(StopReason.END_TURN)
            .build();

        assertEquals("Test response", response.getContent());
        assertEquals(StopReason.END_TURN, response.getStopReason());
    }

    @Test
    void testBuilderWithToolCalls() {
        MockResponse response = MockResponse.builder()
            .content("")
            .addToolCall("id1", "tool1", Map.of("arg1", "value1"))
            .addToolCall("id2", "tool2", Map.of("arg2", "value2"))
            .stopReason(StopReason.TOOL_USE)
            .build();

        assertEquals(2, response.getToolCalls().size());
        assertEquals("tool1", response.getToolCalls().get(0).get("name"));
        assertEquals("tool2", response.getToolCalls().get(1).get("name"));
    }

    @Test
    void testDefaultConstructor() {
        MockResponse response = new MockResponse("Default content");

        assertEquals("Default content", response.getContent());
        assertTrue(response.getToolCalls().isEmpty());
        assertEquals(StopReason.END_TURN, response.getStopReason());
    }

    @Test
    void testFullConstructor() {
        List<Map<String, Object>> toolCalls = List.of(
            Map.of("id", "tc1", "name", "test_tool")
        );

        MockResponse response = new MockResponse(
            "Content",
            toolCalls,
            StopReason.MAX_TOKENS
        );

        assertEquals("Content", response.getContent());
        assertEquals(1, response.getToolCalls().size());
        assertEquals(StopReason.MAX_TOKENS, response.getStopReason());
    }
}