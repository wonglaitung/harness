package com.harness.core;

import java.util.*;

/**
 * Registry for managing available tools.
 *
 * Tools are registered with a unique name and can be retrieved,
 * enabled/disabled, or listed by category.
 *
 * Example:
 * <pre>
 * ToolRegistry registry = new ToolRegistry();
 * registry.register(new ReadTool(), "filesystem");
 * registry.register(new WriteTool(), "filesystem");
 *
 * Tool tool = registry.get("read");
 * List&lt;Tool&gt; allTools = registry.getAll(true);
 * </pre>
 */
public class ToolRegistry {

    private final Map<String, ToolInfo> tools = new HashMap<>();

    /**
     * Information about a registered tool.
     */
    public static class ToolInfo {
        private final Tool tool;
        private final String category;
        private boolean enabled;

        public ToolInfo(Tool tool, String category, boolean enabled) {
            this.tool = tool;
            this.category = category;
            this.enabled = enabled;
        }

        public Tool getTool() { return tool; }
        public String getCategory() { return category; }
        public boolean isEnabled() { return enabled; }
        public void setEnabled(boolean enabled) { this.enabled = enabled; }
    }

    /**
     * Register a tool.
     *
     * @param tool Tool instance to register
     * @param category Category for organization
     */
    public void register(Tool tool, String category) {
        if (tools.containsKey(tool.name())) {
            throw new IllegalArgumentException("Tool already registered: " + tool.name());
        }

        tools.put(tool.name(), new ToolInfo(tool, category, true));
    }

    /**
     * Register a tool with default category.
     */
    public void register(Tool tool) {
        register(tool, "custom");
    }

    /**
     * Unregister a tool.
     *
     * @param name Tool name to unregister
     * @return The unregistered tool, or null if not found
     */
    public Tool unregister(String name) {
        ToolInfo info = tools.remove(name);
        return info != null ? info.tool : null;
    }

    /**
     * Get a tool by name.
     *
     * @param name Tool name
     * @return Tool instance or null
     */
    public Tool get(String name) {
        ToolInfo info = tools.get(name);
        return (info != null && info.enabled) ? info.tool : null;
    }

    /**
     * Get all registered tools.
     *
     * @param enabledOnly Only return enabled tools
     * @return List of tool instances
     */
    public List<Tool> getAll(boolean enabledOnly) {
        List<Tool> result = new ArrayList<>();
        for (ToolInfo info : tools.values()) {
            if (!enabledOnly || info.enabled) {
                result.add(info.tool);
            }
        }
        return result;
    }

    /**
     * Get all registered tools.
     */
    public List<Tool> getAll() {
        return getAll(true);
    }

    /**
     * Get tool definitions for LLM API.
     *
     * @return List of tool definitions
     */
    public List<Map<String, Object>> getDefinitions() {
        List<Map<String, Object>> definitions = new ArrayList<>();
        for (Tool tool : getAll(true)) {
            definitions.add(tool.toDefinition());
        }
        return definitions;
    }

    /**
     * Enable a tool.
     */
    public boolean enable(String name) {
        ToolInfo info = tools.get(name);
        if (info != null) {
            info.setEnabled(true);
            return true;
        }
        return false;
    }

    /**
     * Disable a tool.
     */
    public boolean disable(String name) {
        ToolInfo info = tools.get(name);
        if (info != null) {
            info.setEnabled(false);
            return true;
        }
        return false;
    }

    /**
     * List all tools with their status.
     */
    public Map<String, Map<String, Object>> listTools() {
        Map<String, Map<String, Object>> result = new HashMap<>();
        for (Map.Entry<String, ToolInfo> entry : tools.entrySet()) {
            Map<String, Object> info = new HashMap<>();
            info.put("description", entry.getValue().tool.description());
            info.put("category", entry.getValue().category);
            info.put("enabled", entry.getValue().enabled);
            result.put(entry.getKey(), info);
        }
        return result;
    }

    /**
     * Check if a tool is registered.
     */
    public boolean contains(String name) {
        return tools.containsKey(name);
    }

    /**
     * Get number of registered tools.
     */
    public int size() {
        return tools.size();
    }
}
