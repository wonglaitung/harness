package com.harness.loop.worktree;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CompletableFuture;

/**
 * Git worktree lifecycle manager.
 *
 * <p>Manages creation, tracking, and cleanup of git worktrees for
 * parallel goal execution in isolated environments.</p>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * WorktreeManager manager = new WorktreeManager("/path/to/repo");
 *
 * // Create worktree
 * WorktreeInfo info = manager.createWorktree("feature-auth", "main", true).join();
 *
 * // List active worktrees
 * for (String name : manager.listWorktrees()) {
 *     System.out.println("Active: " + name);
 * }
 *
 * // Cleanup
 * manager.cleanupWorktree("feature-auth").join();
 * }</pre>
 */
public class WorktreeManager {
    private static final Logger logger = LoggerFactory.getLogger(WorktreeManager.class);

    private final String repoRoot;
    private final Map<String, String> worktrees = new ConcurrentHashMap<>();

    /**
     * Create a new WorktreeManager.
     *
     * @param repoRoot Path to the main git repository root
     * @throws WorktreeError If repoRoot is not a valid git repository
     */
    public WorktreeManager(String repoRoot) {
        this.repoRoot = Paths.get(repoRoot).toAbsolutePath().toString();

        // Verify this is a git repository
        Path gitDir = Paths.get(this.repoRoot, ".git");
        if (!Files.isDirectory(gitDir) && !Files.isRegularFile(gitDir)) {
            throw new WorktreeError("Not a git repository: " + this.repoRoot);
        }

        // Recover orphaned worktrees from previous runs
        recoverOrphanedWorktrees();
    }

    /**
     * Recover orphaned worktrees from previous runs.
     */
    private void recoverOrphanedWorktrees() {
        try {
            ProcessBuilder pb = new ProcessBuilder("git", "worktree", "list", "--porcelain");
            pb.directory(new File(repoRoot));
            pb.redirectErrorStream(true);
            Process process = pb.start();

            BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
            String line;
            String currentPath = null;
            String expectedPrefix = repoRoot + "/" + WorktreeConfig.WORKTREES_DIR + "/";

            while ((line = reader.readLine()) != null) {
                if (line.startsWith("worktree ")) {
                    currentPath = line.substring("worktree ".length());
                } else if (line.startsWith("branch ") && currentPath != null) {
                    if (currentPath.startsWith(expectedPrefix)) {
                        String name = Paths.get(currentPath).getFileName().toString();
                        worktrees.put(name, currentPath);
                        logger.info("Recovered orphan worktree: {}", name);
                    }
                    currentPath = null;
                }
            }

            process.waitFor();

            if (!worktrees.isEmpty()) {
                logger.info("Recovered {} orphan worktree(s)", worktrees.size());
            }

        } catch (Exception e) {
            logger.warn("Failed to list worktrees for recovery: {}", e.getMessage());
        }
    }

    /**
     * Create a git worktree for isolated execution.
     *
     * @param name Unique name for this worktree
     * @param baseBranch Base branch to create from
     * @param createBranch If true, create a new branch named {@code name}
     * @return CompletableFuture with WorktreeInfo
     */
    public CompletableFuture<WorktreeInfo> createWorktree(String name, String baseBranch, boolean createBranch) {
        return CompletableFuture.supplyAsync(() -> {
            // Check if worktree already exists
            if (worktrees.containsKey(name)) {
                throw new WorktreeError("Worktree already exists: " + name);
            }

            String branchName = createBranch ? name : baseBranch;
            String worktreePath = repoRoot + "/" + WorktreeConfig.WORKTREES_DIR + "/" + name;

            // Build git worktree add command
            List<String> cmd = new ArrayList<>();
            cmd.add("git");
            cmd.add("worktree");
            cmd.add("add");

            if (createBranch) {
                cmd.add("-b");
                cmd.add(branchName);
            }

            cmd.add(worktreePath);
            cmd.add(baseBranch);

            logger.debug("Creating worktree: {}", String.join(" ", cmd));

            try {
                ProcessBuilder pb = new ProcessBuilder(cmd);
                pb.directory(new File(repoRoot));
                pb.redirectErrorStream(true);
                Process process = pb.start();

                int exitCode = process.waitFor();

                if (exitCode != 0) {
                    String output = readProcessOutput(process);
                    throw new WorktreeError("Failed to create worktree '" + name + "': " + output);
                }

                worktrees.put(name, worktreePath);
                logger.info("Created worktree: {} at {}", name, worktreePath);

                return new WorktreeInfo(worktreePath, branchName);

            } catch (IOException | InterruptedException e) {
                throw new WorktreeError("Failed to create worktree '" + name + "'", e);
            }
        });
    }

    /**
     * Remove a git worktree.
     *
     * @param name Name of the worktree to remove
     * @param force If true, force removal even with uncommitted changes
     * @return CompletableFuture with true if cleanup succeeded
     */
    public CompletableFuture<Boolean> cleanupWorktree(String name, boolean force) {
        return CompletableFuture.supplyAsync(() -> {
            String path = worktrees.get(name);
            if (path == null) {
                logger.warn("Worktree not found for cleanup: {}", name);
                return false;
            }

            List<String> cmd = new ArrayList<>();
            cmd.add("git");
            cmd.add("worktree");
            cmd.add("remove");
            cmd.add(path);

            if (force) {
                cmd.add("--force");
            }

            logger.debug("Removing worktree: {}", String.join(" ", cmd));

            try {
                ProcessBuilder pb = new ProcessBuilder(cmd);
                pb.directory(new File(repoRoot));
                pb.redirectErrorStream(true);
                Process process = pb.start();

                int exitCode = process.waitFor();

                if (exitCode != 0 && force) {
                    // Try prune
                    logger.warn("Force cleanup failed for {}, trying prune", name);
                    pruneWorktrees();
                }

                worktrees.remove(name);
                logger.info("Cleaned up worktree: {}", name);
                return true;

            } catch (IOException | InterruptedException e) {
                logger.warn("Failed to cleanup worktree {}: {}", name, e.getMessage());
                return false;
            }
        });
    }

    /**
     * Prune stale worktree references.
     */
    private void pruneWorktrees() {
        try {
            ProcessBuilder pb = new ProcessBuilder("git", "worktree", "prune");
            pb.directory(new File(repoRoot));
            Process process = pb.start();
            process.waitFor();
        } catch (IOException | InterruptedException e) {
            logger.warn("Failed to prune worktrees: {}", e.getMessage());
        }
    }

    /**
     * List all tracked worktrees.
     */
    public List<String> listWorktrees() {
        return new ArrayList<>(worktrees.keySet());
    }

    /**
     * Get the path to a worktree.
     */
    public String getWorktreePath(String name) {
        return worktrees.get(name);
    }

    /**
     * Get the number of commits in a worktree branch vs base branch.
     */
    public CompletableFuture<Integer> getCommitCount(String name, String baseBranch) {
        return CompletableFuture.supplyAsync(() -> {
            String path = worktrees.get(name);
            if (path == null) {
                return 0;
            }

            try {
                ProcessBuilder pb = new ProcessBuilder(
                        "git", "rev-list", "--count", baseBranch + "..HEAD");
                pb.directory(new File(path));
                pb.redirectErrorStream(true);
                Process process = pb.start();

                BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
                String line = reader.readLine().trim();
                process.waitFor();

                return Integer.parseInt(line);

            } catch (IOException | InterruptedException | NumberFormatException e) {
                return 0;
            }
        });
    }

    /**
     * Check if the main repository has uncommitted changes.
     */
    public CompletableFuture<Boolean> isDirty() {
        return CompletableFuture.supplyAsync(() -> {
            try {
                ProcessBuilder pb = new ProcessBuilder("git", "status", "--porcelain");
                pb.directory(new File(repoRoot));
                pb.redirectErrorStream(true);
                Process process = pb.start();

                BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
                String line = reader.readLine();
                process.waitFor();

                return line != null && !line.isEmpty();

            } catch (IOException | InterruptedException e) {
                return false;
            }
        });
    }

    /**
     * Clean up all tracked worktrees.
     */
    public CompletableFuture<Integer> cleanupAll(boolean force) {
        List<CompletableFuture<Boolean>> futures = new ArrayList<>();

        for (String name : new ArrayList<>(worktrees.keySet())) {
            futures.add(cleanupWorktree(name, force));
        }

        return CompletableFuture.allOf(futures.toArray(new CompletableFuture[0]))
                .thenApply(v -> (int) futures.stream().filter(f -> f.join()).count());
    }

    private String readProcessOutput(Process process) throws IOException {
        BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
        StringBuilder sb = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            sb.append(line).append("\n");
        }
        return sb.toString().trim();
    }

    /**
     * Info about a created worktree.
     */
    public record WorktreeInfo(String path, String branchName) {}

    @Override
    public String toString() {
        return "WorktreeManager{repoRoot='" + repoRoot + "', worktrees=" + worktrees.size() + "}";
    }
}
