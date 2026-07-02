package com.harness.integration;

import java.util.ArrayList;
import java.util.List;

import com.harness.core.LLMClient;
import com.harness.core.SubAgentManager;
import com.harness.core.Tool;

/**
 * Adapter to make AgentHarness implement AgentHarnessParent interface.
 *
 * This allows AgentHarness to be used as a parent for SubAgentManager,
 * enabling sub-agent creation with proper tool and LLM inheritance.
 */
public class AgentHarnessParentAdapter implements SubAgentManager.AgentHarnessParent {

    private final AgentHarness harness;

    public AgentHarnessParentAdapter(AgentHarness harness) {
        this.harness = harness;
    }

    @Override
    public String getModel() {
        return harness.getConfig().getModel();
    }

    @Override
    public Object getLLMClient() {
        return harness.getLLMClient();
    }

    @Override
    public List<Tool> getAllTools() {
        return new ArrayList<>(harness.getToolRegistry().getTools());
    }

    /**
     * Get the underlying AgentHarness.
     */
    public AgentHarness getHarness() {
        return harness;
    }
}