package com.harness.core;

import java.util.Map;

import com.harness.types.Message;
import com.harness.types.ToolResult;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for HookResult convenience methods.
 *
 * Reference: packages/sdk/tests/test_hooks.py - TestHookResult
 */
class HookResultTest {

    @Test
    void testContinueMethod() {
        HookResult result = HookResult.continue_();
        assertEquals(HookAction.CONTINUE, result.action());
        assertNull(result.modifiedArgs());
        assertNull(result.injectMessage());
    }

    @Test
    void testAbortMethod() {
        HookResult result = HookResult.abort("Test abort");
        assertEquals(HookAction.ABORT, result.action());
        assertEquals("Test abort", result.metadata().get("reason"));
    }

    @Test
    void testAbortMethodWithMetadata() {
        Map<String, Object> meta = Map.of("tool", "dangerous_tool", "user", "test");
        HookResult result = HookResult.abort("Blocked", meta);
        assertEquals(HookAction.ABORT, result.action());
        assertEquals("Blocked", result.metadata().get("reason"));
        assertEquals("dangerous_tool", result.metadata().get("tool"));
    }

    @Test
    void testRetryMethod() {
        HookResult result = HookResult.retry(5.0);
        assertEquals(HookAction.RETRY, result.action());
        assertEquals(5.0, result.delaySeconds());
    }

    @Test
    void testInjectMessageMethod() {
        Message msg = Message.user("test message");
        HookResult result = HookResult.injectMessage(msg);
        assertEquals(HookAction.INJECT_MESSAGE, result.action());
        assertEquals(msg, result.injectMessage());
    }

    @Test
    void testModifyArgsMethod() {
        Map<String, Object> args = Map.of("key", "value", "count", 42);
        HookResult result = HookResult.modifyArgs(args);
        assertEquals(HookAction.MODIFY_ARGS, result.action());
        assertEquals(args, result.modifiedArgs());
    }

    @Test
    void testModifyResultMethod() {
        ToolResult toolResult = ToolResult.success("call-123", "output");
        HookResult result = HookResult.modifyResult(toolResult);
        assertEquals(HookAction.MODIFY_RESULT, result.action());
        assertEquals(toolResult, result.modifiedResult());
    }

    @Test
    void testModifyToolOutputMethod() {
        HookResult result = HookResult.modifyToolOutput("new output");
        assertEquals(HookAction.MODIFY_RESULT, result.action());
        assertNotNull(result.modifiedResult());
        assertEquals("new output", result.modifiedResult().content());
    }

    @Test
    void testReinjectMethod() {
        HookResult result = HookResult.reinject(true);
        assertEquals(HookAction.REINJECT, result.action());
        assertTrue(result.clearContext());
    }

    @Test
    void testReinjectWithoutClear() {
        HookResult result = HookResult.reinject(false);
        assertEquals(HookAction.REINJECT, result.action());
        assertFalse(result.clearContext());
    }

    @Test
    void testBuilder() {
        Message msg = Message.user("test");
        Map<String, Object> args = Map.of("key", "value");
        Map<String, Object> meta = Map.of("reason", "custom");

        HookResult result = HookResult.builder()
            .action(HookAction.INJECT_MESSAGE)
            .injectMessage(msg)
            .modifiedArgs(args)
            .delaySeconds(2.5)
            .clearContext(true)
            .metadata(meta)
            .build();

        assertEquals(HookAction.INJECT_MESSAGE, result.action());
        assertEquals(msg, result.injectMessage());
        assertEquals(args, result.modifiedArgs());
        assertEquals(2.5, result.delaySeconds());
        assertTrue(result.clearContext());
        assertEquals(meta, result.metadata());
    }

    @Test
    void testBuilderDefaults() {
        HookResult result = HookResult.builder().build();
        assertEquals(HookAction.CONTINUE, result.action());
        assertNull(result.modifiedArgs());
        assertNull(result.modifiedResult());
        assertNull(result.injectMessage());
        assertEquals(0, result.delaySeconds());
        assertFalse(result.clearContext());
        assertTrue(result.metadata().isEmpty());
    }
}
