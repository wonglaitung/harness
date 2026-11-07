package com.harness.core;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.file.Files;
import java.nio.file.Path;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class MockHarnessRecordingTest {

    @TempDir
    Path tempDir;

    @Test
    void loadsInteractionsRecording() throws Exception {
        Path recording = tempDir.resolve("recording.json");
        Files.writeString(recording, """
                {
                  "interactions": [
                    {
                      "type": "llm_response",
                      "data": {
                        "content": "",
                        "tool_calls": [
                          {"id": "1", "name": "query_balance", "arguments": {}}
                        ],
                        "stop_reason": "tool_use"
                      }
                    },
                    {
                      "type": "tool_result",
                      "data": {
                        "tool_name": "query_balance",
                        "result": "1200",
                        "success": true
                      }
                    },
                    {
                      "type": "llm_response",
                      "data": {
                        "content": "ok",
                        "tool_calls": [],
                        "stop_reason": "end_turn"
                      }
                    }
                  ]
                }
                """);

        MockHarness mock = new MockHarness();
        mock.loadRecording(recording);

        MockHarness.MockLoopResult result = mock.run("hi").join();
        assertEquals("ok", result.finalResponse());
        assertTrue(result.messages().stream()
                .anyMatch(m -> "tool".equals(m.role()) && "1200".equals(m.content())));
    }
}
