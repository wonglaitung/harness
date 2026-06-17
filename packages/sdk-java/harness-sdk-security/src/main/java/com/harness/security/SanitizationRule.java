package com.harness.security;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Sanitization rule.
 *
 * Defines a pattern to detect and replacement to apply.
 */
public record SanitizationRule(
    String name,
    Pattern pattern,
    String replacement,
    String description
) {

    /**
     * Create a rule.
     */
    public static SanitizationRule of(String name, String pattern, String replacement, String description) {
        return new SanitizationRule(name, Pattern.compile(pattern, Pattern.CASE_INSENSITIVE), replacement, description);
    }
}