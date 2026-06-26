package com.harness.core.hooks;

import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.function.BiFunction;
import java.util.function.Consumer;
import java.util.function.Predicate;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.core.HookContext;
import com.harness.core.HookPoint;
import com.harness.core.HookResult;
import com.harness.core.LifecycleHook;

/**
 * Hook that asks for user confirmation before dangerous operations.
 *
 * This hook intercepts tool calls that may have destructive effects
 * (file modifications, command execution) and asks the user to confirm.
 *
 * Design principles (based on industry best practices):
 * 1. File modifications (write/edit) always require confirmation
 * 2. Bash commands only require confirmation for dangerous patterns
 * 3. Read-only operations (read/glob/grep) never require confirmation
 * 4. User can choose to trust a command for the entire session
 *
 * Session Trust:
 * - When user selects "Allow for session", the trust key is cached
 * - Trust keys are command-level: "bash:ls", "bash:rm", "write", "edit"
 * - New sessions start with empty trust cache
 *
 * Example:
 * <pre>
 * ConfirmationHook hook = ConfirmationHook.builder()
 *     .onConfirm((toolName, args) -> {
 *         // Show dialog and return ConfirmationResult
 *         return showConfirmationDialog(toolName, args);
 *     })
 *     .isTrusted(key -> sessionTrustedCommands.contains(key))
 *     .onTrust(key -> sessionTrustedCommands.add(key))
 *     .build();
 *
 * agent.addHook(hook);
 * </pre>
 */
public class ConfirmationHook implements LifecycleHook {

    private static final Logger logger = LoggerFactory.getLogger(ConfirmationHook.class);

    /**
     * Tools that always require confirmation (modify files).
     */
    public static final Set<String> DANGEROUS_TOOLS = Set.of(
        "write",
        "edit"
    );

    /**
     * Dangerous command patterns within bash.
     * Based on: Claude Code security research, OWASP guidelines, and cross-platform considerations.
     */
    public static final Set<String> DANGEROUS_COMMANDS = Set.of(
        // System-destructive commands
        "rm", "rmdir", "del", "erase", "format", "diskpart", "dd", "mkfs", "fdisk", "shred", "wipefs",

        // Privilege escalation
        "sudo", "su", "runas", "doas", "pkexec",

        // Permission changes
        "chmod", "chown", "chgrp", "icacls", "attrib",

        // Git destructive operations
        "git push --force", "git push -f", "git reset --hard", "git clean -fd",

        // Package publishing
        "npm publish", "yarn publish", "pip upload", "twine upload", "cargo publish", "gem push", "mvn deploy",

        // Network/data exfiltration
        "curl | bash", "curl | sh", "wget | bash", "wget | sh", "nc -l", "ncat -l",

        // Process/job control
        "kill", "killall", "pkill", "taskkill",

        // Environment/shell manipulation
        "export", "setenv", "source", "eval",

        // Python dangerous patterns
        "python -c", "python3 -c", "pip install --force", "pip uninstall",

        // Node.js dangerous patterns
        "node -e", "node -p", "npm install -g",

        // Database operations
        "DROP TABLE", "DROP DATABASE", "TRUNCATE", "DELETE FROM",

        // Service management
        "systemctl stop", "systemctl disable", "systemctl restart", "service stop", "net stop"
    );

    private final BiFunction<String, Map<String, Object>, CompletableFuture<ConfirmationResult>> onConfirm;
    private final Predicate<String> isTrusted;
    private final Consumer<String> onTrust;
    private final Set<String> dangerousTools;
    private final Set<String> dangerousCommands;

    private ConfirmationHook(Builder builder) {
        this.onConfirm = builder.onConfirm;
        this.isTrusted = builder.isTrusted;
        this.onTrust = builder.onTrust;
        this.dangerousTools = builder.dangerousTools != null ? builder.dangerousTools : DANGEROUS_TOOLS;
        this.dangerousCommands = builder.dangerousCommands != null ? builder.dangerousCommands : DANGEROUS_COMMANDS;
    }

    @Override
    public List<HookPoint> hookPoints() {
        return List.of(HookPoint.BEFORE_TOOL_EXECUTE);
    }

    @Override
    public HookResult execute(HookContext context) {
        String toolName = context.toolName();
        Map<String, Object> toolArgs = context.toolArgs();

        if (!isDangerous(toolName, toolArgs)) {
            return HookResult.continue_();
        }

        // Generate trust key for this operation
        String trustKey = TrustKeyGenerator.getTrustKey(toolName, toolArgs);

        // Check if already trusted for this session
        if (isTrusted != null && isTrusted.test(trustKey)) {
            logger.info("Command {} is trusted for this session", trustKey);
            return HookResult.continue_();
        }

        try {
            // Synchronous confirmation (in real usage, this would be async)
            ConfirmationResult result = onConfirm.apply(toolName, toolArgs).join();

            if (result.confirmed()) {
                logger.info("User confirmed operation: {}", toolName);

                // Cache trust if user selected "allow for session"
                if (result.trustSession() && onTrust != null) {
                    onTrust.accept(trustKey);
                    logger.info("Command {} is now trusted for this session", trustKey);
                }

                return HookResult.continue_();
            } else {
                logger.info("User rejected operation: {}", toolName);
                return HookResult.abort("User rejected the operation");
            }

        } catch (Exception e) {
            logger.error("Confirmation callback error: {}", e.getMessage());
            return HookResult.abort("Confirmation failed: " + e.getMessage());
        }
    }

    /**
     * Check if the tool call is potentially dangerous.
     *
     * Rules:
     * - write/edit: Always require confirmation
     * - bash: Only if command matches dangerous patterns
     * - read/glob/grep: Never require confirmation
     */
    private boolean isDangerous(String toolName, Map<String, Object> args) {
        // File modification tools always require confirmation
        if (dangerousTools.contains(toolName)) {
            return true;
        }

        // Bash: check command content for dangerous patterns
        if ("bash".equals(toolName) && args != null) {
            Object commandObj = args.get("command");
            if (commandObj instanceof String command) {
                // Check for dangerous command patterns
                for (String dangerous : dangerousCommands) {
                    if (command.contains(dangerous)) {
                        return true;
                    }
                }
            }
        }

        return false;
    }

    /**
     * Create a builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private BiFunction<String, Map<String, Object>, CompletableFuture<ConfirmationResult>> onConfirm;
        private Predicate<String> isTrusted = null;
        private Consumer<String> onTrust = null;
        private Set<String> dangerousTools = null;
        private Set<String> dangerousCommands = null;

        /**
         * Set the confirmation callback.
         * This is called when a dangerous operation is detected.
         * The callback should show a dialog and return the user's decision.
         */
        public Builder onConfirm(BiFunction<String, Map<String, Object>, CompletableFuture<ConfirmationResult>> onConfirm) {
            this.onConfirm = onConfirm;
            return this;
        }

        /**
         * Set the trust check callback.
         * This is called to check if a trust key is already trusted for the session.
         */
        public Builder isTrusted(Predicate<String> isTrusted) {
            this.isTrusted = isTrusted;
            return this;
        }

        /**
         * Set the trust callback.
         * This is called when user selects "allow for session".
         */
        public Builder onTrust(Consumer<String> onTrust) {
            this.onTrust = onTrust;
            return this;
        }

        /**
         * Set custom dangerous tools.
         */
        public Builder dangerousTools(Set<String> dangerousTools) {
            this.dangerousTools = dangerousTools;
            return this;
        }

        /**
         * Set custom dangerous commands.
         */
        public Builder dangerousCommands(Set<String> dangerousCommands) {
            this.dangerousCommands = dangerousCommands;
            return this;
        }

        public ConfirmationHook build() {
            if (onConfirm == null) {
                throw new IllegalStateException("onConfirm callback is required");
            }
            return new ConfirmationHook(this);
        }
    }
}
