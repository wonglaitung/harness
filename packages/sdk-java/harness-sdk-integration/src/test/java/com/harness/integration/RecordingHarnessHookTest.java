package com.harness.integration;

import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;

import org.junit.jupiter.api.Test;

import com.harness.llm.MockLLMClient;
import com.harness.llm.MockResponse;
import com.harness.recording.RecordedInteraction;
import com.harness.recording.RecordingConfig;
import com.harness.recording.RecordingHarness;

class RecordingHarnessHookTest {

    @Test
    void runAutoRecordsLlmInteractions() {
        MockLLMClient llm = new MockLLMClient();
        llm.addResponse(MockResponse.text("recorded response"));

        AgentHarness agent = AgentHarness.builder()
                .llmClient(llm)
                .build();

        RecordingConfig config = new RecordingConfig.Builder()
                .autoSave(false)
                .build();
        RecordingHarness recorder = new RecordingHarness(agent, config);

        recorder.run("hi").join();

        List<RecordedInteraction> interactions = recorder.getInteractions();
        assertTrue(interactions.stream().anyMatch(i -> "llm_request".equals(i.getType())));
        assertTrue(interactions.stream().anyMatch(i -> "llm_response".equals(i.getType())));
        assertTrue(interactions.stream().anyMatch(i -> "loop_result".equals(i.getType())));
    }
}
