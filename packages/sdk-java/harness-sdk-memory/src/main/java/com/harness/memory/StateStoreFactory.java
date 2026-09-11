package com.harness.memory;

import java.nio.file.Path;
import java.util.function.Predicate;

/**
 * Factory for creating SharedStateStore instances with different backends.
 *
 * <p>Provides a unified entry point for creating state stores, mirroring
 * the Python SDK's {@code create_state_store()} factory.</p>
 *
 * <h3>Usage</h3>
 * <pre>{@code
 * // In-memory (default)
 * SharedStateStore memStore = StateStoreFactory.create();
 *
 * // File-backed (SQLite)
 * SharedStateStore fileStore = StateStoreFactory.create(
 *     StateStoreFactory.Backend.FILE,
 *     Path.of(".harness/state.db"));
 *
 * // With verifiers
 * SharedStateStore secureStore = StateStoreFactory.create(
 *     StateStoreFactory.Backend.MEMORY,
 *     true,  // readVerifierRaise
 *     item -> authorizedWriters.contains(item.writerId()),
 *     item -> authorizedReaders.contains(item.sourceAgent()));
 * }</pre>
 */
public class StateStoreFactory {

    /**
     * Supported backend types.
     */
    public enum Backend {
        /** In-memory backend (single-process, development). */
        MEMORY,
        /** SQLite file backend (multi-process, development/small deployments). */
        FILE
    }

    /**
     * Create a SharedStateStore with the default in-memory backend.
     *
     * @return new SharedStateStore
     */
    public static StateStore create() {
        return new SharedStateStore();
    }

    /**
     * Create a SharedStateStore with the specified backend.
     *
     * @param backend backend type
     * @param dbPath  database path (required for FILE backend, ignored for MEMORY)
     * @return new store instance
     */
    public static StateStore create(Backend backend, java.nio.file.Path dbPath) {
        return switch (backend) {
            case MEMORY -> new SharedStateStore();
            case FILE -> new FileStateStore(dbPath);
        };
    }

    /**
     * Create a SharedStateStore with full configuration.
     *
     * @param backend           backend type
     * @param dbPath            database path (required for FILE, ignored for MEMORY)
     * @param readVerifierRaise if true, forged reads throw SecurityException
     * @param writeVerifier     optional predicate for authoritative write approval
     * @param readVerifier      optional predicate for read authorization check
     * @return new store instance
     */
    public static StateStore create(
            Backend backend,
            java.nio.file.Path dbPath,
            boolean readVerifierRaise,
            Predicate<BlackboardItem> writeVerifier,
            Predicate<BlackboardItem> readVerifier) {
        return switch (backend) {
            case MEMORY -> new SharedStateStore(readVerifierRaise, writeVerifier, readVerifier);
            case FILE -> new FileStateStore(dbPath, readVerifierRaise, writeVerifier, readVerifier);
        };
    }

    /**
     * Create a SharedStateStore with read verifier raise only.
     *
     * @param backend           backend type
     * @param dbPath            database path (required for FILE, ignored for MEMORY)
     * @param readVerifierRaise if true, forged reads throw SecurityException
     * @return new store instance
     */
    public static StateStore create(Backend backend, java.nio.file.Path dbPath, boolean readVerifierRaise) {
        return switch (backend) {
            case MEMORY -> new SharedStateStore(readVerifierRaise);
            case FILE -> new FileStateStore(dbPath, readVerifierRaise, null, null);
        };
    }
}
