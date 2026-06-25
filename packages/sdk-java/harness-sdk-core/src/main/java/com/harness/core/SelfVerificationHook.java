package com.harness.core;

import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Hook that automatically runs tests after code modifications.
 *
 * This creates a self-improving loop where the agent:
 * 1. Modifies code
 * 2. Tests are automatically run
 * 3. If tests fail, errors are injected back
 * 4. Agent fixes the issues
 * 5. Loop continues until tests pass
 *
 * Example:
 * <pre>
 * AgentHarness agent = AgentHarness.builder()
 *     .model("claude-sonnet-4-6")
 *     .build();
 *
 * agent.addHook(new SelfVerificationHook(
 *     SelfVerificationConfig.builder()
 *         .testCommand("mvn test")
 *         .verifyOnChange(true)
 *         .build()
 * ));
 *
 * // Tests will run automatically after code changes
 * agent.run("Fix the bug in src/main/java/Main.java").join();
 * </pre>
 */
public class SelfVerificationHook implements LifecycleHook {

    private static final Logger logger = LoggerFactory.getLogger(SelfVerificationHook.class);

    private final SelfVerificationConfig config;
    private final Map<String, Integer> retryCount = new ConcurrentHashMap<>();
    private final Map<String, String> lastTestResults = new ConcurrentHashMap<>();

    public SelfVerificationHook(SelfVerificationConfig config) {
        this.config = config;
    }

    public SelfVerificationHook() {
        this(SelfVerificationConfig.defaults());
    }

    @Override
    public List<HookPoint> hookPoints() {
        return List.of(HookPoint.AFTER_TOOL_EXECUTE);
    }

    @Override
    public HookResult execute(HookContext context) {
        if (context.hookPoint() != HookPoint.AFTER_TOOL_EXECUTE) {
            return HookResult.continue_();
        }

        String toolName = context.toolName();
        if (toolName == null || !config.triggerTools().contains(toolName)) {
            return HookResult.continue_();
        }

        // Check if we should verify
        if (!config.verifyOnChange()) {
            return HookResult.continue_();
        }

        // Run tests
        logger.info("Self-verification: Running tests after {}", toolName);

        Map<String, Object> testResult = runTests(context);

        if (testResult == null) {
            // No tests to run or error
            return HookResult.continue_();
        }

        boolean success = (boolean) testResult.get("success");

        if (success) {
            logger.info("Self-verification: Tests passed");
            retryCount.remove(context.sessionId());
            return HookResult.continue_();
        }

        // Tests failed - inject error message
        String sessionKey = context.sessionId();
        retryCount.put(sessionKey, retryCount.getOrDefault(sessionKey, 0) + 1);

        if (retryCount.get(sessionKey) > config.maxRetries()) {
            logger.warn("Self-verification: Max retries ({}) reached, stopping verification loop", config.maxRetries());
            retryCount.remove(sessionKey);
            return HookResult.continue_();
        }

        logger.info("Self-verification: Tests failed, injecting error (attempt {}/{})", retryCount.get(sessionKey), config.maxRetries());

        // Build error message
        String errorMessage = buildErrorMessage(testResult, context);

        // Inject as user message
        return HookResult.injectMessage(new com.harness.types.Message(
            "user",
            errorMessage,
            Map.of("type", "test_failure", "injected", true)
        ));
    }

    /**
     * Run the test command and return results.
     */
    private Map<String, Object> runTests(HookContext context) {
        Path workDir = config.workingDirectory() != null
            ? config.workingDirectory()
            : Path.of(System.getProperty("user.dir"));

        // Check if tests exist
        if (config.skipIfNoTests() && !hasTests(workDir)) {
            logger.info("Self-verification: No tests found, skipping");
            return null;
        }

        try {
            ProcessBuilder pb = new ProcessBuilder(config.testCommand());
            pb.directory(workDir.toFile());
            pb.redirectErrorStream(true);

            Process process = pb.start();

            // Read output
            StringBuilder output = new StringBuilder();
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    output.append(line).append("\n");
                }
            }

            boolean completed = process.waitFor(config.timeout(), TimeUnit.SECONDS);

            if (!completed) {
                process.destroyForcibly();
                logger.warn("Self-verification: Tests timed out after {}s", config.timeout());
                return Map.of(
                    "success", false,
                    "output", "",
                    "error", "Test execution timed out after " + config.timeout() + " seconds",
                    "returncode", -1
                );
            }

            int returnCode = process.exitValue();
            boolean success = returnCode == 0;

            String outputStr = output.toString();
            lastTestResults.put(context.sessionId(), outputStr);

            return Map.of(
                "success", success,
                "output", outputStr,
                "error", "",
                "returncode", returnCode
            );

        } catch (IOException e) {
            logger.warn("Self-verification: Test command not found: {}", config.testCommand());
            return null;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            logger.warn("Self-verification: Interrupted");
            return null;
        } catch (Exception e) {
            logger.error("Self-verification: Error running tests: {}", e.getMessage());
            return Map.of(
                "success", false,
                "output", "",
                "error", e.getMessage(),
                "returncode", -1
            );
        }
    }

    /**
     * Check if any test files exist.
     */
    private boolean hasTests(Path workDir) {
        // Check common test directories
        String[] testDirs = {"src/test/java", "test", "tests", "src/test"};

        for (String testDir : testDirs) {
            Path testPath = workDir.resolve(testDir);
            if (Files.exists(testPath)) {
                try {
                    // Check for test files
                    try (var stream = Files.walk(testPath)) {
                        boolean hasTests = stream
                            .filter(Files::isRegularFile)
                            .anyMatch(p -> p.getFileName().toString().matches(config.testPattern()));
                        if (hasTests) {
                            return true;
                        }
                    }
                } catch (IOException e) {
                    // Ignore
                }
            }
        }

        return false;
    }

    /**
     * Build the error message to inject.
     */
    private String buildErrorMessage(Map<String, Object> testResult, HookContext context) {
        String output = (String) testResult.get("output");
        String error = (String) testResult.get("error");

        // Truncate if too long
        int maxLen = 2000;
        String combined = (output + "\n" + error).trim();
        if (combined.length() > maxLen) {
            combined = combined.substring(0, maxLen) + "\n... [output truncated]";
        }

        int retries = retryCount.getOrDefault(context.sessionId(), 0);

        return String.format(
            "[自验证] 测试失败 (尝试 %d/%d)\n\n" +
            "测试输出：\n```\n%s\n```\n\n" +
            "请修复上述测试失败的问题。确保：\n" +
            "1. 分析错误信息找出根本原因\n" +
            "2. 修复代码中的问题\n" +
            "3. 重新运行测试确认修复成功",
            retries, config.maxRetries(), combined
        );
    }

    @Override
    public void reset(String sessionId) {
        retryCount.remove(sessionId);
        lastTestResults.remove(sessionId);
    }

    @Override
    public void reset() {
        retryCount.clear();
        lastTestResults.clear();
    }

    /**
     * Get the last test results for a session.
     */
    public String getLastTestResults(String sessionId) {
        return lastTestResults.get(sessionId);
    }
}
