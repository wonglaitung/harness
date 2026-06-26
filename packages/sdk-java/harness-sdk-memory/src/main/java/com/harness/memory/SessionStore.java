package com.harness.memory;

import java.util.List;
import java.util.Optional;

import com.harness.types.Session;

/**
 * Session storage interface.
 *
 * Provides persistence for sessions across application restarts.
 *
 * Example:
 * <pre>
 * SessionStore store = new FileSessionStore();
 * store.save(session);
 *
 * Optional&lt;Session&gt; loaded = store.load("session-123");
 * if (loaded.isPresent()) {
 *     // Use session
 * }
 * </pre>
 */
public interface SessionStore {

    /**
     * Save a session.
     *
     * @param session Session to save
     */
    void save(Session session);

    /**
     * Load a session by ID.
     *
     * @param sessionId Session ID
     * @return Session if found, empty otherwise
     */
    Optional<Session> load(String sessionId);

    /**
     * Delete a session.
     *
     * @param sessionId Session ID to delete
     */
    void delete(String sessionId);

    /**
     * Check if a session exists.
     *
     * @param sessionId Session ID
     * @return True if session exists
     */
    default boolean exists(String sessionId) {
        return load(sessionId).isPresent();
    }

    /**
     * List all session IDs.
     *
     * @return List of session IDs
     */
    List<String> listSessions();

    /**
     * Delete all sessions.
     */
    void deleteAll();
}
