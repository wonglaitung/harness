package com.harness.memory;

import java.sql.*;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.locks.ReentrantReadWriteLock;
import java.util.function.Predicate;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;

/**
 * SQLite-backed shared-state store for multi-process deployments.
 *
 * <p>Persistent implementation using SQLite with rollback journal (not WAL)
 * for cross-process safety. Thread-safe via ReentrantReadWriteLock.</p>
 *
 * <h3>Usage</h3>
 * <pre>{@code
 * FileStateStore store = new FileStateStore(Path.of(".harness/state.db"));
 * BlackboardItem item = BlackboardItem.create("decision", content, "planner", 0.9f, "harness");
 * store.put(item);
 * // CAS write
 * store.writeIfVersion(item.getId(), newContent, 0);
 * store.close();
 * }</pre>
 *
 * <p>Note: Requires SQLite JDBC driver on classpath: org.xerial:sqlite-jdbc</p>
 */
public class FileStateStore implements StateStore {

    private static final Logger logger = LoggerFactory.getLogger(FileStateStore.class);

    private final String dbUrl;
    private final ObjectMapper objectMapper;
    private final ReentrantReadWriteLock lock = new ReentrantReadWriteLock();
    private volatile Connection connection;

    private final boolean readVerifierRaise;
    private final Predicate<BlackboardItem> writeVerifier;
    private final Predicate<BlackboardItem> readVerifier;

    /**
     * Create a file-backed state store.
     *
     * @param dbPath path to SQLite database file
     */
    public FileStateStore(java.nio.file.Path dbPath) {
        this(dbPath, false, null, null);
    }

    /**
     * Create a file-backed state store with full configuration.
     *
     * @param dbPath             path to SQLite database file
     * @param readVerifierRaise  if true, forged reads throw SecurityException
     * @param writeVerifier      optional predicate for authoritative write approval
     * @param readVerifier       optional predicate for read authorization check
     */
    public FileStateStore(
            java.nio.file.Path dbPath,
            boolean readVerifierRaise,
            Predicate<BlackboardItem> writeVerifier,
            Predicate<BlackboardItem> readVerifier) {
        this.dbUrl = "jdbc:sqlite:" + dbPath.toString();
        this.readVerifierRaise = readVerifierRaise;
        this.writeVerifier = writeVerifier;
        this.readVerifier = readVerifier;

        this.objectMapper = new ObjectMapper();
        this.objectMapper.registerModule(new JavaTimeModule());

        // Create parent directory if needed
        try {
            java.nio.file.Files.createDirectories(dbPath.getParent());
        } catch (Exception e) {
            // Ignore if directory exists
        }

        initDatabase();
    }

    private void initDatabase() {
        try {
            connection = DriverManager.getConnection(dbUrl);
            // Use rollback journal (NOT WAL) for cross-process safety
            connection.setAutoCommit(false);
            try (Statement stmt = connection.createStatement()) {
                stmt.execute("PRAGMA busy_timeout=5000");
                stmt.execute(
                    "CREATE TABLE IF NOT EXISTS blackboard (" +
                    "  id TEXT PRIMARY KEY," +
                    "  payload TEXT NOT NULL" +
                    ")"
                );
            }
            connection.commit();
        } catch (SQLException e) {
            throw new RuntimeException("Failed to initialize SQLite database", e);
        }
    }

    private String serialize(BlackboardItem item) throws JsonProcessingException {
        return objectMapper.writeValueAsString(item);
    }

    private BlackboardItem deserialize(String json) throws JsonProcessingException {
        return objectMapper.readValue(json, BlackboardItem.class);
    }

    /**
     * Put an item into the store.
     *
     * @param item the blackboard item
     */
    public void put(BlackboardItem item) {
        Objects.requireNonNull(item, "BlackboardItem must not be null");

        // Authoritative writes require write-verifier approval
        if ("authoritative".equals(item.type()) && writeVerifier != null) {
            if (!writeVerifier.test(item)) {
                throw new IllegalArgumentException(
                    "Write verifier rejected authoritative item: " + item.getId());
            }
        }

        lock.writeLock().lock();
        try {
            String json = serialize(item);
            try (PreparedStatement ps = connection.prepareStatement(
                    "INSERT OR REPLACE INTO blackboard (id, payload) VALUES (?, ?)")) {
                ps.setString(1, item.getId());
                ps.setString(2, json);
                ps.executeUpdate();
            }
            connection.commit();
            logger.debug("Put item {}: type={}, source={}", item.getId(), item.type(), item.sourceAgent());
        } catch (Exception e) {
            rollbackQuietly();
            throw new RuntimeException("Failed to put item: " + item.getId(), e);
        } finally {
            lock.writeLock().unlock();
        }
    }

    /**
     * Get an item by ID.
     *
     * @param id item ID
     * @return the item, or null if not found
     * @throws SecurityException if readVerifierRaise=true and readVerifier rejects the item
     */
    public BlackboardItem get(String id) {
        lock.readLock().lock();
        try {
            BlackboardItem item = loadItem(id);
            if (item == null) {
                return null;
            }

            // Filter expired items
            if (item.isExpired()) {
                lock.readLock().unlock();
                lock.writeLock().lock();
                try {
                    deleteItem(id);
                    connection.commit();
                } finally {
                    lock.writeLock().unlock();
                    lock.readLock().lock();
                }
                return null;
            }

            // Read verification (M6-H)
            if (readVerifier != null && !readVerifier.test(item)) {
                if (readVerifierRaise) {
                    throw new SecurityException(
                        "Forged/forbidden authoritative item rejected by readVerifier (H): " + id);
                }
                logger.warn("Read verifier rejected item {} (silently dropping)", id);
                return null;
            }

            return item;
        } catch (SecurityException e) {
            throw e;
        } catch (Exception e) {
            throw new RuntimeException("Failed to get item: " + id, e);
        } finally {
            if (lock.isReadLockedByCurrentThread()) {
                lock.readLock().unlock();
            }
        }
    }

    private BlackboardItem loadItem(String id) throws SQLException, JsonProcessingException {
        try (PreparedStatement ps = connection.prepareStatement(
                "SELECT payload FROM blackboard WHERE id = ?")) {
            ps.setString(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                if (rs.next()) {
                    return deserialize(rs.getString("payload"));
                }
            }
        }
        return null;
    }

    private void deleteItem(String id) throws SQLException {
        try (PreparedStatement ps = connection.prepareStatement(
                "DELETE FROM blackboard WHERE id = ?")) {
            ps.setString(1, id);
            ps.executeUpdate();
        }
    }

    /**
     * List all active (non-expired) items.
     *
     * @return list of items
     */
    public List<BlackboardItem> listItems() {
        lock.readLock().lock();
        try {
            List<BlackboardItem> result = new ArrayList<>();
            try (Statement stmt = connection.createStatement();
                 ResultSet rs = stmt.executeQuery("SELECT payload FROM blackboard")) {
                while (rs.next()) {
                    BlackboardItem item = deserialize(rs.getString("payload"));
                    if (item.isExpired()) {
                        continue;
                    }

                    // Read verification (M6-H)
                    if (readVerifier != null && !readVerifier.test(item)) {
                        if (readVerifierRaise) {
                            throw new SecurityException(
                                "Forged/forbidden authoritative item rejected by readVerifier (H): " + item.getId());
                        }
                        logger.warn("Read verifier rejected item {} (silently dropping)", item.getId());
                        continue;
                    }

                    result.add(item);
                }
            }
            return List.copyOf(result);
        } catch (SecurityException e) {
            throw e;
        } catch (Exception e) {
            throw new RuntimeException("Failed to list items", e);
        } finally {
            lock.readLock().unlock();
        }
    }

    /**
     * CAS (Compare-And-Swap) write: update content only if the base version matches.
     *
     * @param id          item ID
     * @param newContent  new content to write
     * @param baseVersion expected current version
     * @return true if write succeeded, false if version mismatch
     * @throws IllegalArgumentException if item not found
     */
    public boolean writeIfVersion(String id, Map<String, Object> newContent, int baseVersion) {
        lock.writeLock().lock();
        try {
            BlackboardItem current = loadItem(id);
            if (current == null) {
                throw new IllegalArgumentException("Item not found: " + id);
            }

            if (current.baseVersion() != baseVersion) {
                logger.warn("CAS version mismatch for item {}: expected={}, actual={}",
                    id, baseVersion, current.baseVersion());
                return false;
            }

            // Authoritative writes require write-verifier approval
            if ("authoritative".equals(current.type()) && writeVerifier != null) {
                BlackboardItem candidate = new BlackboardItem(
                    current.id(), current.type(), newContent, current.sourceAgent(),
                    current.confidence(), current.baseVersion() + 1, current.ttlSeconds(),
                    current.status(), current.writerId(), current.effectiveWriter(),
                    current.createdAt());
                if (!writeVerifier.test(candidate)) {
                    throw new IllegalArgumentException(
                        "Write verifier rejected authoritative CAS write: " + id);
                }
            }

            BlackboardItem updated = new BlackboardItem(
                current.id(), current.type(), newContent, current.sourceAgent(),
                current.confidence(), current.baseVersion() + 1, current.ttlSeconds(),
                current.status(), current.writerId(), current.effectiveWriter(),
                current.createdAt());

            String json = serialize(updated);
            try (PreparedStatement ps = connection.prepareStatement(
                    "UPDATE blackboard SET payload = ? WHERE id = ?")) {
                ps.setString(1, json);
                ps.setString(2, id);
                ps.executeUpdate();
            }
            connection.commit();

            logger.debug("CAS write succeeded for item {}: v{} → v{}", id, baseVersion, baseVersion + 1);
            return true;
        } catch (IllegalArgumentException e) {
            rollbackQuietly();
            throw e;
        } catch (Exception e) {
            rollbackQuietly();
            throw new RuntimeException("Failed CAS write for item: " + id, e);
        } finally {
            lock.writeLock().unlock();
        }
    }

    /**
     * Get the current version of an item.
     *
     * @param id item ID
     * @return current base version, or -1 if not found
     */
    public int getVersion(String id) {
        lock.readLock().lock();
        try {
            BlackboardItem item = loadItem(id);
            return item != null ? item.baseVersion() : -1;
        } catch (Exception e) {
            throw new RuntimeException("Failed to get version for item: " + id, e);
        } finally {
            lock.readLock().unlock();
        }
    }

    /**
     * Get conflicting authoritative items (same type, different content).
     *
     * @return list of conflict sets
     */
    public List<ConflictSet> getConflicts() {
        List<BlackboardItem> items = listItems();
        java.util.Map<String, ConflictSet> conflicts = new java.util.LinkedHashMap<>();

        for (BlackboardItem item : items) {
            if (!"authoritative".equals(item.type())) {
                continue;
            }
            for (BlackboardItem other : items) {
                if (other.getId().equals(item.getId()) || !other.type().equals(item.type())) {
                    continue;
                }
                if ("authoritative".equals(other.type()) &&
                    !other.content().equals(item.content())) {
                    ConflictSet cs = conflicts.computeIfAbsent(
                        item.type(), k -> new ConflictSet(k, new ArrayList<>(), Instant.now()));
                    if (!cs.itemIds().contains(item.getId())) {
                        cs.itemIds().add(item.getId());
                    }
                    if (!cs.itemIds().contains(other.getId())) {
                        cs.itemIds().add(other.getId());
                    }
                }
            }
        }
        return new ArrayList<>(conflicts.values());
    }

    /**
     * Get the number of active items.
     */
    public int size() {
        lock.readLock().lock();
        try (Statement stmt = connection.createStatement();
             ResultSet rs = stmt.executeQuery("SELECT COUNT(*) FROM blackboard")) {
            if (rs.next()) {
                return rs.getInt(1);
            }
            return 0;
        } catch (Exception e) {
            throw new RuntimeException("Failed to get size", e);
        } finally {
            lock.readLock().unlock();
        }
    }

    /**
     * Close the database connection.
     */
    public void close() {
        lock.writeLock().lock();
        try {
            if (connection != null && !connection.isClosed()) {
                connection.close();
            }
        } catch (SQLException e) {
            logger.warn("Error closing database connection", e);
        } finally {
            lock.writeLock().unlock();
        }
    }

    private void rollbackQuietly() {
        try {
            if (connection != null && !connection.isClosed()) {
                connection.rollback();
            }
        } catch (SQLException e) {
            logger.warn("Rollback failed", e);
        }
    }
}
