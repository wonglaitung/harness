package com.harness.integration;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Consumer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.core.CircuitBreaker;
import com.harness.core.CircuitBreakerConfig;
import com.harness.core.HookAction;
import com.harness.core.HookContext;
import com.harness.core.HookPoint;
import com.harness.core.HookResult;
import com.harness.core.LLMClient;
import com.harness.core.LoopConfig;
import com.harness.core.OffloadedOutput;
import com.harness.core.OutputOffloader;
import com.harness.core.StuckDetector;
import com.harness.core.StuckDetectorConfig;
import com.harness.core.StuckDetectionResult;
import com.harness.core.StepBudgetController;
import com.harness.core.StepBudgetConfig;
import com.harness.core.Tool;
import com.harness.core.ToolContext;
import com.harness.core.ValidationResult;
import com.harness.types.LLMResponse;
import com.harness.types.Message;
import com.harness.types.ProgressEvent;
import com.harness.types.ProgressEventType;
import com.harness.types.TokenUsage;
import com.harness.types.ToolCall;
import com.harness.types.ToolResult;

/**
 * Agent loop - the core ReAct-style execution engine.
 *
 * Implements the ReAct pattern:
 * 1. Build context from session
 * 2. Call LLM
 * 3. Execute tools if needed
 * 4. Repeat until done or budget exhausted
 *
 * Features:
 * - Circuit breaker for infinite loop detection
 * - Stuck detection for semantic repetition
 * - Step budget for iteration control
 * - Output offloading for large tool results
 * - Lifecycle hooks for extensibility
 * - Progress events for observability
 *
 * Example:
 * <pre>
 * AgentLoop loop = new AgentLoop(llmClient, tools, config);
 * loop.addHook(new MyHook());
 *
 * CompletableFuture<LoopResult> result = loop.run(session, progress -> {
 *     System.out.println(progress);
 * });
 * </pre>
 */
public class AgentLoop {

    private static final Logger logger = LoggerFactory.getLogger(AgentLoop.class);

    private final LLMClient llmClient;
    private final List<Tool> tools;
    private final LoopConfig config;
    private final HookRegistry hookRegistry;

    // Core components
    private final CircuitBreaker circuitBreaker;
    private final StuckDetector stuckDetector;
    private final StepBudgetController stepBudget;
    private final OutputOffloader outputOffloader;

    /**
     * Create AgentLoop with LLM client and tools.
     */
    public AgentLoop(LLMClient llmClient, List<Tool> tools) {
        this(llmClient, tools, LoopConfig.defaults(), new HookRegistry());
    }

    /**
     * Create AgentLoop with configuration.
     */
    public AgentLoop(LLMClient llmClient, List<Tool> tools, LoopConfig config) {
        this(llmClient, tools, config, new HookRegistry());
    }

    /**
     * Create AgentLoop with all components.
     */
    public AgentLoop(LLMClient llmClient, List<Tool> tools, LoopConfig config, HookRegistry hookRegistry) {
        this.llmClient = llmClient;
        this.tools = tools != null ? tools : new ArrayList<>();
        this.config = config;
        this.hookRegistry = hookRegistry != null ? hookRegistry : new HookRegistry();

        // Initialize core components
        this.circuitBreaker = config.enableCircuitBreaker()
            ? new CircuitBreaker(CircuitBreakerConfig.defaults())
            : null;

        this.stuckDetector = new StuckDetector(StuckDetectorConfig.defaults());

        this.stepBudget = new StepBudgetController(StepBudgetConfig.builder()
            .maxIterationsPerTask(config.maxIterations())
            .build());

        this.outputOffloader = new OutputOffloader();

        logger.info("AgentLoop initialized with maxIterations={}, tools={}",
            config.maxIterations(), this.tools.size());
    }

    /**
     * Add a lifecycle hook.
     */
    public void addHook(com.harness.core.LifecycleHook hook) {
        hookRegistry.register(hook);
    }

    /**
     * Remove a lifecycle hook.
     */
    public void removeHook(com.harness.core.LifecycleHook hook) {
        hookRegistry.unregister(hook);
    }

    /**
     * Run the agent loop with a session.
     *
     * @param session Current session with messages
     * @param onProgress Progress callback (optional)
     * @return LoopResult
     */
    public CompletableFuture<com.harness.types.LoopResult> run(
        com.harness.types.Session session,
        Consumer<Object> onProgress
    ) {
        logger.info("Running agent loop for session: {}", session.id());

        return CompletableFuture.supplyAsync(() -> {
            try {
                return runSync(session, onProgress);
            } catch (Exception e) {
                logger.error("Agent loop error: {}", e.getMessage(), e);
                return com.harness.types.LoopResult.error(session, 0, e.getMessage());
            }
        });
    }

    /**
     * Synchronous execution.
     */
    private com.harness.types.LoopResult runSync(
        com.harness.types.Session session,
        Consumer<Object> onProgress
    ) {
        // Reset state
        stepBudget.startTask();
        if (circuitBreaker != null) {
            circuitBreaker.reset();
        }
        stuckDetector.clearSession(session.id());

        com.harness.types.Session currentSession = session;
        AtomicInteger iteration = new AtomicInteger(0);
        TokenUsage totalUsage = new TokenUsage();

        // 1. ON_LOOP_START hook
        executeHooks(HookPoint.ON_LOOP_START, currentSession, iteration.get(), null, null);

        // Emit progress event
        emitProgress(onProgress, ProgressEventType.loopStart(session.id()));

        // Main loop
        while (shouldContinue(iteration.get())) {

            // 2. Check circuit breaker
            if (circuitBreaker != null && circuitBreaker.isOpen()) {
                logger.warn("Circuit breaker is open: {}", circuitBreaker.getReason());
                return com.harness.types.LoopResult.stuck(
                    currentSession, iteration.get(), circuitBreaker.getReason()
                );
            }

            // 3. BEFORE_LLM_CALL hook
            HookContext beforeLlmContext = buildHookContext(currentSession, iteration.get(), null, null);
            if (hookShouldAbort(HookPoint.BEFORE_LLM_CALL, beforeLlmContext)) {
                return com.harness.types.LoopResult.interrupted(currentSession, iteration.get());
            }

            emitProgress(onProgress, ProgressEventType.llmCallStart(iteration.get()));

            // 4. Call LLM with retry
            LLMResponse response;
            try {
                response = callLLMWithRetry(currentSession);
            } catch (Exception e) {
                // ON_ERROR hook
                HookContext errorContext = HookContext.builder()
                    .hookPoint(HookPoint.ON_ERROR)
                    .sessionId(session.id())
                    .iteration(iteration.get())
                    .messages(currentSession.messages())
                    .error(e)
                    .build();
                executeHooksWithContext(HookPoint.ON_ERROR, errorContext);

                // Record error for circuit breaker
                if (circuitBreaker != null) {
                    circuitBreaker.recordError(e);
                }

                logger.error("LLM call failed: {}", e.getMessage());
                return com.harness.types.LoopResult.error(currentSession, iteration.get(), e.getMessage());
            }

            // Update token usage
            if (response.usage() != null) {
                totalUsage = new TokenUsage(
                    totalUsage.inputTokens() + response.usage().inputTokens(),
                    totalUsage.outputTokens() + response.usage().outputTokens()
                );
                currentSession = currentSession.withTokenUsage(totalUsage);
            }

            // 5. AFTER_LLM_CALL hook
            HookContext afterLlmContext = buildHookContext(currentSession, iteration.get(), response, null);
            executeHooksWithContext(HookPoint.AFTER_LLM_CALL, afterLlmContext);

            emitProgress(onProgress, ProgressEventType.llmCallEnd(iteration.get(), response));

            // 6. Stuck detection
            StuckDetectionResult stuck = stuckDetector.check(
                session.id(), currentSession.messages(), iteration.get()
            );
            if (stuck.isStuck()) {
                logger.warn("Stuck detected: {}", stuck.reason());
                return com.harness.types.LoopResult.stuck(
                    currentSession, iteration.get(), "Stuck: " + stuck.reason()
                );
            }

            // 7. Handle response
            if (response.isToolUse()) {
                // Execute tools
                for (ToolCall call : response.toolCalls()) {

                    // BEFORE_TOOL_EXECUTE hook
                    HookContext toolContext = buildHookContext(currentSession, iteration.get(), response, call);
                    if (hookShouldAbort(HookPoint.BEFORE_TOOL_EXECUTE, toolContext)) {
                        return com.harness.types.LoopResult.interrupted(currentSession, iteration.get());
                    }

                    emitProgress(onProgress, ProgressEventType.toolExecuteStart(call.name()));

                    // Record for circuit breaker
                    if (circuitBreaker != null) {
                        circuitBreaker.recordCall(call.name(), call.arguments());
                    }

                    // Check step budget
                    var budgetCheck = stepBudget.checkBeforeToolCall(call.name());
                    if (budgetCheck.shouldStop()) {
                        logger.warn("Step budget exceeded: {}", budgetCheck.message());
                        return com.harness.types.LoopResult.maxIterations(currentSession, iteration.get());
                    }

                    // Execute tool
                    ToolResult result;
                    try {
                        result = executeTool(call, currentSession);
                        if (circuitBreaker != null) {
                            circuitBreaker.recordSuccess();
                        }
                    } catch (Exception e) {
                        result = ToolResult.failure(call.id(), e.getMessage(), call.name());
                        if (circuitBreaker != null) {
                            circuitBreaker.recordError(e);
                        }
                    }

                    // Offload large output
                    if (result.content() != null && result.content().length() > 50000) {
                        OffloadedOutput offloaded = outputOffloader.offload(
                            result.content(), call.name(), call.id(), session.id()
                        );
                        result = ToolResult.success(
                            call.id(),
                            "[Output offloaded to: " + offloaded.filePath() + "]",
                            call.name()
                        );
                        logger.info("Tool output offloaded: {} chars -> {}",
                            result.content().length(), offloaded.filePath());
                    }

                    // Record tool call in budget
                    stepBudget.recordToolCall(call.name());

                    // AFTER_TOOL_EXECUTE hook
                    HookContext afterToolContext = HookContext.builder()
                        .hookPoint(HookPoint.AFTER_TOOL_EXECUTE)
                        .sessionId(session.id())
                        .iteration(iteration.get())
                        .messages(currentSession.messages())
                        .llmResponse(response)
                        .toolName(call.name())
                        .toolArgs(call.arguments())
                        .toolResult(result)
                        .build();
                    executeHooksWithContext(HookPoint.AFTER_TOOL_EXECUTE, afterToolContext);

                    emitProgress(onProgress, ProgressEventType.toolExecuteEnd(call.name(), result));

                    // Add result to session
                    currentSession = currentSession.addMessage(Message.fromToolResult(result));
                }

                // Add assistant message
                currentSession = currentSession.addMessage(Message.assistant(response.content()));

            } else {
                // No tool calls - complete
                logger.info("Loop completed at iteration {}", iteration.get());
                return com.harness.types.LoopResult.completed(
                    currentSession, response.content(), iteration.get(), totalUsage
                );
            }

            // Advance iteration
            iteration.incrementAndGet();
            stepBudget.advanceIteration();
        }

        // 8. ON_LOOP_END hook
        executeHooks(HookPoint.ON_LOOP_END, currentSession, iteration.get(), null, null);

        emitProgress(onProgress, ProgressEventType.loopEnd(session.id(), iteration.get()));

        // Max iterations reached
        logger.warn("Max iterations reached: {}", config.maxIterations());
        return com.harness.types.LoopResult.maxIterations(currentSession, iteration.get());
    }

    /**
     * Check if loop should continue.
     */
    private boolean shouldContinue(int iteration) {
        return iteration < config.maxIterations();
    }

    /**
     * Check if hook at a point wants to abort.
     */
    private boolean hookShouldAbort(HookPoint point, HookContext context) {
        List<HookResult> results = hookRegistry.execute(point, context);
        for (HookResult result : results) {
            if (result != null && result.action() == HookAction.ABORT) {
                Object reason = result.metadata().get("reason");
                logger.info("Hook requested abort: {}", reason);
                return true;
            }
        }
        return false;
    }

    /**
     * Call LLM with retry logic.
     */
    private LLMResponse callLLMWithRetry(com.harness.types.Session session) {
        List<Message> messages = session.messages();
        String systemPrompt = session.systemPrompt();

        // Build tool definitions
        List<LLMClient.ToolDefinition> toolDefs = new ArrayList<>();
        for (Tool tool : tools) {
            toolDefs.add(LLMClient.ToolDefinition.of(
                tool.name(),
                tool.description(),
                tool.inputSchema()
            ));
        }

        int retries = 0;
        Exception lastError = null;

        while (retries <= config.retryOnError()) {
            try {
                return llmClient.call(messages, toolDefs, systemPrompt);
            } catch (Exception e) {
                lastError = e;
                retries++;

                if (retries <= config.retryOnError()) {
                    // Exponential backoff
                    long delay = (long) (1000 * Math.pow(2, retries - 1));
                    logger.warn("LLM call failed, retry {} in {}ms: {}", retries, delay, e.getMessage());

                    try {
                        Thread.sleep(delay);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        throw new RuntimeException("Interrupted during retry", ie);
                    }
                }
            }
        }

        throw new RuntimeException("LLM call failed after " + retries + " retries", lastError);
    }

    /**
     * Execute a tool.
     */
    private ToolResult executeTool(ToolCall call, com.harness.types.Session session) {
        // Find tool
        Tool tool = findTool(call.name());
        if (tool == null) {
            return ToolResult.failure(call.id(), "Tool not found: " + call.name(), call.name());
        }

        // Validate arguments
        ValidationResult validation = tool.validate(call.arguments());
        if (!validation.isValid()) {
            return ToolResult.failure(call.id(), "Validation failed: " + validation.error(), call.name());
        }

        // Build tool context with memory path
        java.nio.file.Path memoryPath = config.memoryMdPath() != null
            ? java.nio.file.Path.of(config.memoryMdPath())
            : java.nio.file.Path.of(System.getProperty("user.home"), ".harness");

        java.util.Map<String, Object> metadata = new java.util.HashMap<>();
        metadata.put("memory_md_path", memoryPath.toString());

        ToolContext ctx = ToolContext.builder()
            .sessionId(session.id())
            .workingDirectory(config.workingDirectory())
            .iteration(stepBudget.getUsage().iterations())
            .metadata(metadata)
            .build();

        // Execute
        try {
            return tool.execute(call.arguments(), ctx).join();
        } catch (Exception e) {
            return ToolResult.failure(call.id(), e.getMessage(), call.name());
        }
    }

    /**
     * Find tool by name.
     */
    private Tool findTool(String name) {
        for (Tool tool : tools) {
            if (tool.name().equals(name)) {
                return tool;
            }
        }
        return null;
    }

    /**
     * Execute hooks at a point with a context.
     */
    private void executeHooksWithContext(HookPoint point, HookContext context) {
        hookRegistry.execute(point, context);
    }

    /**
     * Execute hooks at a point.
     */
    private void executeHooks(
        HookPoint point,
        com.harness.types.Session session,
        int iteration,
        LLMResponse response,
        Exception error
    ) {
        HookContext context = HookContext.builder()
            .hookPoint(point)
            .sessionId(session.id())
            .iteration(iteration)
            .messages(session.messages())
            .llmResponse(response)
            .error(error)
            .build();

        hookRegistry.execute(point, context);
    }

    /**
     * Build hook context.
     */
    private HookContext buildHookContext(
        com.harness.types.Session session,
        int iteration,
        LLMResponse response,
        ToolCall toolCall
    ) {
        return new HookContext(
            HookPoint.BEFORE_LLM_CALL, // Will be overridden by caller
            session.id(),
            iteration,
            session.messages(),
            response,
            toolCall
        );
    }

    /**
     * Emit progress event if callback is set.
     */
    private void emitProgress(Consumer<Object> onProgress, ProgressEvent event) {
        if (onProgress != null && config.enableProgress()) {
            try {
                onProgress.accept(event);
            } catch (Exception e) {
                logger.warn("Progress callback error: {}", e.getMessage());
            }
        }
    }

    /**
     * Get circuit breaker stats.
     */
    public Map<String, Object> getCircuitBreakerStats() {
        return circuitBreaker != null ? circuitBreaker.getStats() : Map.of();
    }

    /**
     * Get step budget stats.
     */
    public Map<String, Object> getBudgetStats() {
        return stepBudget.getUsageReport();
    }

    /**
     * Reset all state.
     */
    public void reset() {
        if (circuitBreaker != null) {
            circuitBreaker.reset();
        }
        stuckDetector.reset();
        stepBudget.startTask(); // Resets counters
        hookRegistry.reset();
    }
}