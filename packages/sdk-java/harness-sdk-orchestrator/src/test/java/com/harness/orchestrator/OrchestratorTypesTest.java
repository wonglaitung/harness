package com.harness.orchestrator;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for Orchestrator types.
 */
class OrchestratorTypesTest {

    @Test
    void testAgentRoleBuilder() {
        AgentRole role = AgentRole.builder()
                .name("architect")
                .description("System design")
                .addSkill("code-analysis")
                .maxIterations(30)
                .build();

        assertEquals("architect", role.getName());
        assertEquals("System design", role.getDescription());
        assertEquals(1, role.getSkills().size());
        assertTrue(role.getSkills().contains("code-analysis"));
        assertEquals(30, role.getMaxIterations());
    }

    @Test
    void testAgentRoleValidation() {
        // Empty name
        assertThrows(IllegalArgumentException.class, () ->
                AgentRole.builder()
                        .description("Test")
                        .build());

        // Empty description
        assertThrows(IllegalArgumentException.class, () ->
                AgentRole.builder()
                        .name("test")
                        .build());

        // Invalid maxIterations
        assertThrows(IllegalArgumentException.class, () ->
                AgentRole.builder()
                        .name("test")
                        .description("Test")
                        .maxIterations(0)
                        .build());
    }

    @Test
    void testTeamConfigBuilder() {
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
                .description("Development team")
                .addRole(role1)
                .addRole(role2)
                .coordinationMode(CoordinationMode.SEQUENTIAL)
                .build();

        assertEquals("dev-team", team.getName());
        assertEquals(2, team.getRoles().size());
        assertEquals(CoordinationMode.SEQUENTIAL, team.getCoordinationMode());
        assertTrue(team.isSharedMemory());
        assertEquals("internal", team.getMessageBus());
    }

    @Test
    void testTeamConfigValidation() {
        AgentRole role = AgentRole.builder()
                .name("test")
                .description("Test role")
                .build();

        // Empty name
        assertThrows(IllegalArgumentException.class, () ->
                TeamConfig.builder()
                        .addRole(role)
                        .build());

        // No roles
        assertThrows(IllegalArgumentException.class, () ->
                TeamConfig.builder()
                        .name("test")
                        .build());

        // Duplicate role names
        AgentRole role1 = AgentRole.builder()
                .name("duplicate")
                .description("Role 1")
                .build();

        AgentRole role2 = AgentRole.builder()
                .name("duplicate")
                .description("Role 2")
                .build();

        assertThrows(IllegalArgumentException.class, () ->
                TeamConfig.builder()
                        .name("test")
                        .addRole(role1)
                        .addRole(role2)
                        .build());
    }

    @Test
    void testTeamResultBuilder() {
        TeamResult result = TeamResult.builder()
                .teamName("test-team")
                .success(true)
                .totalIterations(10)
                .totalTokens(500)
                .durationSeconds(30.5)
                .build();

        assertEquals("test-team", result.getTeamName());
        assertTrue(result.isSuccess());
        assertEquals(10, result.getTotalIterations());
        assertEquals(500, result.getTotalTokens());
        assertEquals(30.5, result.getDurationSeconds());
    }

    @Test
    void testCoordinationMode() {
        assertEquals("broadcast", CoordinationMode.BROADCAST.getValue());
        assertEquals("sequential", CoordinationMode.SEQUENTIAL.getValue());
        assertEquals("hierarchical", CoordinationMode.HIERARCHICAL.getValue());
    }

    @Test
    void testExecutionMetricBuilder() {
        ExecutionMetric metric = ExecutionMetric.builder()
                .name("test-workflow")
                .type("workflow")
                .status("success")
                .durationSeconds(10.5)
                .iterations(5)
                .tokensUsed(100)
                .build();

        assertEquals("test-workflow", metric.getName());
        assertEquals("workflow", metric.getType());
        assertEquals("success", metric.getStatus());
        assertEquals(10.5, metric.getDurationSeconds());
        assertEquals(5, metric.getIterations());
        assertEquals(100, metric.getTokensUsed());
        assertNotNull(metric.getTimestamp());
    }
}
