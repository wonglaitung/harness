package com.harness.service;

/**
 * Distributed lock acquired from Redis.
 *
 * Implements AutoCloseable for try-with-resources pattern.
 *
 * Example:
 * <pre>
 * try (RedisDistributedLock lock = store.acquireLock("resource-123", Duration.ofSeconds(30))) {
 *     if (lock.isAcquired()) {
 *         // Critical section - safe to modify shared resource
 *     } else {
 *         // Lock not acquired - resource is in use
 *     }
 * } // Lock automatically released
 * </pre>
 */
public class RedisDistributedLock implements AutoCloseable {

    private final RedisSessionStore store;
    private final String lockKey;
    private final String lockValue;
    private final boolean acquired;
    private volatile boolean released = false;

    RedisDistributedLock(RedisSessionStore store, String lockKey, String lockValue, boolean acquired) {
        this.store = store;
        this.lockKey = lockKey;
        this.lockValue = lockValue;
        this.acquired = acquired;
    }

    /**
     * Check if the lock was successfully acquired.
     */
    public boolean isAcquired() {
        return acquired && !released;
    }

    /**
     * Check if the lock has been released.
     */
    public boolean isReleased() {
        return released;
    }

    /**
     * Release the lock.
     */
    public void release() {
        if (!released && acquired) {
            store.releaseLock(lockKey, lockValue);
            released = true;
        }
    }

    @Override
    public void close() {
        release();
    }
}
