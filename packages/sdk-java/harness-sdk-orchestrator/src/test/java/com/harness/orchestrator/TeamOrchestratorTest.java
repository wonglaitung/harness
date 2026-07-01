package com.harness.orchestrator;

import com.harness.loop.GoalLoop;
import com.harness.types.LoopResult;
import com.harness.types.Session;
import com.harness.types.TokenUsage;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for TeamOrchestrator.
 */
class TeamOrchestratorTest {

    private MockAgentRunner mockRunner;
    private TeamOrchestrator orchestrator;

    @BeforeEach
    void setUp() {
        mockRunner = new MockAgentRunner();
        orchestrator = new TeamOrchestrator(mockRunner);
    }

    @Test
    void testCreateTeam() {
        AgentRole role1 = AgentRole.builder()
                .name("architect")
                .description("System design")
                .build();

        AgentRole role2 = AgentRole.builder()
                .name("developer")
                .description("Implementation")
                .build();

        TeamConfig team = TeamConfig.builder()
                .name("dev-team")
                .addRole(role1)
                .addRole(role2)
                .coordinationMode(CoordinationMode.BROADCAST)
                .build();

        String teamName = orchestrator.createTeam(team);

        assertEquals("dev-team", teamName);
        assertEquals(team, orchestrator.getTeam("dev-team"));
        assertTrue(orchestrator.listTeams().contains("dev-team"));
    }

    @Test
    void testRunBroadcastMode() {
        // Set up mock responses
        mockRunner.addResponse("architect", true, 1);
        mockRunner.addResponse("developer", true, 1);

        AgentRole role1 = AgentRole.builder()
                .name("architect")
                .description("System design")
                .build();

        AgentRole role2 = AgentRole.builder()
                .name("developer")
                .description("Implementation")
                .build();

        TeamConfig team = TeamConfig.builder()
                .name("broadcast-team")
                .addRole(role1)
                .addRole(role2)
                .coordinationMode(CoordinationMode.BROADCAST)
                .build();

        orchestrator.createTeam(team);

        TeamResult result = orchestrator.run("broadcast-team", "Design and implement feature X").join();

        assertTrue(result.isSuccess());
        assertEquals(2, result.getAgentResults().size());
        assertNotNull(result.getAgentResult("architect"));
        assertNotNull(result.getAgentResult("developer"));
        assertEquals(2, mockRunner.getCallCount());
    }

    @Test
    void testRunSequentialMode() {
        // Set up mock responses
        mockRunner.addResponse("architect", true, 2);
        mockRunner.addResponse("developer", true, 3);

        AgentRole role1 = AgentRole.builder()
                .name("architect")
                .description("System design")
                .maxIterations(2)
                .build();

        AgentRole role2 = AgentRole.builder()
                .name("developer")
                .description("Implementation")
                .maxIterations(3)
                .build();

        TeamConfig team = TeamConfig.builder()
                .name("sequential-team")
                .addRole(role1)
                .addRole(role2)
                .coordinationMode(CoordinationMode.SEQUENTIAL)
                .build();

        orchestrator.createTeam(team);

        TeamResult result = orchestrator.run("sequential-team", "Design and implement feature Y").join();

        assertTrue(result.isSuccess());
        assertEquals(2, result.getAgentResults().size());
        // Sequential mode should call agents one after another
        assertEquals(2, mockRunner.getCallCount());
    }

    @Test
    void testRunHierarchicalMode() {
        // Set up mock responses
        mockRunner.addResponse("leader", true, 1);
        mockRunner.addResponse("worker1", true, 1);
        mockRunner.addResponse("worker2", true, 1);

        AgentRole leader = AgentRole.builder()
                .name("leader")
                .description("Team leader")
                .build();

        AgentRole worker1 = AgentRole.builder()
                .name("worker1")
                .description("Worker 1")
                .build();

        AgentRole worker2 = AgentRole.builder()
                .name("worker2")
                .description("Worker 2")
                .build();

        TeamConfig team = TeamConfig.builder()
                .name("hierarchical-team")
                .addRole(leader)
                .addRole(worker1)
                .addRole(worker2)
                .coordinationMode(CoordinationMode.HIERARCHICAL)
                .build();

        orchestrator.createTeam(team);

        TeamResult result = orchestrator.run("hierarchical-team", "Complete complex task").join();

        assertTrue(result.isSuccess());
        assertEquals(3, result.getAgentResults().size());
    }

    @Test
    void testTeamNotFound() {
        assertThrows(Exception.class, () ->
                orchestrator.run("non-existent-team", "Do something").join());
    }

    @Test
    void testRemoveTeam() {
        AgentRole role = AgentRole.builder()
                .name("test")
                .description("Test role")
                .build();

        TeamConfig team = TeamConfig.builder()
                .name("test-team")
                .addRole(role)
                .build();

        orchestrator.createTeam(team);
        assertNotNull(orchestrator.getTeam("test-team"));

        orchestrator.removeTeam("test-team");
        assertNull(orchestrator.getTeam("test-team"));
    }

    @Test
    void testOverrideCoordinationMode() {
        mockRunner.addResponse("architect", true, 1);
        mockRunner.addResponse("developer", true, 1);

        AgentRole role1 = AgentRole.builder()
                .name("architect")
                .description("System design")
                .build();

        AgentRole role2 = AgentRole.builder()
                .name("developer")
                .description("Implementation")
                .build();

        TeamConfig team = TeamConfig.builder()
                .name("override-team")
                .addRole(role1)
                .addRole(role2)
                .coordinationMode(CoordinationMode.BROADCAST)
                .build();

        orchestrator.createTeam(team);

        // Override to sequential mode
        TeamResult result = orchestrator.run("override-team", "Task", CoordinationMode.SEQUENTIAL).join();

        assertTrue(result.isSuccess());
    }

    /**
     * Mock AgentRunner for testing.
     */
    private static class MockAgentRunner implements GoalLoop.AgentRunner {
        private final List<MockResponse> responses = new ArrayList<>();
        private int index = 0;
        private int callCount = 0;

        void addResponse(String content, boolean achieved, int iterations) {
            responses.add(new MockResponse(content, achieved, iterations));
        }

        int getCallCount() {
            return callCount;
        }

        @Override
        public CompletableFuture<LoopResult> run(String prompt, String sessionId) {
            return run(prompt, sessionId, null);
        }

        @Override
        public CompletableFuture<LoopResult> run(String prompt, String sessionId, Consumer<Object> onProgress) {
            callCount++;

            if (index >= responses.size()) {
                Session session = Session.create(sessionId);
                return CompletableFuture.completedFuture(
                        LoopResult.completed(session, "Default", 1, new TokenUsage(100, 50))
                );
            }

            MockResponse response = responses.get(index++);
            Session session = Session.create(sessionId);

            return CompletableFuture.completedFuture(
                    LoopResult.completed(session, response.content, response.iterations,
                            new TokenUsage(100, 50))
            );
        }

        @Override
        public Session getSession(String sessionId) {
            return Session.create(sessionId);
        }

        @Override
        public int getContextWindow() {
            return 100000;
        }
    }

    private record MockResponse(String content, boolean achieved, int iterations) {}
}
