package com.harness.memory;

import java.sql.*;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.harness.types.Message;
import com.harness.types.Session;
import com.harness.types.TokenUsage;

/**
 * SQLite-based session storage.
 *
 * Provides persistent storage with better performance for large sessions.
 *
 * Note: Requires SQLite JDBC driver to be on the classpath.
 * Add dependency: org.xerial:sqlite-jdbc
 *
 * Example:
 * <pre>
 * SessionStore store = new SQLiteSessionStore(Path.of(".harness/harness.db"));
 * store.save(session);
 *
 * Optional&lt;Session&gt; loaded = store.load("session-123");
 * </pre>
 */
public class SQLiteSessionStore implements SessionStore {

    private static final Logger logger = LoggerFactory.getLogger(SQLiteSessionStore.class);

    private final String dbUrl;
    private final ObjectMapper objectMapper;
    private volatile boolean initialized = false;

    /**
     * Create a SQLite session store.
     *
     * @param dbPath Path to the SQLite database file
     */
    public SQLiteSessionStore(java.nio.file.Path dbPath) {
        this.dbUrl = "jdbc:sqlite:" + dbPath.toString();
        this.objectMapper = new ObjectMapper();
        this.objectMapper.registerModule(new JavaTimeModule());

        // Create parent directory if needed
        try {
            java.nio.file.Files.createDirectories(dbPath.getParent());
        } catch (Exception e) {
            // Ignore if directory exists
        }

        initDb();
    }

    /**
     * Create a SQLite session store with default path.
     */
    public SQLiteSessionStore() {
        this(java.nio.file.Path.of(System.getProperty("user.home"), ".harness", "harness.db"));
    }

    /**
     * Create a SQLite session store with string path.
     *
     * @param dbPath Path to the database file
     */
    public SQLiteSessionStore(String dbPath) {
        this(java.nio.file.Path.of(dbPath));
    }

    /**
     * Initialize database schema.
     */
    private synchronized void initDb() {
        if (initialized) {
            return;
        }

        try (Connection conn = DriverManager.getConnection(dbUrl)) {
            // Create sessions table
            conn.createStatement().execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    created_at TEXT,
                    updated_at TEXT,
                    user_id TEXT,
                    working_directory TEXT,
                    summary TEXT,
                    metadata TEXT,
                    system_prompt TEXT
                )
            """);

            // Create messages table
            conn.createStatement().execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TEXT,
                    tool_call_id TEXT,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """);

            // Create index
            conn.createStatement().execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session_id
                ON messages(session_id)
            """);

            initialized = true;
            logger.info("SQLite session store initialized: {}", dbUrl);

        } catch (SQLException e) {
            logger.error("Failed to initialize database: {}", e.getMessage());
            throw new RuntimeException("Failed to initialize database", e);
        }
    }

    @Override
    public void save(Session session) {
        try (Connection conn = DriverManager.getConnection(dbUrl)) {
            conn.setAutoCommit(false);

            try {
                // Insert or replace session
                PreparedStatement sessionStmt = conn.prepareStatement("""
                    INSERT OR REPLACE INTO sessions
                    (id, created_at, updated_at, user_id, working_directory, summary, metadata, system_prompt)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """);

                sessionStmt.setString(1, session.id());
                sessionStmt.setString(2, session.createdAt().toString());
                sessionStmt.setString(3, session.updatedAt().toString());
                sessionStmt.setString(4, getStringMetadata(session.metadata(), "user_id"));
                sessionStmt.setString(5, getStringMetadata(session.metadata(), "working_directory"));
                sessionStmt.setString(6, getStringMetadata(session.metadata(), "summary"));
                sessionStmt.setString(7, objectMapper.writeValueAsString(session.metadata()));
                sessionStmt.setString(8, session.systemPrompt());
                sessionStmt.execute();

                // Delete old messages
                PreparedStatement deleteStmt = conn.prepareStatement(
                    "DELETE FROM messages WHERE session_id = ?"
                );
                deleteStmt.setString(1, session.id());
                deleteStmt.execute();

                // Insert messages
                PreparedStatement msgStmt = conn.prepareStatement("""
                    INSERT INTO messages
                    (session_id, role, content, timestamp, tool_call_id, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """);

                for (Message msg : session.messages()) {
                    msgStmt.setString(1, session.id());
                    msgStmt.setString(2, msg.role());
                    msgStmt.setString(3, msg.contentAsString());
                    msgStmt.setString(4, msg.timestamp().toString());
                    msgStmt.setString(5, getStringMetadata(msg.metadata(), "tool_call_id"));
                    msgStmt.setString(6, objectMapper.writeValueAsString(msg.metadata()));
                    msgStmt.addBatch();
                }
                msgStmt.executeBatch();

                conn.commit();
                logger.debug("Saved session: {}", session.id());

            } catch (Exception e) {
                conn.rollback();
                throw e;
            }

        } catch (SQLException e) {
            logger.error("Failed to save session {}: {}", session.id(), e.getMessage());
            throw new RuntimeException("Failed to save session", e);
        } catch (JsonProcessingException e) {
            logger.error("Failed to serialize session metadata: {}", e.getMessage());
            throw new RuntimeException("Failed to serialize session", e);
        }
    }

    @Override
    public Optional<Session> load(String sessionId) {
        try (Connection conn = DriverManager.getConnection(dbUrl)) {
            // Load session
            PreparedStatement sessionStmt = conn.prepareStatement(
                "SELECT * FROM sessions WHERE id = ?"
            );
            sessionStmt.setString(1, sessionId);
            ResultSet rs = sessionStmt.executeQuery();

            if (!rs.next()) {
                return Optional.empty();
            }

            String id = rs.getString("id");
            Instant createdAt = Instant.parse(rs.getString("created_at"));
            Instant updatedAt = Instant.parse(rs.getString("updated_at"));
            String systemPrompt = rs.getString("system_prompt");
            @SuppressWarnings("unchecked")
            Map<String, Object> metadata = parseMetadata(rs.getString("metadata"));

            // Load messages
            List<Message> messages = new ArrayList<>();
            PreparedStatement msgStmt = conn.prepareStatement(
                "SELECT role, content, timestamp, metadata FROM messages WHERE session_id = ? ORDER BY id"
            );
            msgStmt.setString(1, sessionId);
            ResultSet msgRs = msgStmt.executeQuery();

            while (msgRs.next()) {
                @SuppressWarnings("unchecked")
                Map<String, Object> msgMetadata = parseMetadata(msgRs.getString("metadata"));
                messages.add(new Message(
                    msgRs.getString("role"),
                    msgRs.getString("content"),
                    Instant.parse(msgRs.getString("timestamp")),
                    msgMetadata
                ));
            }

            Session session = Session.builder()
                .id(id)
                .messages(messages)
                .createdAt(createdAt)
                .updatedAt(updatedAt)
                .metadata(metadata)
                .tokenUsage(new TokenUsage())
                .systemPrompt(systemPrompt)
                .build();

            return Optional.of(session);

        } catch (SQLException e) {
            logger.error("Failed to load session {}: {}", sessionId, e.getMessage());
            return Optional.empty();
        }
    }

    @Override
    public void delete(String sessionId) {
        try (Connection conn = DriverManager.getConnection(dbUrl)) {
            PreparedStatement deleteMsgs = conn.prepareStatement(
                "DELETE FROM messages WHERE session_id = ?"
            );
            deleteMsgs.setString(1, sessionId);
            deleteMsgs.execute();

            PreparedStatement deleteSession = conn.prepareStatement(
                "DELETE FROM sessions WHERE id = ?"
            );
            deleteSession.setString(1, sessionId);
            deleteSession.execute();

            logger.debug("Deleted session: {}", sessionId);

        } catch (SQLException e) {
            logger.error("Failed to delete session {}: {}", sessionId, e.getMessage());
        }
    }

    @Override
    public List<String> listSessions() {
        List<String> sessions = new ArrayList<>();

        try (Connection conn = DriverManager.getConnection(dbUrl)) {
            ResultSet rs = conn.createStatement().executeQuery(
                "SELECT id FROM sessions ORDER BY updated_at DESC"
            );

            while (rs.next()) {
                sessions.add(rs.getString("id"));
            }

        } catch (SQLException e) {
            logger.error("Failed to list sessions: {}", e.getMessage());
        }

        return sessions;
    }

    @Override
    public void deleteAll() {
        try (Connection conn = DriverManager.getConnection(dbUrl)) {
            conn.createStatement().execute("DELETE FROM messages");
            conn.createStatement().execute("DELETE FROM sessions");
            logger.debug("Deleted all sessions");
        } catch (SQLException e) {
            logger.error("Failed to delete all sessions: {}", e.getMessage());
        }
    }

    private String getStringMetadata(Map<String, Object> metadata, String key) {
        if (metadata == null) return null;
        Object value = metadata.get(key);
        return value != null ? value.toString() : null;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> parseMetadata(String json) {
        if (json == null || json.isEmpty()) {
            return Map.of();
        }
        try {
            return objectMapper.readValue(json, Map.class);
        } catch (Exception e) {
            return Map.of();
        }
    }

    /**
     * Close the store (for cleanup).
     */
    public void close() {
        // SQLite JDBC handles connection pooling internally
        // No explicit cleanup needed
    }
}
