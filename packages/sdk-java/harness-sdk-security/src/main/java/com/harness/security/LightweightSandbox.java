package com.harness.security;

import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Lightweight sandbox executor.
 *
 * Provides basic command isolation through:
 * - Command pattern blocking
 * - Optional command whitelist
 * - Clean environment variables
 * - Execution timeout
 */
public class LightweightSandbox {

    private static final Logger logger = LoggerFactory.getLogger(LightweightSandbox.class);

    /**
     * Default blocked patterns.
     */
    public static final List<String> DEFAULT_BLOCKED_PATTERNS = List.of(
        "rm -rf",
        "sudo",
        "chmod",
        "chown",
        "mkfs",
        "dd if=",
        "> /dev/",
        "curl | bash",
        "wget | bash",
        ":(){ :|:& };:",  // Fork bomb
        "rm -rf /",
        "rm -rf ~",
        "chmod -R 777",
        "> /etc/",
        "> ~/.ssh/"
    );

    /**
     * Dangerous paths.
     */
    public static final List<String> DANGEROUS_PATHS = List.of(
        "/etc",
        "/root",
        "~/.ssh",
        "~/.aws",
        "~/.gnupg",
        "~/.config"
    );

    /**
     * Sensitive environment variables to remove.
     */
    public static final Set<String> SENSITIVE_ENV_VARS = Set.of(
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "GITHUB_TOKEN",
        "GITLAB_TOKEN",
        "DATABASE_URL",
        "DB_PASSWORD"
    );

    /**
     * Safe environment variables to keep.
     */
    public static final Set<String> SAFE_ENV_VARS = Set.of(
        "PATH",
        "HOME",
        "USER",
        "LANG",
        "LC_ALL",
        "TERM"
    );

    private final SandboxConfig config;

    /**
     * Create sandbox with default configuration.
     */
    public LightweightSandbox() {
        this(SandboxConfig.defaultConfig());
    }

    /**
     * Create sandbox with custom configuration.
     *
     * @param config sandbox configuration
     */
    public LightweightSandbox(SandboxConfig config) {
        this.config = config;
    }

    /**
     * Validate command safety.
     *
     * @param command command to validate
     * @return ValidationResult with (is_valid, reason)
     */
    public CommandValidation validateCommand(String command) {
        if (command == null || command.isBlank()) {
            return new CommandValidation(false, "Empty command");
        }

        // Check blocked patterns
        for (String pattern : config.blockedPatterns()) {
            if (command.contains(pattern)) {
                return new CommandValidation(false, "Blocked pattern: " + pattern);
            }
        }

        // Check whitelist
        if (config.allowedCommands() != null && !config.allowedCommands().isEmpty()) {
            String cmdBase = command.split("\\s+")[0];
            if (!config.allowedCommands().contains(cmdBase)) {
                return new CommandValidation(false, "Command not in whitelist: " + cmdBase);
            }
        }

        // Check dangerous paths
        for (String path : DANGEROUS_PATHS) {
            String expanded = expandPath(path);
            if (command.contains(expanded)) {
                return new CommandValidation(false, "Dangerous path: " + path);
            }
        }

        return new CommandValidation(true, "");
    }

    /**
     * Execute command in sandbox.
     *
     * @param command command to execute
     * @return CompletableFuture with SandboxResult
     */
    public CompletableFuture<SandboxResult> execute(String command) {
        return execute(command, null, null, null);
    }

    /**
     * Execute command in sandbox.
     *
     * @param command command to execute
     * @param cwd working directory
     * @param env additional environment variables
     * @param timeout execution timeout (overrides config)
     * @return CompletableFuture with SandboxResult
     */
    public CompletableFuture<SandboxResult> execute(
            String command,
            String cwd,
            Map<String, String> env,
            Double timeout) {

        return CompletableFuture.supplyAsync(() -> {
            // Validate command
            CommandValidation validation = validateCommand(command);
            if (!validation.isValid()) {
                logger.warn("Command blocked: {}", validation.reason());
                return SandboxResult.failure(validation.reason());
            }

            // Build clean environment
            Map<String, String> cleanEnv = buildCleanEnv(env);

            try {
                // Build process
                ProcessBuilder pb = new ProcessBuilder("bash", "-c", command);
                if (cwd != null) {
                    pb.directory(new File(cwd));
                }
                pb.redirectErrorStream(true);
                pb.environment().clear();
                pb.environment().putAll(cleanEnv);

                // Start process
                Process process = pb.start();

                // Read output
                StringBuilder output = new StringBuilder();
                try (BufferedReader reader = new BufferedReader(
                        new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
                    String line;
                    while ((line = reader.readLine()) != null) {
                        output.append(line).append("\n");
                    }
                }

                // Wait for completion
                double timeoutSeconds = timeout != null ? timeout : config.maxExecutionTime();
                long timeoutMs = (long) (timeoutSeconds * 1000);
                boolean finished = process.waitFor(timeoutMs, TimeUnit.MILLISECONDS);

                if (!finished) {
                    process.destroyForcibly();
                    logger.warn("Command timed out after {}s: {}", timeoutSeconds, command);
                    return SandboxResult.timeout(timeoutSeconds);
                }

                // Truncate output if needed
                String stdout = output.toString();
                if (stdout.length() > config.maxOutputSize()) {
                    stdout = stdout.substring(0, config.maxOutputSize());
                }

                int exitCode = process.exitValue();

                if (exitCode == 0) {
                    logger.info("Command executed successfully: {}", command);
                    return SandboxResult.success(stdout, "", exitCode);
                } else {
                    logger.warn("Command failed with exit code {}: {}", exitCode, command);
                    return SandboxResult.failure(stdout, "", exitCode);
                }

            } catch (Exception e) {
                logger.error("Command execution error: {}", e.getMessage());
                return SandboxResult.failure("Execution error: " + e.getMessage());
            }
        });
    }

    /**
     * Build clean environment variables.
     *
     * Removes sensitive variables and keeps only safe ones.
     */
    private Map<String, String> buildCleanEnv(Map<String, String> extraEnv) {
        Map<String, String> env = new HashMap<>();

        // Keep safe variables
        Set<String> safeVars = new HashSet<>(SAFE_ENV_VARS);
        if (config.allowedEnvVars() != null) {
            safeVars.addAll(config.allowedEnvVars());
        }

        for (String var : safeVars) {
            String value = System.getenv(var);
            if (value != null) {
                env.put(var, value);
            }
        }

        // Remove sensitive variables
        for (String var : SENSITIVE_ENV_VARS) {
            env.remove(var);
        }

        // Add extra environment
        if (extraEnv != null) {
            env.putAll(extraEnv);
        }

        return env;
    }

    /**
     * Expand path (handle ~).
     */
    private String expandPath(String path) {
        if (path.startsWith("~")) {
            String home = System.getProperty("user.home");
            return home + path.substring(1);
        }
        return path;
    }

    /**
     * Command validation result.
     */
    public record CommandValidation(boolean isValid, String reason) {
    }
}