package com.harness.guardrails;

import java.util.*;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.core.*;

/**
 * Lifecycle hook for PII detection and content safety.
 *
 * This hook intercepts messages before they are sent to the LLM
 * and detects/redacts PII.
 *
 * Example:
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
 */
public class GuardrailHook implements LifecycleHook {

    private static final Logger logger = LoggerFactory.getLogger(GuardrailHook.class);

    private final GuardrailConfig config;
    private final PIIDetector piiDetector;

    public GuardrailHook(GuardrailConfig config) {
        this.config = config;
        this.piiDetector = PIIDetector.create();
    }

    public GuardrailHook() {
        this(GuardrailConfig.defaults());
    }

    @Override
    public List<HookPoint> hookPoints() {
        return List.of(
            HookPoint.BEFORE_LLM_CALL,
            HookPoint.AFTER_TOOL_EXECUTE
        );
    }

    @Override
    public HookResult execute(HookContext context) {
        if (!config.isEnabled()) {
            return HookResult.continue_();
        }

        return switch (context.hookPoint()) {
            case BEFORE_LLM_CALL -> handleBeforeLLMCall(context);
            case AFTER_TOOL_EXECUTE -> handleAfterToolExecute(context);
            default -> HookResult.continue_();
        };
    }

    /**
     * Handle BEFORE_LLM_CALL - scan user message for PII.
     */
    private HookResult handleBeforeLLMCall(HookContext context) {
        if (!config.isLayer1Enabled()) {
            return HookResult.continue_();
        }

        // Get the last user message
        String userMessage = context.userMessage();
        if (userMessage == null || userMessage.isEmpty()) {
            return HookResult.continue_();
        }

        // Detect PII
        List<PIIEntity> entities = piiDetector.detect(userMessage);

        if (entities.isEmpty()) {
            return HookResult.continue_();
        }

        // Log detected PII
        logger.info("Detected {} PII entities in user message", entities.size());
        if (config.isAuditLog()) {
            for (PIIEntity entity : entities) {
                logger.debug("PII detected: {} at position {}-{}",
                    entity.getType().getDescription(),
                    entity.getStart(),
                    entity.getEnd()
                );
            }
        }

        // Redact if configured
        if (config.isRedactPii()) {
            String redacted = piiDetector.redact(userMessage);

            // Inject redacted message
            return HookResult.injectMessage(new com.harness.types.Message(
                "user",
                redacted,
                Map.of("pii_detected", true, "pii_count", entities.size())
            ));
        }

        return HookResult.continue_();
    }

    /**
     * Handle AFTER_TOOL_EXECUTE - scan tool output for PII.
     */
    private HookResult handleAfterToolExecute(HookContext context) {
        if (!config.isLayer1Enabled()) {
            return HookResult.continue_();
        }

        // Get tool output
        String output = context.toolOutput();
        if (output == null || output.isEmpty()) {
            return HookResult.continue_();
        }

        // Detect PII
        List<PIIEntity> entities = piiDetector.detect(output);

        if (entities.isEmpty()) {
            return HookResult.continue_();
        }

        // Log detected PII
        logger.info("Detected {} PII entities in tool output from {}", entities.size(), context.toolName());

        // Redact if configured
        if (config.isRedactPii()) {
            String redacted = piiDetector.redact(output);

            // Return modified result
            return HookResult.modifyToolOutput(redacted);
        }

        return HookResult.continue_();
    }

    /**
     * Get PII detector for custom use.
     */
    public PIIDetector getPiiDetector() {
        return piiDetector;
    }
}
