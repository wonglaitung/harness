package com.harness.tools;

import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.core.Tool;
import com.harness.core.ToolCategory;
import com.harness.core.ToolContext;
import com.harness.core.ValidationResult;
import com.harness.types.ToolResult;

/**
 * Shell command execution tool.
 *
 * Executes shell commands with optional sandbox mode.
 */
public class BashTool implements Tool {

    private static final Logger logger = LoggerFactory.getLogger(BashTool.class);

    public static final String NAME = "bash";
    public static final long DEFAULT_TIMEOUT = 120_000L; // 2 minutes

    private final boolean sandboxMode;
    private final long defaultTimeout;

    public BashTool(boolean sandboxMode, long defaultTimeout) {
        this.sandboxMode = sandboxMode;
        this.defaultTimeout = defaultTimeout;
    }

    public BashTool(boolean sandboxMode) {
        this(sandboxMode, DEFAULT_TIMEOUT);
    }

    public BashTool() {
        this(true, DEFAULT_TIMEOUT);
    }

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public String description() {
        String mode = sandboxMode ? " (sandbox mode)" : "";
        return "Execute shell commands." + mode;
    }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "command", Map.of(
                    "type", "string",
                    "description", "Shell command to execute"
                ),
                "timeout", Map.of(
                    "type", "integer",
                    "description", "Timeout in milliseconds",
                    "default", DEFAULT_TIMEOUT
                )
            ),
            "required", List.of("command")
        );
    }

    @Override
    public ToolCategory category() {
        return ToolCategory.SYSTEM;
    }

    @Override
    public boolean isDangerous() {
        return true;
    }

    @Override
    public ValidationResult validate(Map<String, Object> args) {
        if (!args.containsKey("command")) {
            return ValidationResult.invalid("command is required");
        }

        String command = (String) args.get("command");
        if (command == null || command.isBlank()) {
            return ValidationResult.invalid("command cannot be empty");
        }

        return ValidationResult.valid();
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context) {
        String command = (String) args.get("command");
        long timeout = args.containsKey("timeout")
            ? ((Number) args.get("timeout")).longValue()
            : defaultTimeout;

        String workDir = context.workingDirectory();

        return CompletableFuture.supplyAsync(() -> {
            try {
                // Build process
                ProcessBuilder pb = new ProcessBuilder("bash", "-c", command);
                pb.directory(new File(workDir));
                pb.redirectErrorStream(true);

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
                boolean finished = process.waitFor(timeout, TimeUnit.MILLISECONDS);
                if (!finished) {
                    process.destroyForcibly();
                    return ToolResult.failure("", "Command timed out", NAME);
                }

                String outputStr = output.toString();
                int exitCode = process.exitValue();

                if (exitCode == 0) {
                    logger.info("Command executed successfully: {}", command);
                    return ToolResult.success("", outputStr, NAME);
                } else {
                    logger.warn("Command failed with exit code {}: {}", exitCode, command);
                    return ToolResult.failure("",
                        String.format("Command failed (exit code %d)\n%s", exitCode, outputStr), NAME);
                }

            } catch (Exception e) {
                logger.error("Command execution error: {}", e.getMessage());
                return ToolResult.failure("", "Execution error: " + e.getMessage(), NAME);
            }
        });
    }
}