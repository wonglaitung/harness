package com.harness.skills;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Skill tool configuration.
 *
 * Defines which tools are allowed or restricted for a skill.
 * Supports three modes: allow, deny, ask (for user confirmation).
 *
 * Example:
 * <pre>
 * // Allow specific tools only
 * SkillTools tools = new SkillTools(
 *     List.of("read", "grep", "glob"),
 *     List.of("bash", "write"),
 *     "allow"
 * );
 *
 * // Check if tool is allowed
 * if (tools.isAllowed("read")) {
 *     // Execute tool
 * }
 * </pre>
 */
public class SkillTools {

    /**
     * Default permission modes.
     */
    public enum Permission {
        /**
         * Allow tools by default (deny list takes precedence).
         */
        ALLOW,

        /**
         * Deny tools by default (allow list takes precedence).
         */
        DENY,

        /**
         * Ask user for confirmation before using any tool.
         */
        ASK
    }

    private final Set<String> allowed;
    private final Set<String> restricted;
    private final Permission defaultPermission;

    /**
     * Create a skill tools configuration.
     *
     * @param allowed List of explicitly allowed tools
     * @param restricted List of explicitly restricted tools
     * @param defaultPermission Default permission mode
     */
    public SkillTools(List<String> allowed, List<String> restricted, Permission defaultPermission) {
        this.allowed = allowed != null ? new HashSet<>(allowed) : Set.of();
        this.restricted = restricted != null ? new HashSet<>(restricted) : Set.of();
        this.defaultPermission = defaultPermission != null ? defaultPermission : Permission.ALLOW;
    }

    /**
     * Create with string permission.
     *
     * @param allowed List of explicitly allowed tools
     * @param restricted List of explicitly restricted tools
     * @param defaultPermission Default permission ("allow", "deny", or "ask")
     */
    public SkillTools(List<String> allowed, List<String> restricted, String defaultPermission) {
        this(allowed, restricted, parsePermission(defaultPermission));
    }

    /**
     * Create default tools configuration (allow all).
     */
    public SkillTools() {
        this(List.of(), List.of(), Permission.ALLOW);
    }

    /**
     * Create a configuration that allows specific tools only.
     */
    public static SkillTools allowOnly(String... tools) {
        return new SkillTools(List.of(tools), List.of(), Permission.DENY);
    }

    /**
     * Create a configuration that denies specific tools only.
     */
    public static SkillTools denyOnly(String... tools) {
        return new SkillTools(List.of(), List.of(tools), Permission.ALLOW);
    }

    /**
     * Create a configuration that requires confirmation for all tools.
     */
    public static SkillTools askAll() {
        return new SkillTools(List.of(), List.of(), Permission.ASK);
    }

    /**
     * Check if a tool is allowed.
     *
     * @param toolName Name of the tool to check
     * @return True if the tool is allowed
     */
    public boolean isAllowed(String toolName) {
        if (toolName == null || toolName.isEmpty()) {
            return false;
        }

        // Restricted tools are always denied
        if (restricted.contains(toolName)) {
            return false;
        }

        // If allowed list is empty, use default permission
        if (allowed.isEmpty()) {
            return defaultPermission == Permission.ALLOW;
        }

        // Check if in allowed list
        return allowed.contains(toolName);
    }

    /**
     * Check if a tool requires user confirmation.
     *
     * @param toolName Name of the tool to check
     * @return True if the tool requires confirmation
     */
    public boolean requiresConfirmation(String toolName) {
        if (defaultPermission == Permission.ASK) {
            return true;
        }

        // Check if tool is in neither allowed nor restricted (unknown tools)
        if (!allowed.isEmpty() && !allowed.contains(toolName) && !restricted.contains(toolName)) {
            return defaultPermission == Permission.DENY;
        }

        return false;
    }

    /**
     * Check if a tool is explicitly restricted.
     *
     * @param toolName Name of the tool to check
     * @return True if the tool is restricted
     */
    public boolean isRestricted(String toolName) {
        return restricted.contains(toolName);
    }

    /**
     * Get all allowed tools.
     */
    public Set<String> allowedTools() {
        return new HashSet<>(allowed);
    }

    /**
     * Get all restricted tools.
     */
    public Set<String> restrictedTools() {
        return new HashSet<>(restricted);
    }

    /**
     * Get the default permission.
     */
    public Permission defaultPermission() {
        return defaultPermission;
    }

    /**
     * Builder for creating tools configuration.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private List<String> allowed = new ArrayList<>();
        private List<String> restricted = new ArrayList<>();
        private Permission defaultPermission = Permission.ALLOW;

        public Builder allowed(List<String> allowed) {
            this.allowed = new ArrayList<>(allowed);
            return this;
        }

        public Builder allow(String tool) {
            this.allowed.add(tool);
            return this;
        }

        public Builder restricted(List<String> restricted) {
            this.restricted = new ArrayList<>(restricted);
            return this;
        }

        public Builder restrict(String tool) {
            this.restricted.add(tool);
            return this;
        }

        public Builder defaultPermission(Permission permission) {
            this.defaultPermission = permission;
            return this;
        }

        public Builder defaultPermission(String permission) {
            this.defaultPermission = parsePermission(permission);
            return this;
        }

        public SkillTools build() {
            return new SkillTools(allowed, restricted, defaultPermission);
        }
    }

    private static Permission parsePermission(String permission) {
        if (permission == null) {
            return Permission.ALLOW;
        }
        return switch (permission.toLowerCase()) {
            case "allow" -> Permission.ALLOW;
            case "deny" -> Permission.DENY;
            case "ask" -> Permission.ASK;
            default -> Permission.ALLOW;
        };
    }

    @Override
    public String toString() {
        return String.format("SkillTools(allowed=%s, restricted=%s, default=%s)",
            allowed, restricted, defaultPermission);
    }
}
