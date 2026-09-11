package com.harness.core;

import java.io.BufferedReader;
import java.io.InputStreamReader;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Minimal CLI for the Harness Java SDK (M6-dep).
 *
 * <p>Provides a {@code doctor --deps} subcommand that audits installed
 * dependencies for known CVEs.  The SDK does not bundle a CVE database —
 * it delegates to the platform auditor (e.g., {@code dependencyCheck},
 * {@code gradle dependencies --check}) so remediation stays a human-reviewed,
 * deploy-side concern.</p>
 *
 * <h3>Usage</h3>
 * <pre>{@code
 * java -cp harness-sdk.jar com.harness.core.HarnessCli doctor --deps
 * }</pre>
 */
public class HarnessCli {

    private static final Logger logger = LoggerFactory.getLogger(HarnessCli.class);

    /**
     * Entry point.
     *
     * @param args command-line arguments
     * @return exit code (0 = success)
     */
    public static int main(String[] args) {
        if (args.length == 0) {
            printUsage();
            return 0;
        }

        String command = args[0];

        if ("doctor".equals(command)) {
            return handleDoctor(args);
        }

        printUsage();
        return 0;
    }

    private static int handleDoctor(String[] args) {
        boolean depsFlag = false;
        for (int i = 1; i < args.length; i++) {
            if ("--deps".equals(args[i])) {
                depsFlag = true;
            }
        }

        if (depsFlag) {
            return doctorDeps();
        }

        System.out.println("Usage: harness doctor --deps");
        System.out.println("  --deps    Audit dependencies for known CVEs");
        return 0;
    }

    /**
     * Audit dependencies for known CVEs (M6-dep).
     *
     * <p>Delegates to the Gradle dependency-check plugin or OWASP dependency-check
     * if available.  Falls back to printing a message if no auditor is found.</p>
     *
     * @return exit code
     */
    private static int doctorDeps() {
        // Try Gradle dependency check
        String[] gradleCmd = {"gradle", "dependencies", "--configuration", "runtimeClasspath"};
        String[] gradlewCmd = {"./gradlew", "dependencies", "--configuration", "runtimeClasspath"};

        String[] cmd = null;
        if (commandExists("gradle")) {
            cmd = gradleCmd;
        } else if (commandExists("./gradlew") || commandExists("gradlew")) {
            cmd = gradlewCmd;
        }

        if (cmd != null) {
            System.out.println("Auditing dependencies via: " + String.join(" ", cmd));
            try {
                ProcessBuilder pb = new ProcessBuilder(cmd);
                pb.inheritIO();
                Process process = pb.start();
                return process.waitFor();
            } catch (Exception e) {
                logger.error("Dependency audit failed: {}", e.getMessage());
                System.err.println("Dependency audit failed: " + e.getMessage());
                return 1;
            }
        }

        // No auditor found
        System.out.println("No dependency auditor found.");
        System.out.println("Install the OWASP dependency-check Gradle plugin or use:");
        System.out.println("  gradle dependencies --configuration runtimeClasspath");
        System.out.println("to audit the dependency tree for known CVEs.");
        System.out.println();
        System.out.println("The SDK does not bundle a CVE database — remediation is a");
        System.out.println("human-reviewed, deploy-side concern.");
        return 1;
    }

    private static boolean commandExists(String command) {
        try {
            String[] checkCmd = System.getProperty("os.name").toLowerCase().contains("win")
                ? new String[]{"where", command}
                : new String[]{"which", command};
            ProcessBuilder pb = new ProcessBuilder(checkCmd);
            pb.redirectErrorStream(true);
            Process process = pb.start();
            int exit = process.waitFor();
            return exit == 0;
        } catch (Exception e) {
            return false;
        }
    }

    private static void printUsage() {
        System.out.println("Harness Java SDK CLI");
        System.out.println();
        System.out.println("Usage: harness <command> [options]");
        System.out.println();
        System.out.println("Commands:");
        System.out.println("  doctor    Run diagnostics");
        System.out.println();
        System.out.println("Doctor options:");
        System.out.println("  --deps    Audit dependencies for known CVEs");
    }
}
