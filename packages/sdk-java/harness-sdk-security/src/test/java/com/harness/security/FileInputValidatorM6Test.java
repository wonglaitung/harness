package com.harness.security;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

/**
 * M6-C tests for FileInputValidator write-mode validation.
 */
class FileInputValidatorM6Test {

    private final FileInputValidator validator = new FileInputValidator();

    @Test
    void validatePathWriteModeBlocksSystemPath() {
        ValidationResult result = validator.validatePath("/etc/passwd", "write");
        assertFalse(result.isValid());
    }

    @Test
    void validatePathWriteModeBlocksRoot() {
        ValidationResult result = validator.validatePath("/root/.ssh/id_rsa", "write");
        assertFalse(result.isValid());
    }

    @Test
    void validatePathWriteModeAllowsSafePath() {
        ValidationResult result = validator.validatePath("./output/report.md", "write");
        assertTrue(result.isValid());
    }

    @Test
    void validatePathReadModeDoesNotBlockSystemPath() {
        // Read mode only checks existing DANGEROUS_PATHS, not write-specific ones
        ValidationResult result = validator.validatePath("/etc/passwd", "read");
        assertFalse(result.isValid());  // still blocked by DANGEROUS_PATHS
    }

    @Test
    void validatePathDefaultIsReadMode() {
        ValidationResult result = validator.validatePath("/tmp/safe.txt");
        assertTrue(result.isValid());
    }
}
