package com.harness.tools;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Base64;
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
 * File reading tool.
 *
 * Reads file contents, supports text and image files.
 */
public class ReadTool implements Tool {

    private static final Logger logger = LoggerFactory.getLogger(ReadTool.class);

    public static final String NAME = "read";

    private static final int DEFAULT_LIMIT = 2000;

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public String description() {
        return "Read file contents. Supports text files and image files.";
    }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "file_path", Map.of(
                    "type", "string",
                    "description", "Absolute path to the file to read"
                ),
                "offset", Map.of(
                    "type", "integer",
                    "description", "Starting line number (optional)",
                    "default", 0
                ),
                "limit", Map.of(
                    "type", "integer",
                    "description", "Number of lines to read (optional)",
                    "default", DEFAULT_LIMIT
                )
            ),
            "required", List.of("file_path")
        );
    }

    @Override
    public ToolCategory category() {
        return ToolCategory.FILE_SYSTEM;
    }

    @Override
    public ValidationResult validate(Map<String, Object> args) {
        if (!args.containsKey("file_path")) {
            return ValidationResult.invalid("file_path is required");
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
            int offset = args.containsKey("offset") ? ((Number) args.get("offset")).intValue() : 0;
            int limit = args.containsKey("limit") ? ((Number) args.get("limit")).intValue() : DEFAULT_LIMIT;

            try {
                Path path = Path.of(filePath);

                if (!Files.exists(path)) {
                    return ToolResult.failure("", "File does not exist: " + filePath, NAME);
                }

                // Check for image file
                String contentType = probeContentType(path);
                if (contentType != null && contentType.startsWith("image/")) {
                    return readImage(path);
                }

                // Read text file
                List<String> lines = Files.readAllLines(path);
                int endLine = Math.min(offset + limit, lines.size());

                StringBuilder sb = new StringBuilder();
                for (int i = offset; i < endLine; i++) {
                    sb.append(String.format("%6d\t%s%n", i + 1, lines.get(i)));
                }

                if (endLine < lines.size()) {
                    sb.append(String.format("\n... %d lines omitted ...", lines.size() - endLine));
                }

                return ToolResult.success("", sb.toString(), NAME);

            } catch (IOException e) {
                logger.error("Failed to read file {}: {}", filePath, e.getMessage());
                return ToolResult.failure("", "Failed to read file: " + e.getMessage(), NAME);
            }
        });
    }

    /**
     * Probe content type for file.
     */
    private String probeContentType(Path path) {
        try {
            return Files.probeContentType(path);
        } catch (IOException e) {
            // Fallback to extension
            String name = path.getFileName().toString().toLowerCase();
            if (name.endsWith(".png")) return "image/png";
            if (name.endsWith(".jpg") || name.endsWith(".jpeg")) return "image/jpeg";
            if (name.endsWith(".gif")) return "image/gif";
            return null;
        }
    }

    /**
     * Read image file as base64.
     */
    private ToolResult readImage(Path path) throws IOException {
        byte[] bytes = Files.readAllBytes(path);
        String base64 = Base64.getEncoder().encodeToString(bytes);
        String contentType = probeContentType(path);
        return ToolResult.success("", "data:" + contentType + ";base64," + base64, NAME, Map.of("is_image", true));
    }
}