package com.harness.tools;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
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
 * File writing tool.
 *
 * Writes content to a file. Overwrites existing files.
 */
public class WriteTool implements Tool {

    private static final Logger logger = LoggerFactory.getLogger(WriteTool.class);

    public static final String NAME = "write";

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public String description() {
        return "Write content to a file. Will overwrite existing files.";
    }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "file_path", Map.of(
                    "type", "string",
                    "description", "Absolute path to the file to write"
                ),
                "content", Map.of(
                    "type", "string",
                    "description", "Content to write to the file"
                )
            ),
            "required", List.of("file_path", "content")
        );
    }

    @Override
    public ToolCategory category() {
        return ToolCategory.FILE_SYSTEM;
    }

    @Override
    public boolean isDangerous() {
        return true; // Writing files is dangerous
    }

    @Override
    public ValidationResult validate(Map<String, Object> args) {
        if (!args.containsKey("file_path")) {
            return ValidationResult.invalid("file_path is required");
        }
        if (!args.containsKey("content")) {
            return ValidationResult.invalid("content is required");
        }

        String filePath = (String) args.get("file_path");
        if (filePath == null || filePath.isBlank()) {
            return ValidationResult.invalid("file_path cannot be empty");
        }

        Path path = Path.of(filePath);
        if (!path.isAbsolute()) {
            return ValidationResult.invalid("Must use absolute path");
        }

        return ValidationResult.valid();
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context) {
        return CompletableFuture.supplyAsync(() -> {
            String filePath = (String) args.get("file_path");
            String content = (String) args.get("content");

            try {
                Path path = Path.of(filePath);

                // Create parent directories if needed
                Path parent = path.getParent();
                if (parent != null && !Files.exists(parent)) {
                    Files.createDirectories(parent);
                }

                // Write file
                Files.writeString(path, content);

                logger.info("Wrote file: {}", filePath);
                return ToolResult.success("", "File written: " + filePath, NAME);

            } catch (IOException e) {
                logger.error("Failed to write file {}: {}", filePath, e.getMessage());
                return ToolResult.failure("", "Failed to write file: " + e.getMessage(), NAME);
            }
        });
    }
}