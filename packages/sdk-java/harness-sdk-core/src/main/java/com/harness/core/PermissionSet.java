package com.harness.core;

import java.nio.file.Path;
import java.util.HashSet;
import java.util.Set;

/**
 * Defines permissions for tool execution.
 *
 * Controls what paths, commands, and networks tools can access.
 *
 * Example:
 * <pre>
 * // Full access
 * PermissionSet full = PermissionSet.fullAccess();
 *
 * // Read-only
 * PermissionSet readOnly = PermissionSet.readOnly(List.of("/workspace"));
 *
 * // Sandbox
 * PermissionSet sandbox = PermissionSet.sandbox("/workspace", false);
 *
 * // Check permissions
 * if (perms.isPathAllowed("/workspace/file.txt", "read")) {
 *     // Allow read
 * }
 * </pre>
 */
public class PermissionSet {

    private final Set<Path> allowedReadPaths;
    private final Set<Path> allowedWritePaths;
    private final Set<String> allowedCommands;
    private final Set<String> blockedCommands;
    private final Set<String> allowedHosts;
    private final boolean networkEnabled;

    public PermissionSet() {
        this.allowedReadPaths = new HashSet<>();
        this.allowedWritePaths = new HashSet<>();
        this.allowedCommands = new HashSet<>();
        this.blockedCommands = new HashSet<>();
        this.allowedHosts = new HashSet<>();
        this.networkEnabled = false;
    }

    public PermissionSet(
        Set<Path> allowedReadPaths,
        Set<Path> allowedWritePaths,
        Set<String> allowedCommands,
        Set<String> blockedCommands,
        Set<String> allowedHosts,
        boolean networkEnabled
    ) {
        this.allowedReadPaths = allowedReadPaths != null ? allowedReadPaths : new HashSet<>();
        this.allowedWritePaths = allowedWritePaths != null ? allowedWritePaths : new HashSet<>();
        this.allowedCommands = allowedCommands != null ? allowedCommands : new HashSet<>();
        this.blockedCommands = blockedCommands != null ? blockedCommands : new HashSet<>();
        this.allowedHosts = allowedHosts != null ? allowedHosts : new HashSet<>();
        this.networkEnabled = networkEnabled;
    }

    /**
     * Create a permission set with full access.
     */
    public static PermissionSet fullAccess() {
        return new PermissionSet(null, null, null, null, null, true);
    }

    /**
     * Create a read-only permission set.
     */
    public static PermissionSet readOnly(java.util.List<String> paths) {
        PermissionSet perms = new PermissionSet();
        if (paths != null) {
            for (String p : paths) {
                perms.allowedReadPaths.add(Path.of(p));
            }
        }
        return perms;
    }

    /**
     * Create a sandboxed permission set.
     *
     * @param workspace Base directory for file operations
     * @param allowNetwork Whether to allow network access
     */
    public static PermissionSet sandbox(String workspace, boolean allowNetwork) {
        Path workspacePath = Path.of(workspace).toAbsolutePath().normalize();
        Path harnessDir = Path.of(System.getProperty("user.home")).resolve(".harness");
        Path tempDir = Path.of(System.getProperty("java.io.tmpdir"));

        Set<Path> readPaths = new HashSet<>();
        readPaths.add(workspacePath);
        readPaths.add(harnessDir);
        readPaths.add(tempDir);

        Set<Path> writePaths = new HashSet<>();
        writePaths.add(workspacePath);
        writePaths.add(tempDir);

        return new PermissionSet(
            readPaths,
            writePaths,
            new HashSet<>(),  // Allow all commands
            new HashSet<>(),  // No blocked commands
            new HashSet<>(),
            allowNetwork
        );
    }

    /**
     * Check if a path is accessible.
     *
     * @param path Path to check
     * @param mode "read" or "write"
     * @return True if access is allowed
     */
    public boolean isPathAllowed(String path, String mode) {
        Set<Path> allowed = "write".equals(mode) ? allowedWritePaths : allowedReadPaths;

        // For write mode, if no write paths specified, deny by default
        // (unless read paths are also empty, meaning full access)
        if ("write".equals(mode) && allowed.isEmpty() && !allowedReadPaths.isEmpty()) {
            return false;
        }

        // For read mode, if no read paths specified, allow all
        if (allowed.isEmpty()) {
            return true;
        }

        try {
            Path checkPath = Path.of(path).toAbsolutePath().normalize();

            for (Path allowedPath : allowed) {
                if (checkPath.startsWith(allowedPath)) {
                    return true;
                }
            }
        } catch (Exception e) {
            return false;
        }

        return false;
    }

    /**
     * Check if a command is allowed.
     */
    public boolean isCommandAllowed(String command) {
        if (command == null || command.isEmpty()) {
            return true;
        }

        String baseCmd = command.split("\\s+")[0];

        // Check blocked first
        if (blockedCommands.contains(baseCmd)) {
            return false;
        }

        // If no allowed commands specified, allow all non-blocked
        if (allowedCommands.isEmpty()) {
            return true;
        }

        return allowedCommands.contains(baseCmd);
    }

    /**
     * Check if a host is accessible.
     */
    public boolean isHostAllowed(String host) {
        if (!networkEnabled) {
            return false;
        }

        if (allowedHosts.isEmpty()) {
            return true;
        }

        return allowedHosts.contains(host);
    }

    /**
     * Merge with another permission set.
     */
    public PermissionSet merge(PermissionSet other) {
        Set<Path> mergedRead = new HashSet<>(this.allowedReadPaths);
        mergedRead.addAll(other.allowedReadPaths);

        Set<Path> mergedWrite = new HashSet<>(this.allowedWritePaths);
        mergedWrite.addAll(other.allowedWritePaths);

        Set<String> mergedAllowedCmds = new HashSet<>(this.allowedCommands);
        mergedAllowedCmds.addAll(other.allowedCommands);

        Set<String> mergedBlockedCmds = new HashSet<>(this.blockedCommands);
        mergedBlockedCmds.addAll(other.blockedCommands);

        Set<String> mergedHosts = new HashSet<>(this.allowedHosts);
        mergedHosts.addAll(other.allowedHosts);

        return new PermissionSet(
            mergedRead,
            mergedWrite,
            mergedAllowedCmds,
            mergedBlockedCmds,
            mergedHosts,
            this.networkEnabled || other.networkEnabled
        );
    }

    // Getters
    public Set<Path> getAllowedReadPaths() { return new HashSet<>(allowedReadPaths); }
    public Set<Path> getAllowedWritePaths() { return new HashSet<>(allowedWritePaths); }
    public Set<String> getAllowedCommands() { return new HashSet<>(allowedCommands); }
    public Set<String> getBlockedCommands() { return new HashSet<>(blockedCommands); }
    public Set<String> getAllowedHosts() { return new HashSet<>(allowedHosts); }
    public boolean isNetworkEnabled() { return networkEnabled; }
}
