package com.harness.security;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class ResultSanitizerTest {

    @Test
    void testSanitizeApiKey() {
        ResultSanitizer sanitizer = new ResultSanitizer();

        String input = "api_key: sk-123456789012345678901234567890";
        String result = sanitizer.sanitize(input);

        assertTrue(result.contains("[REDACTED]"));
        assertFalse(result.contains("sk-123456789012345678901234567890"));
    }

    @Test
    void testSanitizeEmail() {
        ResultSanitizer sanitizer = new ResultSanitizer();

        String input = "Contact: user@example.com";
        String result = sanitizer.sanitize(input);

        assertTrue(result.contains("[EMAIL REDACTED]"));
        assertFalse(result.contains("user@example.com"));
    }

    @Test
    void testSanitizeCreditCard() {
        ResultSanitizer sanitizer = new ResultSanitizer();

        String input = "Card: 1234-5678-9012-3456";
        String result = sanitizer.sanitize(input);

        assertTrue(result.contains("[CARD REDACTED]"));
    }

    @Test
    void testSanitizeDisabled() {
        ResultSanitizer sanitizer = new ResultSanitizer(
            new java.util.ArrayList<>(), 100000, false
        );

        String input = "api_key: sk-123456789012345678901234567890";
        String result = sanitizer.sanitize(input);

        assertEquals(input, result);
    }

    @Test
    void testGetRedactionReport() {
        ResultSanitizer sanitizer = new ResultSanitizer();

        String input = "Email: test@example.com and api_key: sk-abc123";
        ResultSanitizer.RedactionReport report = sanitizer.getRedactionReport(input);

        assertTrue(report.totalRedactions() > 0);
    }

    @Test
    void testSanitizeOutput() {
        String result = ResultSanitizer.sanitizeOutput("Token: abc123def456ghi789jkl012mno345");
        // Static method should work
        assertNotNull(result);
    }
}