package com.harness.gate.reconciliation;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;

class ReconcilerTest {

    @Test
    void redactKeepsContentWhenNoUnsourcedClaims() {
        assertEquals("hello", Reconciler.redact("hello", Map.of("unsourced_claims", List.of())));
    }

    @Test
    void redactReplacesUnsourcedClaims() {
        Map<String, Object> report = Map.of("unsourced_claims", List.of("secret"));
        assertEquals("a [已隔离:无溯源] b", Reconciler.redact("a secret b", report));
    }

    @Test
    void redactQuarantinesWhenClaimCannotBeLocated() {
        Map<String, Object> report = Map.of("unsourced_claims", List.of("missing"));
        assertEquals(
                "[内容未通过确定性闸门（含错误级发现），已隔离，不交付原始内容]",
                Reconciler.redact("a secret b", report));
    }
}
