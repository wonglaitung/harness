package com.harness.testing;

import java.util.ArrayList;
import java.util.List;

import com.harness.integration.AgentHarness;
import com.harness.types.LoopResult;
import com.harness.types.Session;

/**
 * RecordingHarness - records agent interactions for testing.
 *
 * Note: This is a simplified implementation. Full implementation pending.
 */
public class RecordingHarness {

    private final AgentHarness delegate;
    private final RecordingConfig config;
    private final List<RecordedInteraction> recordings = new ArrayList<>();

    private RecordingHarness(AgentHarness delegate, RecordingConfig config) {
        this.delegate = delegate;
        this.config = config;
    }

    /**
     * Create a recording wrapper around an AgentHarness.
     */
    public static RecordingHarness record(AgentHarness delegate) {
        return new RecordingHarness(delegate, RecordingConfig.defaults());
    }

    /**
     * Create a recording wrapper with custom config.
     */
    public static RecordingHarness record(AgentHarness delegate, RecordingConfig config) {
        return new RecordingHarness(delegate, config);
    }

    /**
     * Run and record the interaction.
     */
    public LoopResult run(String prompt) {
        LoopResult result = delegate.run(prompt).join();
        recordings.add(new RecordedInteraction(prompt, result));
        return result;
    }

    /**
     * Get all recordings.
     */
    public List<RecordedInteraction> getRecordings() {
        return List.copyOf(recordings);
    }

    /**
     * Clear recordings.
     */
    public void clear() {
        recordings.clear();
    }

    /**
     * Recorded interaction.
     */
    public record RecordedInteraction(
        String prompt,
        LoopResult result
    ) {}
}