package com.harness.memory;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.harness.types.Message;
import com.harness.types.Session;
import com.harness.types.TokenUsage;

/**
 * Session manager - manages conversation sessions.
 *
 * Provides in-memory and file-based session storage.
 */
public class SessionManager {

    private static final Logger logger = LoggerFactory.getLogger(SessionManager.class);

    private final Map<String, Session> sessions;
    private final Path storageDir;
    private final ObjectMapper objectMapper;
    private final boolean persistToDisk;

    public SessionManager(Path storageDir, boolean persistToDisk) {
        this.sessions = new HashMap<>();
        this.storageDir = storageDir;
        this.persistToDisk = persistToDisk;
        this.objectMapper = new ObjectMapper();
        this.objectMapper.registerModule(new JavaTimeModule());

        if (persistToDisk) {
            try {
                Files.createDirectories(storageDir);
            } catch (IOException e) {
                logger.warn("Failed to create session directory: {}", e.getMessage());
            }
        }
    }

    public SessionManager(Path storageDir) {
        this(storageDir, true);
    }

    public SessionManager() {
        this(Path.of(System.getProperty("user.home"), ".harness", "sessions"), true);
    }

    /**
     * Create a new session.
     */
    public Session createSession() {
        Session session = Session.create();
        sessions.put(session.id(), session);
        logger.debug("Created session: {}", session.id());
        return session;
    }

    /**
     * Create a session with specific ID.
     */
    public Session createSession(String sessionId) {
        Session session = Session.create(sessionId);
        sessions.put(session.id(), session);
        logger.debug("Created session: {}", session.id());
        return session;
    }

    /**
     * Get a session by ID.
     */
    public Optional<Session> getSession(String sessionId) {
        // Check memory first
        Session session = sessions.get(sessionId);
        if (session != null) {
            return Optional.of(session);
        }

        // Try to load from disk
        if (persistToDisk) {
            session = loadFromDisk(sessionId);
            if (session != null) {
                sessions.put(sessionId, session);
                return Optional.of(session);
            }
        }

        return Optional.empty();
    }

    /**
     * Get or create a session.
     */
    public Session getOrCreateSession(String sessionId) {
        return getSession(sessionId).orElseGet(() -> createSession(sessionId));
    }

    /**
     * Save a session.
     */
    public void saveSession(Session session) {
        sessions.put(session.id(), session);

        if (persistToDisk) {
            saveToDisk(session);
        }
    }

    /**
     * Delete a session.
     */
    public void deleteSession(String sessionId) {
        sessions.remove(sessionId);

        if (persistToDisk) {
            deleteFromDisk(sessionId);
        }
    }

    /**
     * List all session IDs.
     */
    public List<String> listSessions() {
        if (persistToDisk) {
            try {
                return Files.list(storageDir)
                    .filter(p -> p.toString().endsWith(".json"))
                    .map(p -> p.getFileName().toString().replace(".json", ""))
                    .toList();
            } catch (IOException e) {
                logger.warn("Failed to list sessions: {}", e.getMessage());
            }
        }
        return List.copyOf(sessions.keySet());
    }

    /**
     * Clear all sessions.
     */
    public void clear() {
        sessions.clear();

        if (persistToDisk) {
            try {
                Files.list(storageDir)
                    .filter(p -> p.toString().endsWith(".json"))
                    .forEach(p -> {
                        try {
                            Files.delete(p);
                        } catch (IOException e) {
                            logger.warn("Failed to delete session file: {}", p);
                        }
                    });
            } catch (IOException e) {
                logger.warn("Failed to clear sessions: {}", e.getMessage());
            }
        }
    }

    // Private methods for disk persistence

    private void saveToDisk(Session session) {
        Path sessionFile = storageDir.resolve(session.id() + ".json");
        try {
            SessionData data = new SessionData(
                session.id(),
                session.messages().stream().map(this::messageToData).toList(),
                session.createdAt().toString(),
                session.updatedAt().toString(),
                session.tokenUsage().inputTokens(),
                session.tokenUsage().outputTokens()
            );
            objectMapper.writerWithDefaultPrettyPrinter().writeValue(sessionFile.toFile(), data);
        } catch (IOException e) {
            logger.error("Failed to save session {}: {}", session.id(), e.getMessage());
        }
    }

    private Session loadFromDisk(String sessionId) {
        Path sessionFile = storageDir.resolve(sessionId + ".json");
        if (!Files.exists(sessionFile)) {
            return null;
        }

        try {
            SessionData data = objectMapper.readValue(sessionFile.toFile(), SessionData.class);
            return Session.builder()
                .id(data.id())
                .messages(data.messages().stream().map(this::dataToMessage).toList())
                .tokenUsage(new TokenUsage(data.inputTokens(), data.outputTokens()))
                .createdAt(Instant.parse(data.createdAt()))
                .updatedAt(Instant.parse(data.updatedAt()))
                .build();
        } catch (IOException e) {
            logger.warn("Failed to load session {}: {}", sessionId, e.getMessage());
            return null;
        }
    }

    private void deleteFromDisk(String sessionId) {
        Path sessionFile = storageDir.resolve(sessionId + ".json");
        try {
            Files.deleteIfExists(sessionFile);
        } catch (IOException e) {
            logger.warn("Failed to delete session file: {}", sessionFile);
        }
    }

    private MessageData messageToData(Message msg) {
        return new MessageData(msg.role(), msg.contentAsString(), msg.timestamp().toString());
    }

    private Message dataToMessage(MessageData data) {
        return Message.builder()
            .role(data.role())
            .content(data.content())
            .timestamp(Instant.parse(data.timestamp()))
            .build();
    }

    // Data classes for JSON serialization

    record SessionData(
        String id,
        List<MessageData> messages,
        String createdAt,
        String updatedAt,
        int inputTokens,
        int outputTokens
    ) {}

    record MessageData(
        String role,
        String content,
        String timestamp
    ) {}
}