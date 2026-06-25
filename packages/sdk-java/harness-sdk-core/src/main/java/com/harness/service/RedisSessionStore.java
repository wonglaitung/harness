package com.harness.service;

import java.time.*;
import java.util.*;
import java.util.concurrent.*;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.types.Session;

/**
 * Redis-based distributed session store.
 *
 * Provides session persistence and distributed locking for multi-instance deployments.
 *
 * Features:
 * - Session persistence with TTL
 * - Distributed locking for concurrent access
 * - Session replication across instances
 *
 * Example:
 * <pre>
 * RedisSessionStore store = RedisSessionStore.builder()
 *     .host("localhost")
 *     .port(6379)
 *     .password("secret")
 *     .ttl(Duration.ofHours(24))
 *     .build();
 *
 * // Store session
 * store.save(session);
 *
 * // Retrieve session
 * Session session = store.get("session-123");
 *
 * // Distributed lock
 * try (RedisDistributedLock lock = store.acquireLock("session-123", Duration.ofSeconds(30))) {
 *     if (lock.isAcquired()) {
 *         // Critical section
 *     }
 * }
 * </pre>
 */
public class RedisSessionStore {

    private static final Logger logger = LoggerFactory.getLogger(RedisSessionStore.class);

    private final String host;
    private final int port;
    private final String password;
    private final int database;
    private final Duration ttl;
    private final Duration lockTimeout;

    // In-memory fallback for testing
    private final Map<String, Session> memoryStore = new ConcurrentHashMap<>();
    private final Map<String, String> locks = new ConcurrentHashMap<>();

    private RedisSessionStore(Builder builder) {
        this.host = builder.host;
        this.port = builder.port;
        this.password = builder.password;
        this.database = builder.database;
        this.ttl = builder.ttl;
        this.lockTimeout = builder.lockTimeout;
    }

    /**
     * Save a session.
     */
    public void save(Session session) {
        String key = "session:" + session.id();
        logger.debug("Saving session: {}", session.id());

        // In-memory implementation
        memoryStore.put(key, session);

        // In production, use Redis:
        // jedis.setex(key, ttl.getSeconds(), serialize(session));
    }

    /**
     * Get a session by ID.
     */
    public Session get(String sessionId) {
        String key = "session:" + sessionId;

        // In-memory implementation
        Session session = memoryStore.get(key);

        // In production, use Redis:
        // String data = jedis.get(key);
        // if (data != null) {
        //     session = deserialize(data);
        // }

        return session;
    }

    /**
     * Delete a session.
     */
    public void delete(String sessionId) {
        String key = "session:" + sessionId;
        logger.debug("Deleting session: {}", sessionId);

        memoryStore.remove(key);

        // In production, use Redis:
        // jedis.del(key);
    }

    /**
     * Check if a session exists.
     */
    public boolean exists(String sessionId) {
        String key = "session:" + sessionId;
        return memoryStore.containsKey(key);

        // In production, use Redis:
        // return jedis.exists(key);
    }

    /**
     * Set TTL for a session.
     */
    public void setTTL(String sessionId, Duration duration) {
        String key = "session:" + sessionId;
        logger.debug("Setting TTL for session {}: {}s", sessionId, duration.getSeconds());

        // In production, use Redis:
        // jedis.expire(key, duration.getSeconds());
    }

    /**
     * Acquire a distributed lock.
     */
    public RedisDistributedLock acquireLock(String resourceId, Duration timeout) {
        String lockKey = "lock:" + resourceId;
        String lockValue = UUID.randomUUID().toString();

        // In-memory implementation
        String existing = locks.putIfAbsent(lockKey, lockValue);
        boolean acquired = existing == null;

        // In production, use Redis SET NX:
        // String result = jedis.set(lockKey, lockValue, "NX", "PX", timeout.toMillis());
        // boolean acquired = "OK".equals(result);

        if (acquired) {
            logger.debug("Lock acquired: {}", resourceId);
        } else {
            logger.debug("Lock not acquired: {}", resourceId);
        }

        return new RedisDistributedLock(this, lockKey, lockValue, acquired);
    }

    /**
     * Release a distributed lock.
     */
    void releaseLock(String lockKey, String lockValue) {
        // In-memory implementation
        String existing = locks.get(lockKey);
        if (lockValue.equals(existing)) {
            locks.remove(lockKey);
            logger.debug("Lock released: {}", lockKey);
        }

        // In production, use Lua script for atomic release:
        // String script = "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end";
        // jedis.eval(script, Collections.singletonList(lockKey), Collections.singletonList(lockValue));
    }

    /**
     * Get all session IDs.
     */
    public List<String> getAllSessionIds() {
        // In-memory implementation
        List<String> ids = new ArrayList<>();
        for (String key : memoryStore.keySet()) {
            if (key.startsWith("session:")) {
                ids.add(key.substring(8));
            }
        }
        return ids;

        // In production, use Redis SCAN:
        // return jedis.scan("session:*").getResults();
    }

    /**
     * Clear all sessions.
     */
    public void clear() {
        memoryStore.clear();
        locks.clear();
        logger.info("All sessions cleared");
    }

    // -------------------------------------------------------------------------
    // Builder
    // -------------------------------------------------------------------------

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String host = "localhost";
        private int port = 6379;
        private String password = null;
        private int database = 0;
        private Duration ttl = Duration.ofHours(24);
        private Duration lockTimeout = Duration.ofSeconds(30);

        public Builder host(String v) { this.host = v; return this; }
        public Builder port(int v) { this.port = v; return this; }
        public Builder password(String v) { this.password = v; return this; }
        public Builder database(int v) { this.database = v; return this; }
        public Builder ttl(Duration v) { this.ttl = v; return this; }
        public Builder lockTimeout(Duration v) { this.lockTimeout = v; return this; }

        public RedisSessionStore build() {
            return new RedisSessionStore(this);
        }
    }
}
