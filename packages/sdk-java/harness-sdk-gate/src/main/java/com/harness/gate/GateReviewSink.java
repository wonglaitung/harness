package com.harness.gate;

import java.util.List;
import java.util.Map;

/**
 * Decoupling seam for human-in-the-loop escalation. Failed verdicts are
 * submitted here (best-effort, never blocking delivery) so the gate module
 * stays independent of any specific review-queue implementation.
 */
public interface GateReviewSink {
    void submit(GateReviewItem item);
}
