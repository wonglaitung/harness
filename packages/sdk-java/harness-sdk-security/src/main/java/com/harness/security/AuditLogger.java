package com.harness.security;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * Audit logger.
 *
 * Records all operations to JSON Lines files for later analysis.
 */
public class AuditLogger {

    private static final Logger logger = LoggerFactory.getLogger(AuditLogger.class);
    private static final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * Default log directory.
     */
    public static final String DEFAULT_LOG_DIR = "~/.harness/audit";

    /**
     * Default maximum file size (100MB).
     */
    public static final int DEFAULT_MAX_FILE_SIZE = 100 * 1024 * 1024;

    /**
     * Default retention days.
     */
    public static final int DEFAULT_RETENTION_DAYS = 30;

    private final Path logDir;
    private final int maxFileSize;
    private final int retentionDays;
    private final boolean enabled;

    /**
     * Create logger with default settings.
     */
    public AuditLogger() {
        this(DEFAULT_LOG_DIR, DEFAULT_MAX_FILE_SIZE, DEFAULT_RETENTION_DAYS, true);
    }

    /**
     * Create logger with custom settings.
     *
     * @param logDir directory for log files
     * @param maxFileSize maximum log file size
     * @param retentionDays days to retain logs
     * @param enabled whether logging is enabled
     */
    public AuditLogger(String logDir, int maxFileSize, int retentionDays, boolean enabled) {
        this.maxFileSize = maxFileSize;
        this.retentionDays = retentionDays;
        this.enabled = enabled;

        // Expand path
        String expandedDir = logDir;
        if (logDir.startsWith("~")) {
            expandedDir = System.getProperty("user.home") + logDir.substring(1);
        }
        this.logDir = Path.of(expandedDir);

        if (enabled) {
            try {
                Files.createDirectories(this.logDir);
            } catch (IOException e) {
                logger.warn("Failed to create audit log directory: {}", e.getMessage());
            }
        }
    }

    /**
     * Log an entry.
     *
     * @param entry entry to log
     */
    public void log(AuditLogEntry entry) {
        if (!enabled) {
            return;
        }

        try {
            Path logFile = getLogFile();
            String json = objectMapper.writeValueAsString(entry);
            Files.writeString(logFile, json + "\n",
                Files.exists(logFile) ? java.nio.file.StandardOpenOption.APPEND : java.nio.file.StandardOpenOption.CREATE);
        } catch (IOException e) {
            logger.error("Failed to write audit log: {}", e.getMessage());
        }
    }

    /**
     * Log a tool call.
     */
    public void logToolCall(String sessionId, String toolName,
                            Map<String, Object> arguments, String result) {
        log(AuditLogEntry.toolCall(sessionId, toolName, arguments, result));
    }

    /**
     * Log a file access.
     */
    public void logFileAccess(String sessionId, String action, String path, String result) {
        log(AuditLogEntry.fileAccess(sessionId, action, path, result));
    }

    /**
     * Log a command execution.
     */
    public void logCommand(String sessionId, String command, String result) {
        log(AuditLogEntry.command(sessionId, command, result));
    }

    /**
     * Get current log file.
     */
    private Path getLogFile() throws IOException {
        String today = LocalDate.now().format(DateTimeFormatter.ISO_LOCAL_DATE);
        Path logFile = logDir.resolve("audit-" + today + ".log");

        // Check file size
        if (Files.exists(logFile) && Files.size(logFile) > maxFileSize) {
            // Create new file with index
            int index = 1;
            while (true) {
                Path newFile = logDir.resolve("audit-" + today + "-" + index + ".log");
                if (!Files.exists(newFile)) {
                    logFile = newFile;
                    break;
                }
                index++;
            }
        }

        return logFile;
    }

    /**
     * Query audit logs.
     *
     * @param sessionId filter by session ID
     * @param eventType filter by event type
     * @param action filter by action
     * @param startTime filter by start time
     * @param endTime filter by end time
     * @param limit maximum results
     * @return list of matching entries
     */
    public List<AuditLogEntry> query(String sessionId, String eventType, String action,
                                     Instant startTime, Instant endTime, int limit) {
        if (!Files.exists(logDir)) {
            return List.of();
        }

        List<AuditLogEntry> results = new ArrayList<>();

        try {
            for (Path logFile : Files.list(logDir).toList()) {
                if (!logFile.getFileName().toString().startsWith("audit-") ||
                    !logFile.getFileName().toString().endsWith(".log")) {
                    continue;
                }

                try {
                    for (String line : Files.readAllLines(logFile)) {
                        if (line.isBlank()) {
                            continue;
                        }

                        try {
                            AuditLogEntry entry = objectMapper.readValue(line, AuditLogEntry.class);

                            // Apply filters
                            if (sessionId != null && !entry.sessionId().equals(sessionId)) {
                                continue;
                            }
                            if (eventType != null && !entry.eventType().equals(eventType)) {
                                continue;
                            }
                            if (action != null && !entry.action().equals(action)) {
                                continue;
                            }
                            if (startTime != null && entry.timestamp().isBefore(startTime)) {
                                continue;
                            }
                            if (endTime != null && entry.timestamp().isAfter(endTime)) {
                                continue;
                            }

                            results.add(entry);

                            if (results.size() >= limit) {
                                break;
                            }
                        } catch (Exception e) {
                            // Skip malformed entries
                        }
                    }

                    if (results.size() >= limit) {
                        break;
                    }
                } catch (IOException e) {
                    // Skip unreadable files
                }
            }
        } catch (IOException e) {
            logger.error("Failed to query audit logs: {}", e.getMessage());
        }

        // Sort by timestamp descending
        results.sort(Comparator.comparing(AuditLogEntry::timestamp).reversed());
        return results;
    }

    /**
     * Clean up old logs.
     *
     * @return number of files removed
     */
    public int cleanupOldLogs() {
        LocalDate cutoff = LocalDate.now().minusDays(retentionDays);
        int removed = 0;

        if (!Files.exists(logDir)) {
            return 0;
        }

        try {
            for (Path logFile : Files.list(logDir).toList()) {
                String fileName = logFile.getFileName().toString();
                if (!fileName.startsWith("audit-") || !fileName.endsWith(".log")) {
                    continue;
                }

                try {
                    // Extract date from filename
                    String dateStr = fileName.substring(6, 16); // audit-YYYY-MM-DD
                    LocalDate fileDate = LocalDate.parse(dateStr);

                    if (fileDate.isBefore(cutoff)) {
                        Files.delete(logFile);
                        removed++;
                    }
                } catch (Exception e) {
                    // Skip files with invalid names
                }
            }
        } catch (IOException e) {
            logger.error("Failed to cleanup audit logs: {}", e.getMessage());
        }

        return removed;
    }

    /**
     * Get audit log statistics.
     */
    public AuditStats getStats() {
        if (!Files.exists(logDir)) {
            return new AuditStats(0, 0, 0, logDir.toString());
        }

        try {
            List<Path> files = Files.list(logDir)
                .filter(p -> p.getFileName().toString().startsWith("audit-"))
                .filter(p -> p.getFileName().toString().endsWith(".log"))
                .toList();

            long totalSize = 0;
            for (Path file : files) {
                totalSize += Files.size(file);
            }

            return new AuditStats(
                files.size(),
                totalSize,
                totalSize / (1024.0 * 1024.0),
                logDir.toString()
            );
        } catch (IOException e) {
            return new AuditStats(0, 0, 0, logDir.toString());
        }
    }

    /**
     * Audit log statistics.
     */
    public record AuditStats(
        int totalFiles,
        long totalSize,
        double totalSizeMb,
        String logDir
    ) {
    }
}