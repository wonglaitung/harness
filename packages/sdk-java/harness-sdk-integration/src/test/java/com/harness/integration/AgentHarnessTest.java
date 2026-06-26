package com.harness.integration;

import static org.junit.jupiter.api.Assertions.*;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import com.harness.core.HarnessConfig;
import com.harness.core.LLMClient;
import com.harness.core.LoopConfig;
import com.harness.core.Tool;
import com.harness.types.LLMResponse;
import com.harness.types.Message;
import com.harness.types.Session;
import com.harness.types.StopReason;
import com.harness.types.TokenUsage;
import com.harness.types.ToolCall;
import com.harness.types.ToolResult;

/**
 * Tests for AgentHarness.
 */
class AgentHarnessTest {

    private MockLLMClient mockLLM;

    @BeforeEach
    void setUp() {
        mockLLM = new MockLLMClient();
    }

    @Test
    void testBuilderCreatesHarness() {
        AgentHarness agent = AgentHarness.builder()
            .model("claude-sonnet-4-6")
            .llmClient(mockLLM)
            .build();

        assertNotNull(agent);
        assertEquals("claude-sonnet-4-6", agent.getConfig().getModel());
    }

    @Test
    void testRunWithSimpleResponse() {
        mockLLM.setResponse(LLMResponse.builder()
            .content("Hello! How can I help you?")
            .usage(new TokenUsage(10, 20))
            .build());

        AgentHarness agent = AgentHarness.builder()
            .llmClient(mockLLM)
            .build();

        var result = agent.run("Hi").join();

        assertTrue(result.status().toString().equals("COMPLETED"));
        assertNotNull(result.finalResponse());
    }

    @Test
    void testRegisterTool() {
        AgentHarness agent = AgentHarness.builder()
            .llmClient(mockLLM)
            .build();

        Tool tool = new MockTool("test_tool", "A test tool");
        agent.registerTool(tool);

        assertEquals(1, agent.getToolRegistry().size());
    }

    @Test
    void testAddHook() {
        AgentHarness agent = AgentHarness.builder()
            .llmClient(mockLLM)
            .build();

        MockHook hook = new MockHook();
        agent.addHook(hook);

        // Hook should be registered
        assertNotNull(agent.getHookRegistry());
    }

    @Test
    void testGetOrCreateSession() {
        AgentHarness agent = AgentHarness.builder()
            .llmClient(mockLLM)
            .build();

        Session session = agent.getOrCreateSession("test-session");

        assertNotNull(session);
        assertEquals("test-session", session.id());
    }

    @Test
    void testGetStats() {
        AgentHarness agent = AgentHarness.builder()
            .llmClient(mockLLM)
            .build();

        Map<String, Object> stats = agent.getStats();

        assertNotNull(stats);
        assertTrue(stats.containsKey("sessionCount"));
        assertTrue(stats.containsKey("toolCount"));
    }

    @Test
    void testContinueSession() {
        mockLLM.setResponse(LLMResponse.builder()
            .content("Response")
            .usage(new TokenUsage(5, 10))
            .build());

        AgentHarness agent = AgentHarness.builder()
            .llmClient(mockLLM)
            .build();

        // First run
        agent.run("First message", "session-1").join();

        // Continue session
        var result = agent.continueSession("session-1", "Second message").join();

        assertNotNull(result);
        assertEquals("session-1", result.session().id());
    }

    @Test
    void testClearSession() {
        AgentHarness agent = AgentHarness.builder()
            .llmClient(mockLLM)
            .build();

        agent.getOrCreateSession("test-session");
        agent.clearSession("test-session");

        Session session = agent.getSession("test-session");
        assertNull(session);
    }

    @Test
    void testConfigPreservation() {
        HarnessConfig config = HarnessConfig.builder()
            .model("gpt-4o")
            .maxIterations(5)
            .toolTimeout(60.0)
            .build();

        AgentHarness agent = AgentHarness.builder()
            .config(config)
            .llmClient(mockLLM)
            .build();

        assertEquals("gpt-4o", agent.getConfig().getModel());
        assertEquals(5, agent.getConfig().getMaxIterations());
        assertEquals(60.0, agent.getConfig().getToolTimeout());
    }

    // -------------------------------------------------------------------------
    // Mock classes for testing
    // -------------------------------------------------------------------------

    static class MockLLMClient implements LLMClient {
        private LLMResponse response;

        public void setResponse(LLMResponse response) {
            this.response = response;
        }

        @Override
        public LLMResponse call(List<Message> messages, List<ToolDefinition> tools, String systemPrompt) {
            return response != null ? response :
                LLMResponse.builder()
                    .content("Default response")
                    .usage(new TokenUsage(10, 10))
                    .build();
        }

        @Override
        public java.util.concurrent.CompletableFuture<LLMResponse> callAsync(List<Message> messages, List<ToolDefinition> tools, String systemPrompt) {
            return java.util.concurrent.CompletableFuture.completedFuture(call(messages, tools, systemPrompt));
        }

        @Override
        public void stream(List<Message> messages, List<ToolDefinition> tools, String systemPrompt, StreamCallback onChunk) {
            LLMResponse resp = call(messages, tools, systemPrompt);
            if (resp.content() != null) {
                onChunk.onChunk(resp.content());
            }
        }

        @Override
        public String modelName() {
            return "mock-model";
        }
    }

    static class MockTool implements Tool {
        private final String name;
        private final String description;

        MockTool(String name, String description) {
            this.name = name;
            this.description = description;
        }

        @Override
        public String name() { return name; }

        @Override
        public String description() { return description; }

        @Override
        public Map<String, Object> inputSchema() {
            return Map.of("type", "object", "properties", Map.of());
        }

        @Override
        public java.util.concurrent.CompletableFuture<ToolResult> execute(Map<String, Object> args, com.harness.core.ToolContext context) {
            return java.util.concurrent.CompletableFuture.completedFuture(
                ToolResult.success("mock-call", "Mock result", name())
            );
        }
    }

    static class MockHook implements com.harness.core.LifecycleHook {
        boolean executed = false;

        @Override
        public List<com.harness.core.HookPoint> hookPoints() {
            return List.of(com.harness.core.HookPoint.BEFORE_LLM_CALL);
        }

        @Override
        public com.harness.core.HookResult execute(com.harness.core.HookContext context) {
            executed = true;
            return com.harness.core.HookResult.continue_();
        }
    }
}