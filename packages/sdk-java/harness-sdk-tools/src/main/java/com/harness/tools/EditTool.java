package com.harness.tools;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.core.Tool;
import com.harness.core.ToolCategory;
import com.harness.core.ToolContext;
import com.harness.core.ValidationResult;
import com.harness.types.ToolResult;

/**
 * File editing tool.
 *
 * Replaces specific text in a file.
 */
public class EditTool implements Tool {

    private static final Logger logger = LoggerFactory.getLogger(EditTool.class);

    public static final String NAME = "edit";

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public String description() {
        return "Edit a file by replacing specific text content.";
    }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "file_path", Map.of(
                    "type", "string",
                    "description", "Absolute path to the file to edit"
                ),
                "old_string", Map.of(
                    "type", "string",
                    "description", "Text to replace (must be unique match)"
                ),
                "new_string", Map.of(
                    "type", "string",
                    "description", "Replacement text"
                ),
                "replace_all", Map.of(
                    "type", "boolean",
                    "description", "Replace all occurrences",
                    "default", false
                )
            ),
            "required", List.of("file_path", "old_string", "new_string")
        );
    }

    @Override
    public ToolCategory category() {
        return ToolCategory.FILE_SYSTEM;
    }

    @Override
    public boolean isDangerous() {
        return true;
    }

    @Override
    public ValidationResult validate(Map<String, Object> args) {
        if (!args.containsKey("file_path") || !args.containsKey("old_string") || !args.containsKey("new_string")) {
            return ValidationResult.invalid("file_path, old_string, and new_string are required");
        }

        String filePath = (String) args.get("file_path");
        if (filePath == null || filePath.isBlank()) {
            return ValidationResult.invalid("file_path cannot be empty");
        }

        String oldString = (String) args.get("old_string");
        if (oldString == null || oldString.isEmpty()) {
            return ValidationResult.invalid("old_string cannot be empty");
        }

        return ValidationResult.valid();
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context) {
        return CompletableFuture.supplyAsync(() -> {
            String filePath = (String) args.get("file_path");
            String oldString = (String) args.get("old_string");
            String newString = (String) args.get("new_string");
            boolean replaceAll = args.containsKey("replace_all") && Boolean.TRUE.equals(args.get("replace_all"));

            try {
                Path path = Path.of(filePath);

                if (!Files.exists(path)) {
                    return ToolResult.failure("", "File does not exist: " + filePath, NAME);
                }

                String content = Files.readString(path);

                // Check for matches
                int count = countMatches(content, oldString);
                if (count == 0) {
                    return ToolResult.failure("", "Text not found: " + oldString, NAME);
                }
                if (count > 1 && !replaceAll) {
                    return ToolResult.failure("",
                        String.format("Found %d matches. Use more specific text or set replace_all=true", count), NAME);
                }

                // Perform replacement
                String newContent;
                if (replaceAll) {
                    newContent = content.replace(oldString, newString);
                } else {
                    newContent = content.replaceFirst(Pattern.quote(oldString), Matcher.quoteReplacement(newString));
                }

                Files.writeString(path, newContent);

                int replacedCount = replaceAll ? count : 1;
                logger.info("Replaced {} occurrence(s) in {}", replacedCount, filePath);
                return ToolResult.success("", String.format("Replaced %d occurrence(s)", replacedCount), NAME);

            } catch (IOException e) {
                logger.error("Failed to edit file {}: {}", filePath, e.getMessage());
                return ToolResult.failure("", "Failed to edit file: " + e.getMessage(), NAME);
            }
        });
    }

    /**
     * Count occurrences of a string in text.
     */
    private int countMatches(String text, String pattern) {
        int count = 0;
        int index = 0;
        while ((index = text.indexOf(pattern, index)) != -1) {
            count++;
            index += pattern.length();
        }
        return count;
    }
}