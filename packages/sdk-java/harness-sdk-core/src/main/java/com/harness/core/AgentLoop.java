package com.harness.core;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Consumer;

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
 */
public class AgentLoop {

    private static final Logger logger = LoggerFactory.getLogger(AgentLoop.class);

    private final LLMClient llmClient;
    private final ToolExecutor toolExecutor;
    private final ContextBuilder contextBuilder;
    private final LoopConfig config;

    private volatile LoopState state = LoopState.IDLE;
    private final AtomicBoolean interrupted = new AtomicBoolean(false);
    private final AtomicInteger iteration = new AtomicInteger(0);

    public AgentLoop(LLMClient llmClient, ToolExecutor toolExecutor, LoopConfig config) {
        this.llmClient = llmClient;
        this.toolExecutor = toolExecutor;
        this.config = config;
        this.contextBuilder = new ContextBuilder();
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

            // Call LLM
            state = LoopState.CALLING_LLM;
            logger.debug("Calling LLM at iteration {}", iteration.get());

            List<LLMClient.ToolDefinition> tools = convertTools(toolExecutor.listTools());
            LLMResponse response;
            try {
                response = llmClient.call(context.messages(), tools, context.systemPrompt());
            } catch (Exception e) {
                logger.error("LLM call failed: {}", e.getMessage());
                state = LoopState.ERROR;
                return LoopResult.error(session, iteration.get(), e.getMessage());
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

                // Execute tools
                List<ToolResult> results = executeTools(response.toolCalls(), session);

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
     * Execute tool calls.
     */
    private List<ToolResult> executeTools(List<ToolCall> toolCalls, Session session) {
        ToolContext context = ToolContext.builder()
            .sessionId(session.id())
            .workingDirectory(config.workingDirectory())
            .iteration(iteration.get())
            .build();

        List<CompletableFuture<ToolResult>> futures = new ArrayList<>();
        for (ToolCall call : toolCalls) {
            futures.add(toolExecutor.execute(call, context));
        }

        // Wait for all tools to complete
        CompletableFuture.allOf(futures.toArray(new CompletableFuture[0])).join();

        return futures.stream()
            .map(CompletableFuture::join)
            .toList();
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