package com.harness.security;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Audit log entry.
 *
 * Records a single operation or event.
 */
public record AuditLogEntry(
    @JsonProperty("timestamp") Instant timestamp,
    @JsonProperty("session_id") String sessionId,
    @JsonProperty("event_type") String eventType,
    @JsonProperty("action") String action,
    @JsonProperty("resource") String resource,
    @JsonProperty("arguments") Map<String, Object> arguments,
    @JsonProperty("result") String result,
    @JsonProperty("details") Map<String, Object> details
) {

    private static final Set<String> SENSITIVE_KEYS = Set.of(
        "password", "token", "secret", "key", "credential", "api_key"
    );

    /**
     * Create entry for current time.
     */
    public static AuditLogEntry now(String sessionId, String eventType, String action,
                                    String resource, Map<String, Object> arguments,
                                    String result, Map<String, Object> details) {
        return new AuditLogEntry(
            Instant.now(),
            sessionId,
            eventType,
            action,
            resource,
            sanitizeArguments(arguments),
            result,
            details != null ? details : Map.of()
        );
    }

    /**
     * Create entry for tool call.
     */
    public static AuditLogEntry toolCall(String sessionId, String toolName,
                                         Map<String, Object> arguments, String result) {
        String resource = arguments.containsKey("path")
            ? (String) arguments.get("path")
            : arguments.containsKey("file")
                ? (String) arguments.get("file")
                : "";

        return now(
            sessionId,
            "tool_call",
            toolName,
            resource,
            arguments,
            result,
            Map.of()
        );
    }

    /**
     * Create entry for file access.
     */
    public static AuditLogEntry fileAccess(String sessionId, String action,
                                           String path, String result) {
        return now(
            sessionId,
            "file_access",
            action,
            path,
            Map.of(),
            result,
            Map.of()
        );
    }

    /**
     * Create entry for command execution.
     */
    public static AuditLogEntry command(String sessionId, String command, String result) {
        return now(
            sessionId,
            "command",
            "execute",
            command,
            Map.of(),
            result,
            Map.of()
        );
    }

    /**
     * Sanitize sensitive arguments.
     */
    private static Map<String, Object> sanitizeArguments(Map<String, Object> args) {
        if (args == null) {
            return Map.of();
        }

        Map<String, Object> sanitized = new HashMap<>();
        for (Map.Entry<String, Object> entry : args.entrySet()) {
            String key = entry.getKey();
            if (SENSITIVE_KEYS.stream().anyMatch(s -> key.toLowerCase().contains(s))) {
                sanitized.put(key, "***REDACTED***");
            } else {
                sanitized.put(key, entry.getValue());
            }
        }
        return sanitized;
    }

    /**
     * Get formatted timestamp.
     */
    public String formattedTimestamp() {
        LocalDateTime local = LocalDateTime.ofInstant(timestamp, ZoneId.systemDefault());
        return local.format(DateTimeFormatter.ISO_LOCAL_DATE_TIME);
    }
}