package com.harness.core.hooks;

import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.core.HookContext;
import com.harness.core.HookPoint;
import com.harness.core.HookResult;
import com.harness.core.LifecycleHook;

/**
 * A hook that blocks dangerous tool calls.
 *
 * Prevents execution of tools that match a blocklist.
 * Useful for security-sensitive environments.
 *
 * Default blocked tools:
 * - System commands: rm, sudo, chmod, chown, dd, mkfs, fdisk
 *
 * For bash commands, the hook checks if any word in the command
 * matches the blocked list.
 *
 * Example:
 * <pre>
 * // Use default blocked tools
 * agent.addHook(new AbortOnDangerousToolHook());
 *
 * // Use custom blocked tools
 * agent.addHook(new AbortOnDangerousToolHook(
 *     Set.of("rm", "sudo", "my-dangerous-tool")
 * ));
 * </pre>
 */
public class AbortOnDangerousToolHook implements LifecycleHook {

    private static final Logger logger = LoggerFactory.getLogger(AbortOnDangerousToolHook.class);

    /**
     * Default blocked tools and commands.
     */
    public static final Set<String> DEFAULT_BLOCKED_TOOLS = Set.of(
        "rm", "sudo", "chmod", "chown", "dd", "mkfs", "fdisk"
    );

    private final Set<String> blockedTools;

    /**
     * Create hook with default blocked tools.
     */
    public AbortOnDangerousToolHook() {
        this(DEFAULT_BLOCKED_TOOLS);
    }

    /**
     * Create hook with custom blocked tools.
     *
     * @param blockedTools Set of tool names to block
     */
    public AbortOnDangerousToolHook(Set<String> blockedTools) {
        this.blockedTools = blockedTools != null ? blockedTools : DEFAULT_BLOCKED_TOOLS;
    }

    /**
     * Create hook with custom blocked tools as varargs.
     *
     * @param blockedTools Tool names to block
     */
    public AbortOnDangerousToolHook(String... blockedTools) {
        this.blockedTools = new HashSet<>(Arrays.asList(blockedTools));
    }

    @Override
    public List<HookPoint> hookPoints() {
        return List.of(HookPoint.BEFORE_TOOL_EXECUTE);
    }

    @Override
    public HookResult execute(HookContext context) {
        String toolName = context.toolName();

        // Check if tool is directly blocked
        if (blockedTools.contains(toolName)) {
            logger.warn("Blocked dangerous tool: {}", toolName);
            return HookResult.abort("Tool '" + toolName + "' is blocked for safety");
        }

        // Check bash commands for blocked words
        if ("bash".equals(toolName) && context.toolArgs() != null) {
            Map<String, Object> args = context.toolArgs();
            Object commandObj = args.get("command");

            if (commandObj instanceof String command) {
                String[] words = command.split("\\s+");

                for (String word : words) {
                    if (blockedTools.contains(word)) {
                        logger.warn("Blocked dangerous command: {} in {}", word, command);
                        return HookResult.abort(
                            "Command contains blocked tool '" + word + "'"
                        );
                    }
                }
            }
        }

        return HookResult.continue_();
    }

    /**
     * Add a tool to the blocked list.
     *
     * @param toolName Tool name to block
     */
    public void addBlockedTool(String toolName) {
        blockedTools.add(toolName);
    }

    /**
     * Remove a tool from the blocked list.
     *
     * @param toolName Tool name to allow
     */
    public void removeBlockedTool(String toolName) {
        blockedTools.remove(toolName);
    }

    /**
     * Get the current blocked tools.
     */
    public Set<String> getBlockedTools() {
        return Set.copyOf(blockedTools);
    }

    @Override
    public String toString() {
        return "AbortOnDangerousToolHook{blockedTools=" + blockedTools + "}";
    }
}
