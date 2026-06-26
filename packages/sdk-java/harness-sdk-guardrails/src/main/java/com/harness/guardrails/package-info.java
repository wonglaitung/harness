/**
 * Guardrails module for content safety.
 *
 * Provides two layers of content safety:
 * - Layer 1: PII detection using regex and NLP rules (fast, &lt;1ms)
 * - Layer 2: LLM-based content judge for complex cases (~100ms)
 *
 * Key components:
 * - {@link com.harness.guardrails.GuardrailConfig} - Main configuration
 * - {@link com.harness.guardrails.JudgeConfig} - Layer 2 Judge configuration
 * - {@link com.harness.guardrails.StreamInterceptConfig} - Stream interception configuration
 * - {@link com.harness.guardrails.ComplianceJudge} - LLM-based content judge
 * - {@link com.harness.guardrails.JudgeResult} - Safety assessment result
 * - {@link com.harness.guardrails.PIIDetector} - PII detection engine
 * - {@link com.harness.guardrails.PIIEntity} - Detected PII entity
 * - {@link com.harness.guardrails.GuardrailHook} - Lifecycle hook for PII detection
 * - {@link com.harness.guardrails.StreamInterceptor} - Real-time stream monitoring
 *
 * Example (PII Detection):
 * <pre>
 * PIIDetector detector = PIIDetector.create();
 * String text = "My phone is 13812345678";
 * List&lt;PIIEntity&gt; entities = detector.detect(text);
 * String redacted = detector.redact(text);
 * </pre>
 *
 * Example (GuardrailHook):
 * <pre>
 * GuardrailConfig config = GuardrailConfig.builder()
 *     .enabled(true)
 *     .layer1Enabled(true)
 *     .redactPii(true)
 *     .build();
 *
 * GuardrailHook hook = new GuardrailHook(config);
 * agent.addHook(hook);
 * </pre>
 *
 * Example (Content Judge):
 * <pre>
 * JudgeConfig judgeConfig = JudgeConfig.builder()
 *     .enabled(true)
 *     .endpoint("http://localhost:8001/v1/chat/completions")
 *     .build();
 *
 * ComplianceJudge judge = new ComplianceJudge(judgeConfig);
 * JudgeResult result = judge.judge("Content to check").join();
 * if (!result.isSafe()) {
 *     throw new ContentRiskException(result);
 * }
 * </pre>
 */
package com.harness.guardrails;
