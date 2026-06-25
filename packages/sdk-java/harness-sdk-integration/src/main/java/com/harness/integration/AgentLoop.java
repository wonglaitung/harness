package com.harness.integration;

import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
import java.util.function.Consumer;
import java.util.Random;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.memory.SessionManager;
import com.harness.security.AuditLogger;
import com.harness.security.InputValidator;
import com.harness.security.ResultSanitizer;
import com.harness.types.*;

/**
 * Agent loop - the core execution engine.
 *
 * Implements a ReAct-style loop:
 * 1. Build context from session
 * 2. Call LLM
 * 3. Execute tools if needed
 * 4. Repeat until done
 *
 * Robustness features:
 * - LLM retry with exponential backoff and jitter
 * - Tool execution timeout protection
 * - Circuit breaker for repeated failures
 * - Stuck detection (empty/error/semantic)
 * - Step budget control
 * - Cost control
 * - Output offloading for large results
 * - Progress events
 * - Snapshot and resume
 */
public class AgentLoop {

    private static final Logger logger = LoggerFactory.getLogger(AgentLoop.class);
    private static final Random random = new Random();

    // Core components
    private final LLMClient llmClient;
    private final ToolExecutor toolExecutor;
    private final ContextBuilder contextBuilder;
    private final LoopConfig config;
    private final SessionManager sessionManager;

    // Robustness components
    private final ErrorHandler errorHandler;
    private final CircuitBreaker circuitBreaker;
    private final StuckDetector stuckDetector;
    private final StepBudgetController stepBudget;
    private final CostController costController;
    private final OutputOffloader outputOffloader;

    // Security components
    private final InputValidator inputValidator;
    private final ResultSanitizer sanitizer;
    private final AuditLogger auditLogger;

    // State
    private volatile LoopState state = LoopState.IDLE;
    private final AtomicBoolean interrupted = new AtomicBoolean(false);
    private final AtomicInteger iteration = new AtomicInteger(0);
    private final AtomicInteger stuckFeedbackCount = new AtomicInteger(0);
    private final AtomicBoolean circuitBreakerStopInjected = new AtomicBoolean(false);

    // Hooks
    private final List<LifecycleHook> hooks = new CopyOnWriteArrayList<>();

    // Progress callback
    private Consumer<ProgressEvent> onProgress;
    private long loopStartTime;

    // Constructors

    public AgentLoop(LLMClient llmClient, ToolExecutor toolExecutor, LoopConfig config) {
        this.llmClient = llmClient;
        this.toolExecutor = toolExecutor;
        this.config = config;
        this.contextBuilder = new ContextBuilder();
        this.sessionManager = null;

        // Initialize robustness components
        this.errorHandler = new ErrorHandler();
        this.circuitBreaker = config.enableCircuitBreaker() ? new CircuitBreaker() : null;
        this.stuckDetector = new StuckDetector();
        this.stepBudget = new StepBudgetController();
        this.costController = config.enableCostControl() ? new CostController() : null;
        this.outputOffloader = new OutputOffloader();

        // Initialize security components
        this.inputValidator = new InputValidator();
        this.sanitizer = new ResultSanitizer();
        this.auditLogger = new AuditLogger();
    }

    public AgentLoop(LLMClient llmClient, ToolExecutor toolExecutor, SessionManager sessionManager, LoopConfig config) {
        this.llmClient = llmClient;
        this.toolExecutor = toolExecutor;
        this.config = config;
        this.contextBuilder = new ContextBuilder();
        this.sessionManager = sessionManager;

        // Initialize robustness components
        this.errorHandler = new ErrorHandler();
        this.circuitBreaker = config.enableCircuitBreaker() ? new CircuitBreaker() : null;
        this.stuckDetector = new StuckDetector();
        this.stepBudget = new StepBudgetController();
        this.costController = config.enableCostControl() ? new CostController() : null;
        this.outputOffloader = new OutputOffloader();

        // Initialize security components
        this.inputValidator = new InputValidator();
        this.sanitizer = new ResultSanitizer();
        this.auditLogger = new AuditLogger();
    }

    public AgentLoop(LLMClient llmClient, ToolExecutor toolExecutor) {
        this(llmClient, toolExecutor, LoopConfig.defaults());
    }

    // -------------------------------------------------------------------------
    // Public API
    // -------------------------------------------------------------------------

    /**
     * Run the agent loop synchronously.
     */
    public LoopResult run(String prompt, Session session) {
        return runAsync(prompt, session).join();
    }

    /**
     * Run the agent loop with default session.
     */
    public LoopResult run(String prompt) {
        return run(prompt, Session.create());
    }

    /**
     * Run the agent loop asynchronously.
     */
    public CompletableFuture<LoopResult> runAsync(String prompt, Session session) {
        return runAsync(prompt, session, null, null);
    }

    /**
     * Run the agent loop with tools.
     */
    public CompletableFuture<LoopResult> run(String prompt, Session session,
            List<Map<String, Object>> tools, Consumer<ProgressEvent> onProgress) {
        return runAsync(prompt, session, tools, onProgress);
    }

    /**
     * Run the agent loop asynchronously with tools.
     */
    public CompletableFuture<LoopResult> runAsync(String prompt, Session session,
            List<Map<String, Object>> tools, Consumer<ProgressEvent> onProgress) {
        return CompletableFuture.supplyAsync(() -> executeLoop(prompt, session, tools, onProgress));
    }

    /**
     * Interrupt the current loop.
     */
    public void interrupt() {
        interrupted.set(true);
    }

    /**
     * Get current state.
     */
    public LoopState getState() {
        return state;
    }

    /**
     * Get current iteration.
     */
    public int getIteration() {
        return iteration.get();
    }

    /**
     * Add a lifecycle hook.
     */
    public void addHook(LifecycleHook hook) {
        hooks.add(hook);
    }

    /**
     * Remove a lifecycle hook.
     */
    public void removeHook(LifecycleHook hook) {
        hooks.remove(hook);
    }

    /**
     * Get all registered hooks.
     */
    public List<LifecycleHook> getHooks() {
        return new ArrayList<>(hooks);
    }

    // -------------------------------------------------------------------------
    // Main Loop Execution
    // -------------------------------------------------------------------------

    private LoopResult executeLoop(String prompt, Session session, List<Map<String, Object>> tools,
                                    Consumer<ProgressEvent> progressCallback) {
        logger.info("Starting agent loop, maxIterations={}", config.maxIterations());

        // Initialize state
        this.onProgress = progressCallback;
        this.loopStartTime = System.currentTimeMillis();
        interrupted.set(false);
        iteration.set(0);
        state = LoopState.IDLE;
        stuckFeedbackCount.set(0);
        circuitBreakerStopInjected.set(false);
        errorHandler.reset();

        // Reset circuit breaker for new task
        if (circuitBreaker != null) {
            circuitBreaker.reset();
        }

        // Start step budget task
        if (stepBudget != null) {
            stepBudget.startTask();
        }

        TokenUsage totalUsage = new TokenUsage();

        // Input validation
        if (inputValidator != null) {
            var validationResult = inputValidator.validate(prompt);
            if (!validationResult.valid()) {
                throw new IllegalArgumentException("Invalid input: " + validationResult.errors());
            }
            if (!validationResult.warnings().isEmpty()) {
                emitProgress(ProgressEventType.WARNING,
                    "Input validation warnings: " + validationResult.warnings(),
                    Map.of("warnings", validationResult.warnings()));
            }
        }

        // Emit loop start
        String promptPreview = prompt != null && prompt.length() > 100
            ? prompt.substring(0, 100) + "..."
            : prompt;
        emitProgress(ProgressEventType.LOOP_START, "Starting agent loop",
            Map.of("prompt", promptPreview, "session_id", session.id()));

        // Execute ON_LOOP_START hooks
        HookResult hookResult = executeHooks(HookPoint.ON_LOOP_START, session, 0, null, null, null);
        if (hookResult.action() == HookAction.ABORT) {
            state = LoopState.ERROR;
            return LoopResult.error(session, 0, hookResult.metadata().getOrDefault("reason", "Aborted by hook").toString());
        }

        // Add user message to session
        if (prompt != null && !prompt.isEmpty()) {
            session = session.addMessage(Message.user(prompt));
        }

        try {
            while (iteration.get() < config.maxIterations()) {
                // Check step budget
                if (stepBudget != null && iteration.get() > 0) {
                    BudgetCheckResult budgetResult = stepBudget.advanceIteration();
                    if (budgetResult.shouldStop()) {
                        state = LoopState.ERROR;
                        emitProgress(ProgressEventType.ERROR, budgetResult.message(),
                            Map.of("step_budget", stepBudget.getUsageReport()));
                        return LoopResult.error(session, iteration.get(), budgetResult.message());
                    }
                }

                // Check cost budget
                if (costController != null) {
                    BudgetStatus budgetStatus = costController.check(totalUsage, session.id());
                    if (!budgetStatus.isWithinBudget()) {
                        state = LoopState.ERROR;
                        emitProgress(ProgressEventType.ERROR,
                            budgetStatus.warningMessage() != null ? budgetStatus.warningMessage() : "Budget exceeded",
                            Map.of("total_tokens", totalUsage.totalTokens(),
                                   "limit", costController.getStats().get("config")));
                        return LoopResult.error(session, iteration.get(), "Budget exceeded");
                    }
                }

                // Emit iteration event
                emitProgress(ProgressEventType.ITERATION,
                    String.format("Iteration %d/%d", iteration.get() + 1, config.maxIterations()),
                    Map.of("iteration", iteration.get() + 1));

                // Check for interruption
                if (interrupted.get()) {
                    state = LoopState.INTERRUPTED;
                    emitProgress(ProgressEventType.LOOP_END, "Loop interrupted",
                        Map.of("status", "interrupted", "iterations", iteration.get()));
                    return LoopResult.interrupted(session, iteration.get());
                }

                // Build context
                state = LoopState.BUILDING_CONTEXT;
                long contextStart = System.currentTimeMillis();
                emitProgress(ProgressEventType.STATE_CHANGE, "Building context",
                    Map.of("state", LoopState.BUILDING_CONTEXT.getValue()));

                // Add remaining steps hint
                int remainingSteps = config.maxIterations() - iteration.get();
                if (remainingSteps <= 2 && iteration.get() > 0) {
                    String hint = String.format("[系统提示] 还有 %d 步达到迭代上限。请立即总结当前进展并给出最终回答。", remainingSteps);
                    session = session.addMessage(Message.user(hint));
                }

                ContextBuilder.Context context = contextBuilder.build(session);
                long contextDuration = System.currentTimeMillis() - contextStart;

                // Call LLM
                state = LoopState.CALLING_LLM;
                long llmStart = System.currentTimeMillis();
                emitProgress(ProgressEventType.LLM_CALL, "Calling LLM: " + llmClient.modelName(),
                    Map.of("model", llmClient.modelName(), "message_count", context.messages().size()));

                // Execute BEFORE_LLM_CALL hooks
                hookResult = executeHooks(HookPoint.BEFORE_LLM_CALL, session, iteration.get(), context.messages(), null, null);
                if (hookResult.action() == HookAction.ABORT) {
                    state = LoopState.ERROR;
                    return LoopResult.error(session, iteration.get(),
                        hookResult.metadata().getOrDefault("reason", "Aborted by hook").toString());
                }
                if (hookResult.action() == HookAction.INJECT_MESSAGE && hookResult.injectMessage() != null) {
                    session = session.addMessage(hookResult.injectMessage());
                }

                // LLM call with retry
                LLMResponse response = callLLMWithRetry(context, convertTools(toolExecutor.listTools()));

                if (response == null) {
                    state = LoopState.ERROR;
                    return LoopResult.error(session, iteration.get(), "LLM call failed after all retries");
                }

                long llmDuration = System.currentTimeMillis() - llmStart;

                // Execute AFTER_LLM_CALL hooks
                hookResult = executeHooks(HookPoint.AFTER_LLM_CALL, session, iteration.get(), null, response, null);
                if (hookResult.action() == HookAction.ABORT) {
                    state = LoopState.ERROR;
                    return LoopResult.error(session, iteration.get(),
                        hookResult.metadata().getOrDefault("reason", "Aborted by hook").toString());
                }

                // Emit LLM response
                String contentPreview = response.content() != null && response.content().length() > 500
                    ? response.content().substring(0, 500) + "..."
                    : response.content();
                emitProgress(ProgressEventType.LLM_RESPONSE, "LLM responded",
                    Map.of(
                        "stop_reason", response.stopReason().getValue(),
                        "input_tokens", response.usage().inputTokens(),
                        "output_tokens", response.usage().outputTokens(),
                        "content", contentPreview,
                        "has_tool_calls", response.isToolUse(),
                        "tool_names", response.isToolUse()
                            ? response.toolCalls().stream().map(ToolCall::name).toList()
                            : List.of()
                    ),
                    llmDuration);

                // Update usage
                totalUsage = totalUsage.add(response.usage());

                // Add assistant message (skip if empty and has tool calls)
                if (response.content() != null && !response.content().isEmpty() || !response.isToolUse()) {
                    session = session.addMessage(Message.assistant(response.content()));
                }

                // Check if we need tools
                if (response.isToolUse()) {
                    state = LoopState.EXECUTING_TOOLS;
                    emitProgress(ProgressEventType.STATE_CHANGE,
                        String.format("Executing %d tool(s)", response.toolCalls().size()),
                        Map.of("state", LoopState.EXECUTING_TOOLS.getValue(),
                               "tool_count", response.toolCalls().size(),
                               "tools", response.toolCalls().stream().map(ToolCall::name).toList()));

                    // Execute tools
                    List<ToolResult> results = executeToolsWithTimeout(response.toolCalls(), session);

                    // Add tool results and check for circuit breaker
                    boolean hasCircuitBreakerError = false;
                    for (ToolResult result : results) {
                        String content = result.success() ? result.content() : "Error: " + result.error();
                        if (result.error() != null && result.error().contains("Circuit breaker")) {
                            hasCircuitBreakerError = true;
                        }
                        session = session.addMessage(Message.fromToolResult(result));
                    }

                    // Inject circuit breaker stop message if needed
                    if (hasCircuitBreakerError && !circuitBreakerStopInjected.get()) {
                        circuitBreakerStopInjected.set(true);
                        String stopMessage = "[系统强制停止] 工具调用被阻止，因为检测到重复调用相同工具。" +
                            "请立即停止调用工具，基于当前已有信息给出最终回答。不要再尝试调用任何工具。";
                        session = session.addMessage(Message.user(stopMessage));
                        logger.info("Injected circuit breaker stop message");
                        emitProgress(ProgressEventType.STATE_CHANGE,
                            "Circuit breaker triggered, injecting stop message",
                            circuitBreaker != null ? circuitBreaker.getStats() : Map.of());
                    }

                    iteration.incrementAndGet();

                    // Stuck detection
                    StuckDetectionResult stuckResult = checkStuck(session, iteration.get());
                    if (stuckResult.isStuck()) {
                        if (stuckFeedbackCount.get() < config.maxStuckFeedbacks()) {
                            stuckFeedbackCount.incrementAndGet();
                            String feedback = generateStuckFeedback(stuckFeedbackCount.get(), session, stuckResult);
                            session = session.addMessage(Message.user(feedback));
                            emitProgress(ProgressEventType.STATE_CHANGE,
                                String.format("Stuck state detected at iteration %d (%s), injecting feedback (%d/%d)",
                                    iteration.get(), stuckResult.reason(),
                                    stuckFeedbackCount.get(), config.maxStuckFeedbacks()),
                                Map.of("stuck_feedback_count", stuckFeedbackCount.get(),
                                       "stuck_reason", stuckResult.reason(),
                                       "stuck_similarity", stuckResult.similarity()));
                            // Clear stuck detector state
                            if (stuckDetector != null) {
                                stuckDetector.clearSession(session.id());
                            }
                        } else {
                            state = LoopState.STUCK;
                            emitProgress(ProgressEventType.ERROR,
                                "Agent stuck: repeated failures after feedback attempts",
                                Map.of("stuck_feedback_count", stuckFeedbackCount.get(),
                                       "stuck_reason", stuckResult.reason()));
                            return LoopResult.error(session, iteration.get(), "Agent stuck: repeated failures after feedback attempts");
                        }
                    }

                    continue;
                }

                // Done!
                state = LoopState.COMPLETED;
                session = session.withTokenUsage(totalUsage);

                // Execute ON_EXIT_ATTEMPT hooks (for Ralph Loop)
                hookResult = executeHooks(HookPoint.ON_EXIT_ATTEMPT, session, iteration.get(), null, response, null);
                if (hookResult.action() == HookAction.REINJECT) {
                    emitProgress(ProgressEventType.STATE_CHANGE, "Ralph Loop: Reinjecting continuation prompt",
                        Map.of("reason", hookResult.metadata().getOrDefault("reason", "Long task continuation")));
                    // Clear session messages except first user message
                    Message firstUserMsg = null;
                    for (Message m : session.messages()) {
                        if ("user".equals(m.role())) {
                            firstUserMsg = m;
                            break;
                        }
                    }
                    session = new Session(session.id(), new ArrayList<>(), session.createdAt(), session.updatedAt(),
                        session.metadata(), session.tokenUsage(), session.systemPrompt());
                    if (firstUserMsg != null) {
                        session = session.addMessage(firstUserMsg);
                    }
                    if (hookResult.injectMessage() != null) {
                        session = session.addMessage(hookResult.injectMessage());
                    } else {
                        session = session.addMessage(Message.user("[继续] 请继续之前的任务。"));
                    }
                    iteration.incrementAndGet();
                    continue;
                }

                // Emit completion
                long totalDuration = System.currentTimeMillis() - loopStartTime;
                emitProgress(ProgressEventType.LOOP_END, "Loop completed successfully",
                    Map.of("status", "completed", "iterations", iteration.get() + 1, "total_tokens", totalUsage.totalTokens()),
                    totalDuration);

                // Execute ON_LOOP_END hooks
                executeHooks(HookPoint.ON_LOOP_END, session, iteration.get(), null, null, null);

                logger.info("Loop completed at iteration {}, tokens={}", iteration.get(), totalUsage.totalTokens());
                return LoopResult.completed(session, response.content(), iteration.get(), totalUsage);
            }

            // Max iterations reached
            state = LoopState.ERROR;
            emitProgress(ProgressEventType.ERROR, "Max iterations reached", Map.of("iterations", iteration.get()));

            // Execute ON_LOOP_END hooks
            executeHooks(HookPoint.ON_LOOP_END, session, iteration.get(), null, null, null);

            // Try to get final response from last assistant message
            String finalResponse = null;
            for (Message msg : session.messages()) {
                if ("assistant".equals(msg.role()) && msg.contentAsString() != null) {
                    finalResponse = msg.contentAsString();
                }
            }

            return LoopResult.maxIterations(session, iteration.get());

        } catch (Exception e) {
            logger.error("Loop exception: {}", e.getMessage(), e);

            // Execute ON_ERROR hooks
            executeHooks(HookPoint.ON_ERROR, session, iteration.get(), null, null, e);

            state = LoopState.ERROR;
            emitProgress(ProgressEventType.ERROR, "Error: " + e.getMessage(),
                Map.of("error", e.getMessage(), "type", e.getClass().getSimpleName()));

            // Execute ON_LOOP_END hooks
            executeHooks(HookPoint.ON_LOOP_END, session, iteration.get(), null, null, null);

            return LoopResult.error(session, iteration.get(), e.getMessage());

        } finally {
            // End step budget task
            if (stepBudget != null) {
                try {
                    stepBudget.endTask();
                } catch (Exception e) {
                    logger.warn("Error ending step budget task: {}", e.getMessage());
                }
            }
        }
    }

    // -------------------------------------------------------------------------
    // LLM Call with Retry
    // -------------------------------------------------------------------------

    private LLMResponse callLLMWithRetry(ContextBuilder.Context context, List<LLMClient.ToolDefinition> tools) {
        int maxRetries = config.retryOnError();

        for (int attempt = 0; attempt < maxRetries; attempt++) {
            try {
                return llmClient.call(context.messages(), tools, context.systemPrompt());
            } catch (Exception e) {
                logger.warn("LLM call failed (attempt {}/{}): {}", attempt + 1, maxRetries, e.getMessage());

                if (attempt < maxRetries - 1) {
                    ErrorContext errorContext = ErrorContext.builder()
                        .error(e)
                        .iteration(iteration.get())
                        .attempt(attempt + 1)
                        .build();

                    ErrorDecision decision = errorHandler.handle(e, errorContext);

                    if (decision.action() == ErrorAction.RETRY) {
                        double delaySeconds = decision.delaySeconds() > 0
                            ? decision.delaySeconds()
                            : Math.min(Math.pow(2, attempt) + random.nextDouble() * 0.5, 30);

                        logger.info("Retrying in {}s: {}", String.format("%.1f", delaySeconds), decision.message());

                        emitProgress(ProgressEventType.ERROR,
                            String.format("LLM call failed, retrying: %s", decision.message()),
                            Map.of("error", e.getMessage(), "attempt", attempt + 1, "delay", delaySeconds));

                        try {
                            Thread.sleep((long) (delaySeconds * 1000));
                        } catch (InterruptedException ie) {
                            Thread.currentThread().interrupt();
                            logger.warn("Retry sleep interrupted");
                            break;
                        }
                    } else if (decision.action() == ErrorAction.ABORT) {
                        logger.error("Error handler decided to abort: {}", decision.message());
                        break;
                    }
                }
            }
        }

        logger.error("LLM call failed after {} attempts", maxRetries);
        return null;
    }

    // -------------------------------------------------------------------------
    // Tool Execution
    // -------------------------------------------------------------------------

    private List<ToolResult> executeToolsWithTimeout(List<ToolCall> toolCalls, Session session) {
        ToolContext context = ToolContext.builder()
            .sessionId(session.id())
            .workingDirectory(config.workingDirectory())
            .iteration(iteration.get())
            .build();

        List<ToolResult> results = new ArrayList<>();

        for (ToolCall call : toolCalls) {
            // Check step budget before tool call
            if (stepBudget != null) {
                BudgetCheckResult budgetResult = stepBudget.checkBeforeToolCall(call.name());
                if (budgetResult.shouldStop()) {
                    results.add(ToolResult.error(call.id(), call.name(),
                        "Step budget exceeded: " + budgetResult.message()));
                    break;
                }
            }

            // Check circuit breaker
            if (circuitBreaker != null && circuitBreaker.isOpen()) {
                String reason = circuitBreaker.getReason();
                emitProgress(ProgressEventType.ERROR, "Circuit breaker open: " + reason,
                    Map.of("circuit_breaker", circuitBreaker.getStats()));
                results.add(ToolResult.error(call.id(), call.name(), "Circuit breaker open: " + reason));
                continue;
            }

            // Record call for circuit breaker
            if (circuitBreaker != null) {
                circuitBreaker.recordCall(call.name(), call.arguments());
            }

            // Emit tool call start
            emitProgress(ProgressEventType.TOOL_CALL, "Executing: " + call.name(),
                Map.of("tool", call.name(), "tool_call_id", call.id(), "arguments", call.arguments()));

            // Execute BEFORE_TOOL_EXECUTE hooks
            HookResult hookResult = executeHooks(HookPoint.BEFORE_TOOL_EXECUTE, session, iteration.get(), null, null, call);
            if (hookResult.action() == HookAction.ABORT) {
                results.add(ToolResult.error(call.id(), call.name(),
                    hookResult.metadata().getOrDefault("reason", "Aborted by hook").toString()));
                continue;
            }

            long toolStart = System.currentTimeMillis();
            ToolResult result;

            try {
                // Execute with timeout
                result = toolExecutor.execute(call, context)
                    .orTimeout(config.timeoutPerTool(), TimeUnit.MILLISECONDS)
                    .exceptionally(ex -> {
                        if (ex.getCause() instanceof TimeoutException) {
                            logger.warn("Tool {} timed out after {}ms", call.name(), config.timeoutPerTool());
                            return ToolResult.error(call.id(), call.name(),
                                "Tool execution timed out after " + config.timeoutPerTool() + "ms");
                        }
                        return ToolResult.error(call.id(), call.name(), ex.getMessage());
                    })
                    .join();
            } catch (Exception e) {
                result = ToolResult.error(call.id(), call.name(), e.getMessage());
            }

            long toolDuration = System.currentTimeMillis() - toolStart;

            // Record tool call for step budget
            if (stepBudget != null) {
                stepBudget.recordToolCall(call.name());
            }

            // Offload large output if needed
            if (outputOffloader != null && result.success() && result.content() != null) {
                if (outputOffloader.shouldOffload(result.content(), session.id())) {
                    result = outputOffloader.createOffloadedResult(result, session.id());
                    emitProgress(ProgressEventType.STATE_CHANGE,
                        String.format("Offloaded large output from %s", call.name()),
                        Map.of("offloaded", true, "original_size", result.metadata().get("original_size")));
                }
            }

            // Execute AFTER_TOOL_EXECUTE hooks
            hookResult = executeHooks(HookPoint.AFTER_TOOL_EXECUTE, session, iteration.get(), null, null, call);
            if (hookResult.action() == HookAction.INJECT_MESSAGE && hookResult.injectMessage() != null) {
                session = session.addMessage(hookResult.injectMessage());
            }
            if (hookResult.action() == HookAction.MODIFY_RESULT && hookResult.modifiedResult() != null) {
                result = hookResult.modifiedResult();
            }

            // Sanitize output
            if (sanitizer != null && result.success() && result.content() != null) {
                result = new ToolResult(result.toolCallId(), result.success(),
                    sanitizer.sanitize(result.content()), result.error(), result.metadata());
            }

            // Audit log
            if (auditLogger != null) {
                auditLogger.logToolCall(session.id(), call.name(), call.arguments(),
                    result.success() ? "success" : "error",
                    result.error() != null ? Map.of("error", result.error()) : null);
            }

            // Record result for circuit breaker
            if (circuitBreaker != null) {
                if (result.success()) {
                    circuitBreaker.recordSuccess();
                } else {
                    circuitBreaker.recordError(new RuntimeException(result.error()));
                }
            }

            // Emit tool result
            String resultPreview = result.content() != null
                ? result.content().substring(0, Math.min(200, result.content().length()))
                : result.error() != null ? result.error() : "";
            emitProgress(ProgressEventType.TOOL_RESULT,
                String.format("Tool %s: %s", call.name(), result.success() ? "success" : "failed"),
                Map.of("tool", call.name(), "tool_call_id", call.id(), "success", result.success(),
                       "error", result.error(), "result", resultPreview, "metadata", result.metadata()),
                toolDuration);

            results.add(result);
        }

        return results;
    }

    // -------------------------------------------------------------------------
    // Stuck Detection
    // -------------------------------------------------------------------------

    private StuckDetectionResult checkStuck(Session session, int currentIteration) {
        // Fast path: check empty/error patterns
        if (currentIteration < config.stuckMinIterations()) {
            return StuckDetectionResult.notStuck("below_min_iterations");
        }

        List<Message> recent = session.messages().subList(
            Math.max(0, session.messages().size() - 6), session.messages().size());
        List<Message> toolMsgs = recent.stream().filter(m -> "tool".equals(m.role())).toList();

        if (toolMsgs.size() < config.stuckConsecutiveFailures()) {
            // Try semantic detection if enabled
            if (stuckDetector != null) {
                return stuckDetector.check(session.id(), session.messages(), currentIteration);
            }
            return StuckDetectionResult.notStuck("not_enough_tool_messages");
        }

        int n = config.stuckConsecutiveFailures();

        // Check for empty results
        long emptyCount = toolMsgs.subList(toolMsgs.size() - n, toolMsgs.size()).stream()
            .filter(m -> m.contentAsString() == null || m.contentAsString().isBlank())
            .count();
        if (emptyCount >= n) {
            return StuckDetectionResult.stuck("empty", 0, (int) emptyCount, Map.of("empty_count", emptyCount));
        }

        // Check for error results
        long errorCount = toolMsgs.subList(toolMsgs.size() - n, toolMsgs.size()).stream()
            .filter(m -> m.contentAsString() != null && m.contentAsString().startsWith("Error:"))
            .count();
        if (errorCount >= n) {
            return StuckDetectionResult.stuck("error", 0, (int) errorCount, Map.of("error_count", errorCount));
        }

        // Semantic detection
        if (stuckDetector != null) {
            return stuckDetector.check(session.id(), session.messages(), currentIteration);
        }

        return StuckDetectionResult.notStuck("no_stuck");
    }

    private String generateStuckFeedback(int feedbackCount, Session session, StuckDetectionResult detectionResult) {
        if (detectionResult.reason().equals("semantic_repeat") && detectionResult.similarity() > 0) {
            String similarityStr = String.format("%.0f%%", detectionResult.similarity() * 100);
            if (feedbackCount == 1) {
                return String.format("""
                    [循环检测] 检测到重复的输出模式（相似度 %s）。
                    你的方法似乎在原地打转，请尝试完全不同的策略。
                    建议：
                    1. 换用其他工具或方法
                    2. 重新审视问题的核心需求
                    3. 如果已尝试多种方法，可以考虑承认无法解决
                    """, similarityStr);
            } else {
                return String.format("""
                    [循环检测 - 最后机会] 重复模式仍在继续（相似度 %s）。
                    请立即：
                    1. 承认无法继续并说明遇到的困难，或
                    2. 采用根本性不同的方法
                    """, similarityStr);
            }
        }

        // Default feedback
        if (feedbackCount == 1) {
            return """
                [循环检测] 最近几步操作无进展（工具返回空结果或错误）。
                请尝试：
                1. 使用不同的工具或方法
                2. 调整参数或搜索策略
                3. 重新评估当前问题是否可解决
                """;
        }

        return """
            [循环检测 - 最后机会] 已尝试调整但仍无进展。
            请立即：
            1. 承认无法继续并说明遇到的困难，或
            2. 采用完全不同的方法（根本性改变策略）
            """;
    }

    // -------------------------------------------------------------------------
    // Snapshot and Resume
    // -------------------------------------------------------------------------

    /**
     * Create a snapshot of the current loop state.
     */
    public LoopSnapshot createSnapshot(Session session, int currentIteration,
                                       List<ToolCall> pendingToolCalls, String lastLlmResponse) {
        return new LoopSnapshot(session.id(), session.messages(), currentIteration,
            pendingToolCalls != null ? pendingToolCalls : List.of(), lastLlmResponse);
    }

    /**
     * Resume execution from a snapshot.
     */
    public CompletableFuture<LoopResult> resumeFromSnapshot(LoopSnapshot snapshot,
            List<Map<String, Object>> tools, Consumer<ProgressEvent> progressCallback) {
        return CompletableFuture.supplyAsync(() -> {
            Session session = new Session(snapshot.sessionId(), snapshot.messages(),
                java.time.Instant.now(), java.time.Instant.now(), new TokenUsage(), Map.of());

            this.onProgress = progressCallback;
            this.loopStartTime = System.currentTimeMillis();
            interrupted.set(false);
            iteration.set(snapshot.currentIteration());
            stuckFeedbackCount.set(0);
            circuitBreakerStopInjected.set(false);

            // Reset circuit breaker
            if (circuitBreaker != null) {
                circuitBreaker.reset();
            }

            emitProgress(ProgressEventType.STATE_CHANGE,
                String.format("Resuming from snapshot at iteration %d", snapshot.currentIteration()),
                Map.of("state", LoopState.BUILDING_CONTEXT.getValue(), "snapshot_created_at", snapshot.createdAt().toString()));

            // Execute pending tool calls if any
            if (!snapshot.pendingToolCalls().isEmpty()) {
                state = LoopState.EXECUTING_TOOLS;
                List<ToolResult> results = executeToolsWithTimeout(snapshot.pendingToolCalls(), session);
                for (ToolResult result : results) {
                    String content = result.success() ? result.content() : "Error: " + result.error();
                    session = session.addMessage(Message.fromToolResult(result));
                }
                iteration.incrementAndGet();
            }

            // Continue the loop
            return executeLoop(null, session, tools, progressCallback);
        });
    }

    // -------------------------------------------------------------------------
    // Helper Methods
    // -------------------------------------------------------------------------

    private void emitProgress(ProgressEventType type, String message, Map<String, Object> data) {
        if (onProgress != null && config.enableProgress()) {
            onProgress.accept(new ProgressEvent(type, message, data != null ? data : Map.of(), null));
        }
    }

    private void emitProgress(ProgressEventType type, String message, Map<String, Object> data, long durationMs) {
        if (onProgress != null && config.enableProgress()) {
            onProgress.accept(new ProgressEvent(type, message, data != null ? data : Map.of(), (double) durationMs));
        }
    }

    private HookResult executeHooks(HookPoint point, Session session, int iteration,
                                   List<Message> messages, LLMResponse response, ToolCall toolCall) {
        HookContext context = new HookContext(point, session.id(), iteration, messages, response, toolCall, null, null, null);

        for (LifecycleHook hook : hooks) {
            if (hook.hookPoints().contains(point)) {
                try {
                    HookResult result = hook.execute(context);
                    if (result.action() != HookAction.CONTINUE) {
                        return result;
                    }
                    // Update context if modified
                    if (result.injectMessage() != null) {
                        context = new HookContext(point, session.id(), iteration,
                            context.messages(), context.llmResponse(), context.toolCall(),
                            result.injectMessage(), result.modifiedArgs(), result.modifiedResult());
                    }
                } catch (Exception e) {
                    logger.warn("Hook {} failed: {}", hook.getClass().getSimpleName(), e.getMessage());
                }
            }
        }
        return HookResult.continue_();
    }

    private List<LLMClient.ToolDefinition> convertTools(List<Tool> tools) {
        return tools.stream()
            .map(t -> LLMClient.ToolDefinition.of(t.name(), t.description(), t.inputSchema()))
            .toList();
    }
}
