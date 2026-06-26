package com.harness.tools;

import java.io.IOException;
import java.nio.file.FileSystems;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.PathMatcher;
import java.nio.file.SimpleFileVisitor;
import java.nio.file.FileVisitResult;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.core.Tool;
import com.harness.core.ToolCategory;
import com.harness.core.ToolContext;
import com.harness.core.ValidationResult;
import com.harness.types.ToolResult;

/**
 * File pattern matching tool.
 *
 * Uses glob patterns to search for files.
 */
public class GlobTool implements Tool {

    private static final Logger logger = LoggerFactory.getLogger(GlobTool.class);

    public static final String NAME = "glob";

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public String description() {
        return "Search for files using glob patterns (e.g., **/*.java)";
    }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "pattern", Map.of(
                    "type", "string",
                    "description", "Glob pattern like **/*.java"
                ),
                "path", Map.of(
                    "type", "string",
                    "description", "Search directory (optional, defaults to working directory)"
                )
            ),
            "required", List.of("pattern")
        );
    }

    @Override
    public ToolCategory category() {
        return ToolCategory.FILE_SYSTEM;
    }

    @Override
    public ValidationResult validate(Map<String, Object> args) {
        if (!args.containsKey("pattern")) {
            return ValidationResult.invalid("pattern is required");
        }

        String pattern = (String) args.get("pattern");
        if (pattern == null || pattern.isBlank()) {
            return ValidationResult.invalid("pattern cannot be empty");
        }

        return ValidationResult.valid();
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context) {
        return CompletableFuture.supplyAsync(() -> {
            String pattern = (String) args.get("pattern");
            String basePath = args.containsKey("path") && args.get("path") != null
                ? (String) args.get("path")
                : context.workingDirectory();

            try {
                Path rootPath = Path.of(basePath);
                if (!Files.exists(rootPath)) {
                    return ToolResult.failure("", "Directory does not exist: " + basePath, NAME);
                }

                PathMatcher matcher = FileSystems.getDefault().getPathMatcher("glob:" + pattern);
                List<String> matches = new ArrayList<>();

                Files.walkFileTree(rootPath, new SimpleFileVisitor<Path>() {
                    @Override
                    public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) {
                        // Match against relative path for glob patterns like **/*.java
                        Path relative = rootPath.relativize(file);
                        if (matcher.matches(relative) || matcher.matches(file.getFileName())) {
                            matches.add(file.toString());
                        }
                        return FileVisitResult.CONTINUE;
                    }

                    @Override
                    public FileVisitResult visitFileFailed(Path file, IOException exc) {
                        return FileVisitResult.CONTINUE;
                    }
                });

                // Sort by modification time (newest first)
                matches.sort((a, b) -> {
                    try {
                        return -Files.getLastModifiedTime(Path.of(a))
                            .compareTo(Files.getLastModifiedTime(Path.of(b)));
                    } catch (IOException e) {
                        return 0;
                    }
                });

                String result = String.join("\n", matches);
                if (result.isEmpty()) {
                    result = "No files found matching pattern: " + pattern;
                }

                logger.info("Found {} files matching {}", matches.size(), pattern);
                return ToolResult.success("", result, NAME);

            } catch (IOException e) {
                logger.error("Glob search failed: {}", e.getMessage());
                return ToolResult.failure("", "Search failed: " + e.getMessage(), NAME);
            }
        });
    }
}