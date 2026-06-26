package com.harness.memory;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.harness.types.Message;
import com.harness.types.Session;
import com.harness.types.TokenUsage;

/**
 * File-based session storage.
 *
 * Stores each session as a JSON file in a directory.
 *
 * Example:
 * <pre>
 * SessionStore store = new FileSessionStore(Path.of(".harness/sessions"));
 * store.save(session);
 *
 * Optional&lt;Session&gt; loaded = store.load("session-123");
 * </pre>
 */
public class FileSessionStore implements SessionStore {

    private static final Logger logger = LoggerFactory.getLogger(FileSessionStore.class);

    private final Path storageDir;
    private final ObjectMapper objectMapper;

    /**
     * Create a file session store.
     *
     * @param storageDir Directory to store session files
     */
    public FileSessionStore(Path storageDir) {
        this.storageDir = storageDir;
        this.objectMapper = new ObjectMapper();
        this.objectMapper.registerModule(new JavaTimeModule());

        try {
            Files.createDirectories(storageDir);
        } catch (IOException e) {
            logger.warn("Failed to create storage directory: {}", e.getMessage());
        }
    }

    /**
     * Create a file session store with default directory.
     */
    public FileSessionStore() {
        this(Path.of(System.getProperty("user.home"), ".harness", "sessions"));
    }

    /**
     * Create a file session store with string path.
     *
     * @param storageDirPath Path to storage directory
     */
    public FileSessionStore(String storageDirPath) {
        this(Path.of(storageDirPath));
    }

    private Path sessionPath(String sessionId) {
        return storageDir.resolve(sessionId + ".json");
    }

    @Override
    public void save(Session session) {
        Path path = sessionPath(session.id());

        try {
            SessionData data = new SessionData(
                session.id(),
                session.messages().stream()
                    .map(MessageData::fromMessage)
                    .collect(Collectors.toList()),
                session.createdAt(),
                session.updatedAt(),
                session.metadata(),
                new TokenUsageData(session.tokenUsage()),
                session.systemPrompt()
            );

            objectMapper.writerWithDefaultPrettyPrinter().writeValue(path.toFile(), data);
            logger.debug("Saved session to: {}", path);

        } catch (IOException e) {
            logger.error("Failed to save session {}: {}", session.id(), e.getMessage());
            throw new RuntimeException("Failed to save session", e);
        }
    }

    @Override
    public Optional<Session> load(String sessionId) {
        Path path = sessionPath(sessionId);

        if (!Files.exists(path)) {
            return Optional.empty();
        }

        try {
            SessionData data = objectMapper.readValue(path.toFile(), SessionData.class);

            List<Message> messages = data.messages().stream()
                .map(MessageData::toMessage)
                .collect(Collectors.toList());

            TokenUsage tokenUsage = data.tokenUsage() != null
                ? data.tokenUsage().toTokenUsage()
                : new TokenUsage();

            Session session = Session.builder()
                .id(data.id())
                .messages(messages)
                .createdAt(data.createdAt())
                .updatedAt(data.updatedAt())
                .metadata(data.metadata() != null ? data.metadata() : java.util.Map.of())
                .tokenUsage(tokenUsage)
                .systemPrompt(data.systemPrompt())
                .build();

            return Optional.of(session);

        } catch (IOException e) {
            logger.error("Failed to load session {}: {}", sessionId, e.getMessage());
            return Optional.empty();
        }
    }

    @Override
    public void delete(String sessionId) {
        Path path = sessionPath(sessionId);

        try {
            if (Files.exists(path)) {
                Files.delete(path);
                logger.debug("Deleted session: {}", sessionId);
            }
        } catch (IOException e) {
            logger.error("Failed to delete session {}: {}", sessionId, e.getMessage());
        }
    }

    @Override
    public List<String> listSessions() {
        try (Stream<Path> files = Files.list(storageDir)) {
            return files
                .filter(p -> p.toString().endsWith(".json"))
                .map(p -> p.getFileName().toString().replace(".json", ""))
                .sorted()
                .collect(Collectors.toList());
        } catch (IOException e) {
            logger.error("Failed to list sessions: {}", e.getMessage());
            return List.of();
        }
    }

    @Override
    public void deleteAll() {
        for (String sessionId : listSessions()) {
            delete(sessionId);
        }
    }

    // -------------------------------------------------------------------------
    // Data classes for JSON serialization
    // -------------------------------------------------------------------------

    /**
     * Session data for JSON serialization.
     */
    public record SessionData(
        String id,
        List<MessageData> messages,
        Instant createdAt,
        Instant updatedAt,
        java.util.Map<String, Object> metadata,
        TokenUsageData tokenUsage,
        String systemPrompt
    ) {}

    /**
     * Message data for JSON serialization.
     */
    public record MessageData(
        String role,
        String content,
        Instant timestamp,
        java.util.Map<String, Object> metadata
    ) {
        public static MessageData fromMessage(Message msg) {
            return new MessageData(
                msg.role(),
                msg.contentAsString(),
                msg.timestamp(),
                msg.metadata()
            );
        }

        public Message toMessage() {
            return new Message(
                role,
                content,
                timestamp,
                metadata != null ? metadata : java.util.Map.of()
            );
        }
    }

    /**
     * Token usage data for JSON serialization.
     */
    public record TokenUsageData(
        int inputTokens,
        int outputTokens,
        int cacheReadTokens,
        int cacheWriteTokens,
        int toolCalls
    ) {
        public TokenUsageData(TokenUsage usage) {
            this(
                usage.inputTokens(),
                usage.outputTokens(),
                usage.cacheReadTokens(),
                usage.cacheWriteTokens(),
                usage.toolCalls()
            );
        }

        public TokenUsage toTokenUsage() {
            return new TokenUsage(inputTokens, outputTokens, cacheReadTokens, cacheWriteTokens, toolCalls);
        }
    }
}
