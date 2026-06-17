/**
 * Security module for Harness SDK Java.
 *
 * Provides comprehensive security features for safe agent operations.
 *
 * Input Validation:
 * - {@link InputValidator}: Validates input length and checks for injection patterns
 * - {@link PromptInjectionDetector}: Detects common injection patterns in user input
 * - {@link FileInputValidator}: Validates file paths and content
 * - {@link ValidationResult}: Result of input validation
 *
 * Sandbox Execution:
 * - {@link SandboxExecutor}: Full sandbox executor with permission checking
 * - {@link LightweightSandbox}: Lightweight sandbox with command pattern blocking
 * - {@link SandboxConfig}: Sandbox configuration
 * - {@link SandboxResult}: Result of sandbox execution
 *
 * Audit Logging:
 * - {@link AuditLogger}: Records all operations to JSON Lines files
 * - {@link AuditLogEntry}: Single audit log entry
 *
 * Output Sanitization:
 * - {@link ResultSanitizer}: Removes sensitive information from tool outputs
 * - {@link SanitizationRule}: Rule for pattern detection and replacement
 */
package com.harness.security;