package com.harness.recording;

import java.util.concurrent.CompletableFuture;

import com.harness.core.LifecycleHook;
import com.harness.types.LoopResult;

/**
 * Minimal contract a harness must expose so {@link RecordingHarness} can
 * register an auto-recording hook and drive the wrapped harness.
 */
public interface HookAwareHarness {

    /**
     * Register a lifecycle hook.
     */
    void addHook(LifecycleHook hook);

    /**
     * Run the harness for a session.
     */
    CompletableFuture<LoopResult> run(String prompt, String sessionId);
}
