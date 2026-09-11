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
import java.util.regex.Pattern;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Lightweight sandbox executor (M6-C enhanced).
 *
 * Provides basic command isolation through:
 * - Command pattern blocking (with normalization to defeat obfuscation)
 * - Optional command whitelist
 * - Clean environment variables
 * - Execution timeout
 *
 * <p>M6 additions: parse-level validation — {@link #normalizeCommand(String)},
 * {@link #tokenizeCommand(String)}, {@link #validatePathWrite(String)},
 * {@link #validateToolOutput(String)}.</p>
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
     * Dangerous paths (read + general).
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
     * Write-specific dangerous path prefixes (M6-C).
     * WriteTool/EditTool must reject these targets.
     */
    private static final List<String> WRITE_DANGEROUS_PATHS = List.of(
        "/etc",
        "/boot",
        "/dev",
        "/proc",
        "/sys",
        "/root",
        "/usr",
        "/var",
        "~/.ssh",
        "~/.aws",
        "~/.gnupg",
        "/"
    );

    /**
     * Dangerous output patterns for tool return content (M6-C).
     */
    private static final List<String> DANGEROUS_OUTPUT_PATTERNS = List.of(
        "curl",
        "wget",
        "bash",
        "sh",
        "python",
        "perl",
        "ruby",
        "nc",
        "ncat",
        "socat",
        "chmod",
        "chown",
        "rm -rf",
        "mkfs",
        "> /etc/",
        "> /dev/"
    );

    /** Patterns with pipe (command injection via tool output). */
    private static final List<Pattern> PIPE_PATTERNS = List.of(
        Pattern.compile("\\|\\s*bash"),
        Pattern.compile("\\|\\s*sh"),
        Pattern.compile("\\|\\s*python"),
        Pattern.compile("\\|\\s*perl"),
        Pattern.compile("\\|\\s*ruby"),
        Pattern.compile("\\|\\s*nc")
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

    // ------------------------------------------------------------------
    // M6-C: Parse-level validation methods
    // ------------------------------------------------------------------

    /**
     * Normalize a command string (M6-C).
     *
     * <p>Removes backslash obfuscation ({@code cu\rl} → {@code curl}),
     * collapses redundant whitespace, and strips leading/trailing spaces.
     * Used before pattern matching to defeat simple obfuscation.</p>
     *
     * @param command raw command
     * @return normalized command
     */
    public static String normalizeCommand(String command) {
        if (command == null) {
            return null;
        }
        // Remove backslash before whitespace (cu\rl → curl)
        String normalized = command.replaceAll("\\\\\\s", "");
        // Collapse multiple spaces
        normalized = normalized.replaceAll("\\s{2,}", " ").trim();
        return normalized;
    }

    /**
     * Tokenize a shell command (M6-C).
     *
     * <p>Strips single/double quotes and backslash escapes, then splits on
     * shell metacharacters ({@code |}, {@code &}, {@code ;}, {@code >},
     * {@code <}).  Useful for extracting the base command for whitelist
     * checking after normalization.</p>
     *
     * @param command raw or normalized command
     * @return list of tokens (first token is typically the base command)
     */
    public static List<String> tokenizeCommand(String command) {
        if (command == null || command.isBlank()) {
            return List.of();
        }

        List<String> tokens = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        boolean inSingleQuote = false;
        boolean inDoubleQuote = false;
        boolean escaped = false;

        for (int i = 0; i < command.length(); i++) {
            char c = command.charAt(i);

            if (escaped) {
                current.append(c);
                escaped = false;
                continue;
            }

            if (c == '\\' && !inSingleQuote) {
                escaped = true;
                continue;
            }

            if (c == '\'' && !inDoubleQuote) {
                inSingleQuote = !inSingleQuote;
                continue;
            }

            if (c == '"' && !inSingleQuote) {
                inDoubleQuote = !inDoubleQuote;
                continue;
            }

            if (!inSingleQuote && !inDoubleQuote) {
                if (c == '|' || c == '&' || c == ';' || c == '>' || c == '<') {
                    if (!current.isEmpty()) {
                        tokens.add(current.toString());
                        current.setLength(0);
                    }
                    tokens.add(String.valueOf(c));
                    continue;
                }
                if (c == ' ' || c == '\t') {
                    if (!current.isEmpty()) {
                        tokens.add(current.toString());
                        current.setLength(0);
                    }
                    continue;
                }
            }

            current.append(c);
        }

        if (!current.isEmpty()) {
            tokens.add(current.toString());
        }

        return tokens;
    }

    /**
     * Validate a write path (M6-C).
     *
     * <p>Checks the target path against system/sensitive directories.
     * Used by WriteTool/EditTool before writing files.  Complements
     * {@link com.harness.security.FileInputValidator#validatePath} with
     * write-specific semantics.</p>
     *
     * @param target path to validate for writing
     * @return validation result (isValid=false means blocked)
     */
    public static PathValidation validatePathWrite(String target) {
        if (target == null || target.isBlank()) {
            return new PathValidation(false, "Empty path");
        }

        String expanded = expandPath(target);

        for (String dangerous : WRITE_DANGEROUS_PATHS) {
            String expandedDangerous = expandPath(dangerous);
            if (dangerous.equals("/")) {
                // Root: block only exact root or paths starting with / without further components
                if (expanded.equals("/") || expanded.equals("")) {
                    return new PathValidation(false, "Writes to root filesystem are forbidden");
                }
            } else if (expanded.startsWith(expandedDangerous + "/") || expanded.equals(expandedDangerous)) {
                return new PathValidation(false, "Writes to system path " + dangerous + " are forbidden");
            }
        }

        return new PathValidation(true, "");
    }

    /**
     * Validate tool output content (M6-C).
     *
     * <p>Scans output from MCP/side-effect tools for dangerous instructions
     * (e.g., embedded shell commands, pipe-to-bash patterns).  This is a
     * <b>parse-level</b> check only — semantic injection re-scanning is
     * intentionally avoided to prevent false positives on legitimate output.</p>
     *
     * @param text tool output text
     * @return validation result (isValid=false means blocked)
     */
    public static PathValidation validateToolOutput(String text) {
        if (text == null || text.isBlank()) {
            return new PathValidation(true, "");
        }

        String lower = text.toLowerCase();

        // Check for pipe-to-shell patterns
        for (Pattern pipePattern : PIPE_PATTERNS) {
            if (pipePattern.matcher(text).find()) {
                return new PathValidation(false, "Tool output contains pipe-to-shell pattern: " + pipePattern.pattern());
            }
        }

        // Check for redirect-to-system patterns
        if (lower.contains("> /etc/") || lower.contains("> /dev/") || lower.contains("> /proc/")) {
            return new PathValidation(false, "Tool output contains redirect to system path");
        }

        // Check for fork bomb
        if (text.contains(":(){ :|:& };:")) {
            return new PathValidation(false, "Tool output contains fork bomb pattern");
        }

        return new PathValidation(true, "");
    }

    /**
     * Expand path (handle ~).
     */
    private static String expandPath(String path) {
        if (path.startsWith("~")) {
            String home = System.getProperty("user.home");
            return home + path.substring(1);
        }
        return path;
    }

    // ------------------------------------------------------------------
    // Core sandbox operations
    // ------------------------------------------------------------------

    /**
     * Validate command safety (M6-C: now normalizes before checking).
     *
     * @param command command to validate
     * @return CommandValidation with (is_valid, reason)
     */
    public CommandValidation validateCommand(String command) {
        if (command == null || command.isBlank()) {
            return new CommandValidation(false, "Empty command");
        }

        // M6-C: normalize first to defeat obfuscation
        String normalized = normalizeCommand(command);

        // Check blocked patterns (on normalized form)
        for (String pattern : config.blockedPatterns()) {
            if (normalized.contains(pattern)) {
                return new CommandValidation(false, "Blocked pattern: " + pattern);
            }
        }

        // Check whitelist (use tokenize to extract base command)
        if (config.allowedCommands() != null && !config.allowedCommands().isEmpty()) {
            List<String> tokens = tokenizeCommand(normalized);
            if (!tokens.isEmpty()) {
                String cmdBase = tokens.get(0);
                if (!config.allowedCommands().contains(cmdBase)) {
                    return new CommandValidation(false, "Command not in whitelist: " + cmdBase);
                }
            }
        }

        // Check dangerous paths (on normalized form)
        for (String path : DANGEROUS_PATHS) {
            String expanded = expandPath(path);
            if (normalized.contains(expanded)) {
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
     * Command validation result.
     */
    public record CommandValidation(boolean isValid, String reason) {
    }

    /**
     * Path/tool-output validation result (M6-C).
     */
    public record PathValidation(boolean isValid, String reason) {
    }
}
