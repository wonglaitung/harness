package com.harness.gate;

import com.harness.gate.models.GateFinding;

import java.util.List;
import java.util.Map;

/**
 * Validators implement {@link #check} returning findings. The LLM never
 * participates in the verdict — validation is 100% deterministic code.
 */
public interface GateValidator {
    List<GateFinding> check(
            String content,
            List<String> sources,
            List<Map<String, Object>> toolRecords);
}
