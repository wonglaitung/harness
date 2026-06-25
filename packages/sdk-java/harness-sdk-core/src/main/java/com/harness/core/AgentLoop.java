package com.harness.core;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Consumer;
import java.util.random.RandomGenerator;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

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
 * - Configurable retry count
 * - Intelligent error handling with ErrorHandler
 */
public class AgentLoop {

    private static final Logger logger = LoggerFactory.getLogger(AgentLoop.class);
    private static final RandomGenerator random = RandomGenerator.getDefault();

    private final LLMClient llmClient;
    private final ToolExecutor toolExecutor;
    private final ContextBuilder contextBuilder;
    private final LoopConfig config;
    private final ErrorHandler errorHandler;

    private volatile LoopState state = LoopState.IDLE;
    private final AtomicBoolean interrupted = new AtomicBoolean(false);
    private final AtomicInteger iteration = new AtomicInteger(0);

    public AgentLoop(LLMClient llmClient, ToolExecutor toolExecutor, LoopConfig config) {
        this.llmClient = llmClient;
        this.toolExecutor = toolExecutor;
        this.config = config;
        this.contextBuilder = new ContextBuilder();
        this.errorHandler = new ErrorHandler();
    }

    public AgentLoop(LLMClient llmClient, ToolExecutor toolExecutor) {
        this(llmClient, toolExecutor, LoopConfig.defaults());
    }

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
        return CompletableFuture.supplyAsync(() -> executeLoop(prompt, session));
    }

    /**
     * Main loop execution.
     */
    private LoopResult executeLoop(String prompt, Session session) {
        logger.info("Starting agent loop, maxIterations={}", config.maxIterations());

        // Reset state
        interrupted.set(false);
        iteration.set(0);
        state = LoopState.IDLE;
        errorHandler.reset();  // Reset error handler for new loop

        TokenUsage totalUsage = new TokenUsage();

        // Add user message to session
        if (prompt != null && !prompt.isEmpty()) {
            session = session.addMessage(Message.user(prompt));
        }

        while (iteration.get() < config.maxIterations()) {
            // Check for interruption
            if (interrupted.get()) {
                state = LoopState.INTERRUPTED;
                logger.info("Loop interrupted at iteration {}", iteration.get());
                return LoopResult.interrupted(session, iteration.get());
            }

            // Build context
            state = LoopState.BUILDING_CONTEXT;
            ContextBuilder.Context context = contextBuilder.build(session);

            // Call LLM with retry
            state = LoopState.CALLING_LLM;
            logger.debug("Calling LLM at iteration {}", iteration.get());

            List<LLMClient.ToolDefinition> tools = convertTools(toolExecutor.listTools());
            LLMResponse response = callLLMWithRetry(context, tools);

            if (response == null) {
                // All retries failed
                state = LoopState.ERROR;
                return LoopResult.error(session, iteration.get(), "LLM call failed after all retries");
            }

            logger.debug("LLM response: stopReason={}, hasToolCalls={}",
                response.stopReason(), response.isToolUse());

            // Update token usage
            totalUsage = totalUsage.add(response.usage());

            // Add assistant message (skip if empty and has tool calls)
            if (response.content() != null && !response.content().isEmpty() || !response.isToolUse()) {
                session = session.addMessage(Message.assistant(response.content()));
            }

            // Check if we need tools
            if (response.isToolUse()) {
                state = LoopState.EXECUTING_TOOLS;

                // Execute tools with timeout
                List<ToolResult> results = executeToolsWithTimeout(response.toolCalls(), session);

                // Add tool results to session
                for (ToolResult result : results) {
                    session = session.addMessage(Message.fromToolResult(result));
                }

                iteration.incrementAndGet();
                continue;
            }

            // Done!
            state = LoopState.COMPLETED;
            session = session.withTokenUsage(totalUsage);

            logger.info("Loop completed at iteration {}, tokens={}",
                iteration.get(), totalUsage.totalTokens());

            return LoopResult.completed(session, response.content(), iteration.get(), totalUsage);
        }

        // Max iterations reached
        state = LoopState.ERROR;
        logger.warn("Max iterations reached: {}", iteration.get());

        // Try to get final response from last assistant message
        String finalResponse = null;
        for (Message msg : session.messages()) {
            if ("assistant".equals(msg.role()) && msg.contentAsString() != null) {
                finalResponse = msg.contentAsString();
            }
        }

        return LoopResult.maxIterations(session, iteration.get());
    }

    /**
     * Call LLM with retry and intelligent error handling.
     *
     * Retry strategy:
     * - Max retries from config.retryOnError()
     * - Uses ErrorHandler for intelligent delay (e.g., Retry-After header)
     * - Fallback: exponential backoff with jitter
     *
     * @return LLMResponse or null if all retries failed
     */
    private LLMResponse callLLMWithRetry(ContextBuilder.Context context, List<LLMClient.ToolDefinition> tools) {
        int maxRetries = config.retryOnError();

        for (int attempt = 0; attempt < maxRetries; attempt++) {
            try {
                return llmClient.call(context.messages(), tools, context.systemPrompt());
            } catch (Exception e) {
                logger.warn("LLM call failed (attempt {}/{}): {}",
                    attempt + 1, maxRetries, e.getMessage());

                if (attempt < maxRetries - 1) {
                    // Build error context
                    ErrorContext errorContext = ErrorContext.builder()
                        .error(e)
                        .iteration(iteration.get())
                        .attempt(attempt + 1)
                        .build();

                    // Get intelligent decision from ErrorHandler
                    ErrorDecision decision = errorHandler.handle(e, errorContext);

                    if (decision.action() == ErrorAction.RETRY) {
                        // Use ErrorHandler's delay or fallback to exponential backoff with jitter
                        double delaySeconds;
                        if (decision.delaySeconds() > 0) {
                            delaySeconds = decision.delaySeconds();
                        } else {
                            // Exponential backoff with jitter (cap at 30s)
                            long baseBackoffMs = Math.min((long) Math.pow(2, attempt) * 1000, 30_000);
                            long jitterMs = random.nextLong(500);
                            delaySeconds = (baseBackoffMs + jitterMs) / 1000.0;
                        }

                        logger.info("Retrying in {}s: {}", String.format("%.1f", delaySeconds), decision.message());

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
                    // Other actions (SKIP, COMPRESS_CONTEXT, ESCALATE) not handled in LLM call
                }
            }
        }

        logger.error("LLM call failed after {} attempts", maxRetries);
        return null;
    }

    /**
     * Execute tool calls with timeout protection.
     *
     * Each tool execution is limited by config.timeoutPerTool().
     * If timeout is exceeded, returns a failed ToolResult.
     */
    private List<ToolResult> executeToolsWithTimeout(List<ToolCall> toolCalls, Session session) {
        ToolContext context = ToolContext.builder()
            .sessionId(session.id())
            .workingDirectory(config.workingDirectory())
            .iteration(iteration.get())
            .build();

        List<CompletableFuture<ToolResult>> futures = new ArrayList<>();
        for (ToolCall call : toolCalls) {
            futures.add(executeToolWithTimeout(call, context));
        }

        // Wait for all tools to complete
        CompletableFuture.allOf(futures.toArray(new CompletableFuture[0])).join();

        return futures.stream()
            .map(CompletableFuture::join)
            .toList();
    }

    /**
     * Execute a single tool with timeout.
     */
    private CompletableFuture<ToolResult> executeToolWithTimeout(ToolCall call, ToolContext context) {
        CompletableFuture<ToolResult> future = toolExecutor.execute(call, context);

        return future.orTimeout(config.timeoutPerTool(), TimeUnit.MILLISECONDS)
            .exceptionally(ex -> {
                if (ex.getCause() instanceof TimeoutException) {
                    logger.warn("Tool {} timed out after {}ms", call.name(), config.timeoutPerTool());
                    return ToolResult.error(
                        call.id(),
                        call.name(),
                        "Tool execution timed out after " + config.timeoutPerTool() + "ms"
                    );
                }
                logger.error("Tool {} failed: {}", call.name(), ex.getMessage());
                return ToolResult.error(call.id(), call.name(), ex.getMessage());
            });
    }

    /**
     * Convert internal tools to LLM tool definitions.
     */
    private List<LLMClient.ToolDefinition> convertTools(List<Tool> tools) {
        return tools.stream()
            .map(t -> LLMClient.ToolDefinition.of(t.name(), t.description(), t.inputSchema()))
            .toList();
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
}