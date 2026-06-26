/**
 * Guardrails module for content safety.
 *
 * Provides two layers of content safety:
 * - Layer 1: PII detection using regex and NLP rules
 * - Layer 2: LLM-based content judge for complex cases
 *
 * Key components:
 * - {@link com.harness.guardrails.GuardrailConfig} - Main configuration
 * - {@link com.harness.guardrails.ComplianceJudge} - LLM-based content judge
 * - {@link com.harness.guardrails.JudgeResult} - Safety assessment result
 *
 * Example:
 * <pre>
 * GuardrailConfig config = GuardrailConfig.builder()
 *     .enabled(true)
 *     .layer1Enabled(true)
 *     .layer2Enabled(true)
 *     .judgeEndpoint("http://localhost:8000/v1/chat/completions")
 *     .build();
 *
 * ComplianceJudge judge = new ComplianceJudge(config.getJudgeConfig());
 *
 * JudgeResult result = judge.judge("Content to check");
 * if (!result.isSafe()) {
 *     throw new ContentRiskException(result);
 * }
 * </pre>
 */
package com.harness.guardrails;
