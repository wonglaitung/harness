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
import java.util.regex.Pattern;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.core.Tool;
import com.harness.core.ToolCategory;
import com.harness.core.ToolContext;
import com.harness.core.ValidationResult;
import com.harness.types.ToolResult;

/**
 * Content search tool.
 *
 * Searches file contents using regular expressions.
 */
public class GrepTool implements Tool {

    private static final Logger logger = LoggerFactory.getLogger(GrepTool.class);

    public static final String NAME = "grep";

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public String description() {
        return "Search file contents using regular expressions";
    }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "pattern", Map.of(
                    "type", "string",
                    "description", "Regular expression pattern"
                ),
                "path", Map.of(
                    "type", "string",
                    "description", "Search directory or file"
                ),
                "glob", Map.of(
                    "type", "string",
                    "description", "File filter pattern (e.g., *.java)"
                ),
                "ignore_case", Map.of(
                    "type", "boolean",
                    "description", "Ignore case",
                    "default", false
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
            String patternStr = (String) args.get("pattern");
            String basePath = args.containsKey("path") && args.get("path") != null
                ? (String) args.get("path")
                : context.workingDirectory();
            String glob = args.containsKey("glob") ? (String) args.get("glob") : null;
            boolean ignoreCase = args.containsKey("ignore_case") && Boolean.TRUE.equals(args.get("ignore_case"));

            try {
                Pattern regex = ignoreCase
                    ? Pattern.compile(patternStr, Pattern.CASE_INSENSITIVE)
                    : Pattern.compile(patternStr);

                Path rootPath = Path.of(basePath);
                if (!Files.exists(rootPath)) {
                    return ToolResult.failure("", "Path does not exist: " + basePath, NAME);
                }

                List<String> results = new ArrayList<>();
                PathMatcher globMatcher = glob != null
                    ? FileSystems.getDefault().getPathMatcher("glob:" + glob)
                    : null;

                Files.walkFileTree(rootPath, new SimpleFileVisitor<Path>() {
                    @Override
                    public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) {
                        // Check glob filter
                        if (globMatcher != null && !globMatcher.matches(file.getFileName())) {
                            return FileVisitResult.CONTINUE;
                        }

                        try {
                            List<String> lines = Files.readAllLines(file);
                            for (int i = 0; i < lines.size(); i++) {
                                if (regex.matcher(lines.get(i)).find()) {
                                    results.add(String.format("%s:%d:%s",
                                        file, i + 1, lines.get(i)));
                                }
                            }
                        } catch (IOException e) {
                            // Skip unreadable files
                        }

                        return FileVisitResult.CONTINUE;
                    }

                    @Override
                    public FileVisitResult visitFileFailed(Path file, IOException exc) {
                        return FileVisitResult.CONTINUE;
                    }
                });

                String result = String.join("\n", results);
                if (result.isEmpty()) {
                    result = "No matches found for pattern: " + patternStr;
                }

                logger.info("Found {} matches for {}", results.size(), patternStr);
                return ToolResult.success("", result, NAME);

            } catch (Exception e) {
                logger.error("Grep search failed: {}", e.getMessage());
                return ToolResult.failure("", "Search failed: " + e.getMessage(), NAME);
            }
        });
    }
}