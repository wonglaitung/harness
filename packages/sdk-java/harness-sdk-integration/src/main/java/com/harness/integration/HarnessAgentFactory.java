package com.harness.integration;

import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.core.HarnessConfig;
import com.harness.core.LLMClient;
import com.harness.core.SubAgentManager;
import com.harness.core.SubAgentConfig;
import com.harness.core.SubAgentResult;
import com.harness.core.SubAgentStatus;
import com.harness.core.Tool;
import com.harness.types.LoopResult;
import com.harness.types.LoopState;
import com.harness.types.TokenUsage;

/**
 * AgentFactory implementation that creates real AgentHarness sub-agents.
 *
 * This factory creates AgentHarness instances for each sub-agent,
 * properly inheriting tools and LLM client from the parent agent.
 */
public class HarnessAgentFactory implements SubAgentManager.AgentFactory {

    private static final Logger logger = LoggerFactory.getLogger(HarnessAgentFactory.class);

    @Override
    public SubAgentManager.AgentRunner createRunner(
        SubAgentConfig config,
        List<Tool> tools,
        SubAgentManager.AgentHarnessParent parent
    ) {
        return new HarnessAgentRunner(config, tools, parent);
    }

    /**
     * AgentRunner that wraps an AgentHarness.
     */
    private static class HarnessAgentRunner implements SubAgentManager.AgentRunner {
        private final SubAgentConfig config;
        private final AgentHarness subAgent;

        HarnessAgentRunner(SubAgentConfig config, List<Tool> tools, SubAgentManager.AgentHarnessParent parent) {
            this.config = config;

            // Build sub-agent harness config
            HarnessConfig subConfig = HarnessConfig.builder()
                .model(parent != null ? parent.getModel() : "claude-sonnet-4-6")
                .maxIterations(config.maxIterations())
                .systemPrompt(config.systemPrompt() != null
                    ? config.systemPrompt()
                    : buildDefaultPrompt(config))
                .build();

            // Create sub-agent with inherited LLM client
            LLMClient llmClient = parent != null ? (LLMClient) parent.getLLMClient() : null;

            if (llmClient != null) {
                this.subAgent = new AgentHarness(llmClient, subConfig, tools);
            } else {
                this.subAgent = new AgentHarness(subConfig);
                // Register inherited tools
                for (Tool tool : tools) {
                    this.subAgent.registerTool(tool);
                }
            }

            logger.debug("Created HarnessAgentRunner for: {}", config.name());
        }

        @Override
        public SubAgentResult run() {
            try {
                // Run the sub-agent synchronously
                LoopResult loopResult = subAgent.run(config.task()).join();

                // Convert to SubAgentResult
                return buildResultFromLoop(config, loopResult);
            } catch (Exception e) {
                logger.error("Sub-agent {} execution failed: {}", config.name(), e.getMessage());
                return SubAgentResult.failure(config.name(), e.getMessage());
            }
        }

        private SubAgentResult buildResultFromLoop(SubAgentConfig config, LoopResult loopResult) {
            boolean success = loopResult.status() == LoopState.COMPLETED;
            SubAgentStatus status = success
                ? SubAgentStatus.COMPLETED
                : SubAgentStatus.FAILED;

            TokenUsage usage = loopResult.tokenUsage() != null
                ? loopResult.tokenUsage()
                : new TokenUsage(0, 0);

            String reportFormat = config.reportFormat() != null ? config.reportFormat() : "summary";

            switch (reportFormat) {
                case "summary":
                    String response = loopResult.finalResponse() != null ? loopResult.finalResponse() : "";
                    String summary = response.length() > 500
                        ? response.substring(0, 500) + "..."
                        : response;
                    return new SubAgentResult(
                        config.name(), success, status, summary, null, null,
                        loopResult.iterations(), usage, null
                    );

                case "full":
                    return new SubAgentResult(
                        config.name(), success, status, null,
                        loopResult.finalResponse(), null,
                        loopResult.iterations(), usage, null
                    );

                case "structured":
                    java.util.Map<String, Object> structured = new java.util.HashMap<>();
                    structured.put("response", loopResult.finalResponse());
                    structured.put("iterations", loopResult.iterations());
                    structured.put("messages", loopResult.session() != null
                        ? loopResult.session().messages()
                        : java.util.List.of());
                    return new SubAgentResult(
                        config.name(), success, status, null, null, structured,
                        loopResult.iterations(), usage, null
                    );

                default:
                    return SubAgentResult.success(
                        config.name(), loopResult.finalResponse(),
                        loopResult.iterations(), usage
                    );
            }
        }

        private String buildDefaultPrompt(SubAgentConfig config) {
            return String.format(
                "You are a specialized sub-agent tasked with: %s\n\n" +
                "You are part of a larger task and should focus only on your assigned work.\n" +
                "Complete your task thoroughly and report your findings clearly.\n\n" +
                "When finished, provide a concise summary of what you accomplished.",
                config.task()
            );
        }
    }
}