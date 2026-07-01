package com.harness.orchestrator;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Multi-agent team configuration.
 *
 * <p>Defines a team of agents that can work together on tasks
 * using different coordination modes.</p>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * TeamConfig team = TeamConfig.builder()
 *     .name("dev-team")
 *     .description("Development team")
 *     .addRole(AgentRole.builder()
 *         .name("architect")
 *         .description("System design")
 *         .build())
 *     .addRole(AgentRole.builder()
 *         .name("developer")
 *         .description("Implementation")
 *         .build())
 *     .coordinationMode(CoordinationMode.SEQUENTIAL)
 *     .build();
 * }</pre>
 */
public class TeamConfig {
    private final String name;
    private final String description;
    private final List<AgentRole> roles;
    private final CoordinationMode coordinationMode;
    private final boolean sharedMemory;
    private final String messageBus;

    private TeamConfig(Builder builder) {
        this.name = builder.name;
        this.description = builder.description;
        this.roles = new ArrayList<>(builder.roles);
        this.coordinationMode = builder.coordinationMode;
        this.sharedMemory = builder.sharedMemory;
        this.messageBus = builder.messageBus;

        validate();
    }

    private void validate() {
        if (name == null || name.isEmpty()) {
            throw new IllegalArgumentException("team name cannot be empty");
        }

        if (roles.isEmpty()) {
            throw new IllegalArgumentException("team must have at least one role");
        }

        // Validate role names are unique
        Set<String> roleNames = new HashSet<>();
        for (AgentRole role : roles) {
            if (!roleNames.add(role.getName())) {
                throw new IllegalArgumentException("role names must be unique within team: " + role.getName());
            }
        }
    }

    // Getters

    public String getName() {
        return name;
    }

    public String getDescription() {
        return description;
    }

    public List<AgentRole> getRoles() {
        return new ArrayList<>(roles);
    }

    public CoordinationMode getCoordinationMode() {
        return coordinationMode;
    }

    public boolean isSharedMemory() {
        return sharedMemory;
    }

    public String getMessageBus() {
        return messageBus;
    }

    /**
     * Get a role by name.
     */
    public AgentRole getRole(String name) {
        for (AgentRole role : roles) {
            if (role.getName().equals(name)) {
                return role;
            }
        }
        return null;
    }

    /**
     * Create a builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * Builder for TeamConfig.
     */
    public static class Builder {
        private String name;
        private String description = "";
        private List<AgentRole> roles = new ArrayList<>();
        private CoordinationMode coordinationMode = CoordinationMode.BROADCAST;
        private boolean sharedMemory = true;
        private String messageBus = "internal";

        public Builder name(String name) {
            this.name = name;
            return this;
        }

        public Builder description(String description) {
            this.description = description;
            return this;
        }

        public Builder roles(List<AgentRole> roles) {
            this.roles = new ArrayList<>(roles);
            return this;
        }

        public Builder addRole(AgentRole role) {
            this.roles.add(role);
            return this;
        }

        public Builder coordinationMode(CoordinationMode coordinationMode) {
            this.coordinationMode = coordinationMode;
            return this;
        }

        public Builder sharedMemory(boolean sharedMemory) {
            this.sharedMemory = sharedMemory;
            return this;
        }

        public Builder messageBus(String messageBus) {
            this.messageBus = messageBus;
            return this;
        }

        public TeamConfig build() {
            return new TeamConfig(this);
        }
    }

    @Override
    public String toString() {
        return "TeamConfig{name='" + name + "', roles=" + roles.size() + '}';
    }
}
