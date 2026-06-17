package com.harness.security;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Validator for file-related inputs.
 *
 * Validates file paths and content.
 */
public class FileInputValidator {

    private static final Logger logger = LoggerFactory.getLogger(FileInputValidator.class);

    /**
     * Default dangerous file extensions.
     */
    public static final Set<String> DANGEROUS_EXTENSIONS = Set.of(
        ".exe", ".bat", ".cmd", ".sh", ".ps1", ".vbs", ".js", ".jar"
    );

    /**
     * Default dangerous paths.
     */
    public static final Set<String> DANGEROUS_PATHS = Set.of(
        "/etc/passwd",
        "/etc/shadow",
        "/root/.ssh",
        "~/.ssh",
        "~/.aws",
        "~/.gnupg"
    );

    /**
     * Default maximum file size (10MB).
     */
    public static final int DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024;

    private final Set<String> allowedExtensions;
    private final Set<String> blockedExtensions;
    private final int maxFileSize;

    /**
     * Create validator with default settings.
     */
    public FileInputValidator() {
        this(null, DANGEROUS_EXTENSIONS, DEFAULT_MAX_FILE_SIZE);
    }

    /**
     * Create validator with custom settings.
     *
     * @param allowedExtensions allowed file extensions
     * @param blockedExtensions blocked file extensions
     * @param maxFileSize maximum file size
     */
    public FileInputValidator(Set<String> allowedExtensions, Set<String> blockedExtensions, int maxFileSize) {
        this.allowedExtensions = allowedExtensions;
        this.blockedExtensions = blockedExtensions;
        this.maxFileSize = maxFileSize;
    }

    /**
     * Validate file path.
     *
     * @param path file path to validate
     * @return ValidationResult
     */
    public ValidationResult validatePath(String path) {
        List<String> errors = new ArrayList<>();
        List<String> warnings = new ArrayList<>();

        // Expand path
        String expanded = expandPath(path);

        // Check dangerous paths
        for (String dangerous : DANGEROUS_PATHS) {
            String expandedDangerous = expandPath(dangerous);
            if (expanded.contains(expandedDangerous)) {
                errors.add("Access to sensitive path denied: " + dangerous);
            }
        }

        // Check extension
        String ext = getExtension(path);
        if (!ext.isEmpty()) {
            if (blockedExtensions != null && blockedExtensions.contains(ext)) {
                errors.add("File extension not allowed: " + ext);
            }

            if (allowedExtensions != null && !allowedExtensions.contains(ext)) {
                errors.add("File extension not in allowed list: " + ext);
            }
        }

        if (!errors.isEmpty()) {
            logger.warn("Path validation failed for {}: {}", path, errors);
            return ValidationResult.invalid(errors, expanded);
        }

        return ValidationResult.valid(expanded);
    }

    /**
     * Validate file content.
     *
     * @param content file content to validate
     * @return ValidationResult
     */
    public ValidationResult validateContent(String content) {
        return validateContent(content.getBytes());
    }

    /**
     * Validate file content.
     *
     * @param content file content bytes to validate
     * @return ValidationResult
     */
    public ValidationResult validateContent(byte[] content) {
        List<String> errors = new ArrayList<>();
        List<String> warnings = new ArrayList<>();

        // Size check
        if (content.length > maxFileSize) {
            errors.add("File size (" + content.length + ") exceeds maximum (" + maxFileSize + ")");
        }

        String sanitizedText = new String(content);

        if (!errors.isEmpty()) {
            logger.warn("Content validation failed: {}", errors);
            return ValidationResult.invalid(errors, sanitizedText);
        }

        return ValidationResult.valid(sanitizedText);
    }

    /**
     * Expand path (handle ~ and environment variables).
     */
    private String expandPath(String path) {
        if (path.startsWith("~")) {
            String home = System.getProperty("user.home");
            return home + path.substring(1);
        }
        return path;
    }

    /**
     * Get file extension.
     */
    private String getExtension(String path) {
        int dotIndex = path.lastIndexOf('.');
        if (dotIndex > 0 && dotIndex < path.length() - 1) {
            return path.substring(dotIndex).toLowerCase();
        }
        return "";
    }
}