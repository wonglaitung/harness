package com.harness.orchestrator;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for DependencyGraph.
 */
class DependencyGraphTest {

    private DependencyGraph graph;

    @BeforeEach
    void setUp() {
        graph = new DependencyGraph();
    }

    @Test
    void testAddStep() {
        WorkflowStep step = WorkflowStep.builder()
                .name("step1")
                .goal("Do something")
                .build();

        graph.addStep(step);

        assertEquals(step, graph.getStep("step1"));
        assertTrue(graph.getDependencies("step1").isEmpty());
    }

    @Test
    void testAddDependency() {
        WorkflowStep step1 = WorkflowStep.builder()
                .name("step1")
                .goal("First")
                .build();

        WorkflowStep step2 = WorkflowStep.builder()
                .name("step2")
                .goal("Second")
                .build();

        graph.addStep(step1);
        graph.addStep(step2);
        graph.addDependency("step2", "step1");

        Set<String> deps = graph.getDependencies("step2");
        assertEquals(1, deps.size());
        assertTrue(deps.contains("step1"));
    }

    @Test
    void testGetReadySteps() {
        WorkflowStep step1 = WorkflowStep.builder()
                .name("step1")
                .goal("First")
                .build();

        WorkflowStep step2 = WorkflowStep.builder()
                .name("step2")
                .goal("Second")
                .build();

        WorkflowStep step3 = WorkflowStep.builder()
                .name("step3")
                .goal("Third")
                .build();

        graph.addStep(step1);
        graph.addStep(step2);
        graph.addStep(step3);
        graph.addDependency("step2", "step1");
        graph.addDependency("step3", "step2");

        // Only step1 is ready initially
        List<WorkflowStep> ready = graph.getReadySteps();
        assertEquals(1, ready.size());
        assertEquals("step1", ready.get(0).getName());

        // Mark step1 as completed
        graph.markCompleted("step1");
        ready = graph.getReadySteps();
        assertEquals(1, ready.size());
        assertEquals("step2", ready.get(0).getName());

        // Mark step2 as completed
        graph.markCompleted("step2");
        ready = graph.getReadySteps();
        assertEquals(1, ready.size());
        assertEquals("step3", ready.get(0).getName());
    }

    @Test
    void testCascadeSkip() {
        WorkflowStep step1 = WorkflowStep.builder()
                .name("step1")
                .goal("First")
                .build();

        WorkflowStep step2 = WorkflowStep.builder()
                .name("step2")
                .goal("Second")
                .build();

        WorkflowStep step3 = WorkflowStep.builder()
                .name("step3")
                .goal("Third")
                .build();

        graph.addStep(step1);
        graph.addStep(step2);
        graph.addStep(step3);
        graph.addDependency("step2", "step1");
        graph.addDependency("step3", "step2");

        // Skip step1, should cascade to step2 and step3
        graph.markSkipped("step1");

        assertTrue(graph.isSkipped("step1"));
        assertTrue(graph.isSkipped("step2"));
        assertTrue(graph.isSkipped("step3"));

        // No ready steps after skip cascade
        List<WorkflowStep> ready = graph.getReadySteps();
        assertTrue(ready.isEmpty());
    }

    @Test
    void testDeadlockDetection() {
        WorkflowStep step1 = WorkflowStep.builder()
                .name("step1")
                .goal("First")
                .build();

        WorkflowStep step2 = WorkflowStep.builder()
                .name("step2")
                .goal("Second")
                .build();

        WorkflowStep step3 = WorkflowStep.builder()
                .name("step3")
                .goal("Third")
                .build();

        graph.addStep(step1);
        graph.addStep(step2);
        graph.addStep(step3);

        // Create cycle: step1 -> step2 -> step3 -> step1
        graph.addDependency("step1", "step2");
        graph.addDependency("step2", "step3");
        graph.addDependency("step3", "step1");

        assertTrue(graph.detectDeadlock());
    }

    @Test
    void testNoDeadlock() {
        WorkflowStep step1 = WorkflowStep.builder()
                .name("step1")
                .goal("First")
                .build();

        WorkflowStep step2 = WorkflowStep.builder()
                .name("step2")
                .goal("Second")
                .build();

        graph.addStep(step1);
        graph.addStep(step2);
        graph.addDependency("step2", "step1");

        assertFalse(graph.detectDeadlock());
    }

    @Test
    void testGetDependents() {
        WorkflowStep step1 = WorkflowStep.builder()
                .name("step1")
                .goal("First")
                .build();

        WorkflowStep step2 = WorkflowStep.builder()
                .name("step2")
                .goal("Second")
                .build();

        WorkflowStep step3 = WorkflowStep.builder()
                .name("step3")
                .goal("Third")
                .build();

        graph.addStep(step1);
        graph.addStep(step2);
        graph.addStep(step3);
        graph.addDependency("step2", "step1");
        graph.addDependency("step3", "step1");

        Set<String> dependents = graph.getDependents("step1");
        assertEquals(2, dependents.size());
        assertTrue(dependents.contains("step2"));
        assertTrue(dependents.contains("step3"));
    }

    @Test
    void testStatusSummary() {
        WorkflowStep step1 = WorkflowStep.builder()
                .name("step1")
                .goal("First")
                .build();

        WorkflowStep step2 = WorkflowStep.builder()
                .name("step2")
                .goal("Second")
                .build();

        graph.addStep(step1);
        graph.addStep(step2);
        graph.addDependency("step2", "step1");

        graph.markCompleted("step1");

        Map<String, Integer> summary = graph.getStatusSummary();
        assertEquals(2, summary.get("total"));
        assertEquals(1, summary.get("completed"));
        assertEquals(0, summary.get("skipped"));
        assertEquals(1, summary.get("pending"));
    }

    @Test
    void testReset() {
        WorkflowStep step = WorkflowStep.builder()
                .name("step1")
                .goal("First")
                .build();

        graph.addStep(step);
        graph.markCompleted("step1");

        assertTrue(graph.isCompleted("step1"));

        graph.reset();

        assertFalse(graph.isCompleted("step1"));
        assertNotNull(graph.getStep("step1")); // Step definition preserved
    }

    @Test
    void testHasPending() {
        WorkflowStep step1 = WorkflowStep.builder()
                .name("step1")
                .goal("First")
                .build();

        WorkflowStep step2 = WorkflowStep.builder()
                .name("step2")
                .goal("Second")
                .build();

        graph.addStep(step1);
        graph.addStep(step2);

        assertTrue(graph.hasPending());

        graph.markCompleted("step1");
        assertTrue(graph.hasPending());

        graph.markCompleted("step2");
        assertFalse(graph.hasPending());
    }

    @Test
    void testHasOnlySkippedPending() {
        WorkflowStep step1 = WorkflowStep.builder()
                .name("step1")
                .goal("First")
                .build();

        WorkflowStep step2 = WorkflowStep.builder()
                .name("step2")
                .goal("Second")
                .build();

        graph.addStep(step1);
        graph.addStep(step2);
        graph.addDependency("step2", "step1");

        assertFalse(graph.hasOnlySkippedPending());

        graph.markSkipped("step1");
        assertTrue(graph.hasOnlySkippedPending());
    }
}
