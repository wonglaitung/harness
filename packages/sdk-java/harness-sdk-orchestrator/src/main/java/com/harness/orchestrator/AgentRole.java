package com.harness.orchestrator;

import java.util.ArrayList;
import java.util.List;

/**
 * Agent role definition.
 *
 * <p>Defines a specific role within a multi-agent team,
 * including skills, tools, and behavioral configuration.</p>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * AgentRole architect = AgentRole.builder()
 *     .name("architect")
 *     .description("System design and architecture")
 *     .addSkill("code-analysis")
 *     .maxIterations(30)
 *     .build();
 * }</pre>
 */
public class AgentRole {
    private final String name;
    private final String description;
    private final List<String> skills;
    private final List<String> allowedTools;
    private final String systemPrompt;
    private final int maxIterations;

    private AgentRole(Builder builder) {
        this.name = builder.name;
        this.description = builder.description;
        this.skills = new ArrayList<>(builder.skills);
        this.allowedTools = builder.allowedTools != null ? new ArrayList<>(builder.allowedTools) : null;
        this.systemPrompt = builder.systemPrompt;
        this.maxIterations = builder.maxIterations;

        validate();
    }

    private void validate() {
        if (name == null || name.isEmpty()) {
            throw new IllegalArgumentException("role name cannot be empty");
        }

        if (description == null || description.isEmpty()) {
            throw new IllegalArgumentException("role description cannot be empty");
        }

        if (maxIterations < 1) {
            throw new IllegalArgumentException("maxIterations must be at least 1");
        }
    }

    // Getters

    public String getName() {
        return name;
    }

    public String getDescription() {
        return description;
    }

    public List<String> getSkills() {
        return new ArrayList<>(skills);
    }

    public List<String> getAllowedTools() {
        return allowedTools != null ? new ArrayList<>(allowedTools) : null;
    }

    public String getSystemPrompt() {
        return systemPrompt;
    }

    public int getMaxIterations() {
        return maxIterations;
    }

    /**
     * Create a builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * Builder for AgentRole.
     */
    public static class Builder {
        private String name;
        private String description;
        private List<String> skills = new ArrayList<>();
        private List<String> allowedTools;
        private String systemPrompt;
        private int maxIterations = 20;

        public Builder name(String name) {
            this.name = name;
            return this;
        }

        public Builder description(String description) {
            this.description = description;
            return this;
        }

        public Builder skills(List<String> skills) {
            this.skills = new ArrayList<>(skills);
            return this;
        }

        public Builder addSkill(String skill) {
            this.skills.add(skill);
            return this;
        }

        public Builder allowedTools(List<String> allowedTools) {
            this.allowedTools = new ArrayList<>(allowedTools);
            return this;
        }

        public Builder systemPrompt(String systemPrompt) {
            this.systemPrompt = systemPrompt;
            return this;
        }

        public Builder maxIterations(int maxIterations) {
            this.maxIterations = maxIterations;
            return this;
        }

        public AgentRole build() {
            return new AgentRole(this);
        }
    }

    @Override
    public String toString() {
        return "AgentRole{name='" + name + "', description='" + description + "'}";
    }
}
