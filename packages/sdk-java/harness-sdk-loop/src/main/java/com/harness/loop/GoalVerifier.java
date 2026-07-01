package com.harness.loop;

import com.harness.loop.types.GoalConfig;
import com.harness.loop.types.GoalResult;
import com.harness.loop.types.VerificationMethod;
import com.harness.loop.types.VerificationRecord;
import com.harness.loop.types.VerificationResult;
import com.harness.core.LLMClient;
import com.harness.types.LLMResponse;
import com.harness.types.Message;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import java.util.function.Function;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Verifies if a goal has been achieved.
 *
 * <p>This class is stateless - all context is passed via parameters.
 * Supports multiple verification methods with fault tolerance.</p>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * GoalVerifier verifier = new GoalVerifier(config, llmClient);
 *
 * VerificationResult result = verifier.verify(goalResult).join();
 *
 * if (result.isAchieved()) {
 *     System.out.println("Goal achieved!");
 * } else if (result.shouldRetry()) {
 *     System.out.println("Verifier fault, should retry");
 * }
 * }</pre>
 */
public class GoalVerifier {
    private static final Logger logger = LoggerFactory.getLogger(GoalVerifier.class);

    private static final String DEFAULT_VERIFICATION_PROMPT = """
# Goal Verification

## Original Goal
%s

## Success Criteria
%s

## Agent's Final Response
%s

## Your Task
Determine if the goal has been achieved. Respond in JSON format:
{
    "achieved": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of your judgment"
}

Be strict but fair. Only mark as achieved if the agent has clearly completed the goal.""";

    private final GoalConfig config;
    private final LLMClient llmClient;
    private final List<VerificationRecord> verificationHistory;

    /**
     * Create a new GoalVerifier.
     *
     * @param config Goal configuration
     * @param llmClient LLM client for LLM verification (optional if using custom verifier)
     */
    public GoalVerifier(GoalConfig config, LLMClient llmClient) {
        this.config = config;
        this.llmClient = llmClient;
        this.verificationHistory = new ArrayList<>();

        // Validate configuration
        if (config.getVerificationMethod() == VerificationMethod.LLM && llmClient == null) {
            throw new IllegalArgumentException("LLM client is required when verificationMethod is LLM");
        }
    }

    /**
     * Create a new GoalVerifier without LLM client (for custom verification).
     *
     * @param config Goal configuration
     */
    public GoalVerifier(GoalConfig config) {
        this(config, null);
    }

    /**
     * Get the history of verification attempts (read-only).
     */
    public List<VerificationRecord> getVerificationHistory() {
        return Collections.unmodifiableList(verificationHistory);
    }

    /**
     * Verify if the goal has been achieved.
     *
     * @param result The GoalResult from agent execution
     * @return CompletableFuture with VerificationResult
     */
    public CompletableFuture<VerificationResult> verify(GoalResult result) {
        return verify(result, new HashMap<>());
    }

    /**
     * Verify if the goal has been achieved.
     *
     * @param result The GoalResult from agent execution
     * @param context Additional context for verification
     * @return CompletableFuture with VerificationResult
     */
    public CompletableFuture<VerificationResult> verify(GoalResult result, Map<String, Object> context) {
        int maxRetries = config.getVerifierMaxRetries();
        double delay = config.getVerifierRetryDelay();

        return verifyWithRetry(result, context, 0, maxRetries, delay);
    }

    private CompletableFuture<VerificationResult> verifyWithRetry(
            GoalResult result,
            Map<String, Object> context,
            int attempt,
            int maxRetries,
            double delay) {

        return verifyOnce(result, context)
                .thenApply(verification -> {
                    // Record successful verification
                    verificationHistory.add(new VerificationRecord.Builder()
                            .iteration(result.totalIterations())
                            .achieved(verification.isAchieved())
                            .confidence(verification.getConfidence())
                            .reasoning(verification.getReasoning())
                            .method(config.getVerificationMethod())
                            .build());

                    return verification;
                })
                .exceptionallyCompose(error -> {
                    int nextAttempt = attempt + 1;

                    if (nextAttempt <= maxRetries && shouldRetry(error)) {
                        logger.warn("Verification attempt {}/{} failed: {}. Retrying in {}s...",
                                nextAttempt, maxRetries, error.getMessage(), delay);

                        // Delay and retry with new attempt count
                        double nextDelay = delay * config.getVerifierRetryBackoff();
                        return CompletableFuture.runAsync(() -> {
                                    try {
                                        Thread.sleep((long) (delay * 1000));
                                    } catch (InterruptedException e) {
                                        Thread.currentThread().interrupt();
                                    }
                                }, CompletableFuture.delayedExecutor((long) delay, TimeUnit.SECONDS))
                                .thenCompose(v -> verifyWithRetry(result, context, nextAttempt, maxRetries, nextDelay));
                    } else {
                        // Max retries reached or non-retryable error
                        logger.error("Verification failed after {} attempts: {}", nextAttempt, error.getMessage());

                        verificationHistory.add(new VerificationRecord.Builder()
                                .iteration(result.totalIterations())
                                .achieved(false)
                                .confidence(0.0)
                                .reasoning("Verifier fault: " + error.getMessage())
                                .method(config.getVerificationMethod())
                                .error(error.getMessage())
                                .build());

                        return CompletableFuture.completedFuture(
                                VerificationResult.fault(error.getMessage(), false));
                    }
                });
    }

    private boolean shouldRetry(Throwable error) {
        String errorStr = error.getMessage().toLowerCase();
        return errorStr.contains("rate limit") ||
                errorStr.contains("timeout") ||
                errorStr.contains("503") ||
                errorStr.contains("502") ||
                errorStr.contains("429");
    }

    private CompletableFuture<VerificationResult> verifyOnce(GoalResult result, Map<String, Object> context) {
        VerificationMethod method = config.getVerificationMethod();

        return switch (method) {
            case CUSTOM -> verifyCustom(result, context);
            case LLM -> verifyLLM(result, context);
            case TOOL -> verifyTool(result, context);
        };
    }

    private CompletableFuture<VerificationResult> verifyCustom(GoalResult result, Map<String, Object> context) {
        Function<GoalResult, Boolean> verifier = config.getCustomVerifier();

        if (verifier == null) {
            return CompletableFuture.failedFuture(
                    new VerificationException("No custom verifier provided", false));
        }

        try {
            Boolean achieved = verifier.apply(result);

            if (achieved == null) {
                achieved = false;
            }

            return CompletableFuture.completedFuture(new VerificationResult.Builder()
                    .achieved(achieved)
                    .confidence(achieved ? 1.0 : 0.0)
                    .reasoning("Custom verifier result")
                    .build());
        } catch (Exception e) {
            logger.error("Custom verifier raised exception", e);
            return CompletableFuture.failedFuture(
                    new VerificationException("Custom verifier error: " + e.getMessage(), false));
        }
    }

    private CompletableFuture<VerificationResult> verifyLLM(GoalResult result, Map<String, Object> context) {
        if (llmClient == null) {
            return CompletableFuture.failedFuture(
                    new VerificationException("LLM client not available", false));
        }

        // Build verification prompt
        String prompt = buildVerificationPrompt(result);

        // Call LLM for verification
        List<Message> messages = new ArrayList<>();
        messages.add(new Message("user", prompt));

        return llmClient.callAsync(messages, null, "You are a goal verification assistant. Respond only in valid JSON format.")
                .thenApply(response -> {
                    String responseText = response.content() != null ? response.content() : "";
                    return parseLLMResponse(responseText);
                })
                .exceptionally(error -> {
                    throw new VerificationException("LLM verification error: " + error.getMessage(),
                            shouldRetry(error));
                });
    }

    private CompletableFuture<VerificationResult> verifyTool(GoalResult result, Map<String, Object> context) {
        // TODO: Implement tool-based verification
        return CompletableFuture.failedFuture(
                new VerificationException("Tool verification not yet implemented", false));
    }

    private String buildVerificationPrompt(GoalResult result) {
        // Truncate response if too long
        int maxResponseLen = 2000;
        String responseText = result.finalResponse() != null ? result.finalResponse() : "";
        if (responseText.length() > maxResponseLen) {
            responseText = responseText.substring(0, maxResponseLen) + "\n... (truncated)";
        }

        String successCriteria = config.getSuccessCriteria() != null ?
                config.getSuccessCriteria() : "Goal is achieved when the task is complete.";

        return String.format(DEFAULT_VERIFICATION_PROMPT,
                config.getDescription(),
                successCriteria,
                responseText);
    }

    private VerificationResult parseLLMResponse(String responseText) {
        // Try direct JSON parse
        try {
            Map<String, Object> data = parseJson(responseText);
            return buildResultFromMap(data);
        } catch (Exception e) {
            // Continue to try other methods
        }

        // Try extracting JSON from markdown code blocks
        Pattern jsonPattern = Pattern.compile("```(?:json)?\\s*([\\s\\S]*?)```");
        Matcher matcher = jsonPattern.matcher(responseText);
        while (matcher.find()) {
            try {
                Map<String, Object> data = parseJson(matcher.group(1).trim());
                return buildResultFromMap(data);
            } catch (Exception e) {
                // Continue to next match
            }
        }

        // Try finding JSON-like content
        Pattern jsonPattern2 = Pattern.compile("\\{[\\s\\S]*\\}");
        Matcher matcher2 = jsonPattern2.matcher(responseText);
        while (matcher2.find()) {
            try {
                Map<String, Object> data = parseJson(matcher2.group());
                return buildResultFromMap(data);
            } catch (Exception e) {
                // Continue to next match
            }
        }

        // Fallback: keyword detection
        String responseLower = responseText.toLowerCase();
        boolean achieved = (responseLower.contains("achieved") ||
                responseLower.contains("completed") ||
                responseLower.contains("success") ||
                responseLower.contains("done")) &&
                !(responseLower.contains("not achieved") ||
                        responseLower.contains("incomplete") ||
                        responseLower.contains("failed"));

        return new VerificationResult.Builder()
                .achieved(achieved)
                .confidence(0.3)
                .reasoning("Fallback keyword detection (JSON parse failed)")
                .build();
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> parseJson(String json) throws Exception {
        // Use Jackson from core module
        com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
        return mapper.readValue(json, Map.class);
    }

    private VerificationResult buildResultFromMap(Map<String, Object> data) {
        boolean achieved = false;
        if (data.containsKey("achieved")) {
            Object val = data.get("achieved");
            achieved = Boolean.TRUE.equals(val);
        }

        double confidence = 0.5;
        if (data.containsKey("confidence")) {
            Object val = data.get("confidence");
            if (val instanceof Number) {
                confidence = ((Number) val).doubleValue();
            }
        }

        String reasoning = "";
        if (data.containsKey("reasoning")) {
            reasoning = String.valueOf(data.get("reasoning"));
        }

        return new VerificationResult.Builder()
                .achieved(achieved)
                .confidence(confidence)
                .reasoning(reasoning)
                .build();
    }

    /**
     * Clear verification history (for new goal execution).
     */
    public void clearHistory() {
        verificationHistory.clear();
    }

    /**
     * Exception for verification failures.
     */
    public static class VerificationException extends RuntimeException {
        private final boolean shouldRetry;

        public VerificationException(String message, boolean shouldRetry) {
            super(message);
            this.shouldRetry = shouldRetry;
        }

        public boolean shouldRetry() {
            return shouldRetry;
        }
    }
}
