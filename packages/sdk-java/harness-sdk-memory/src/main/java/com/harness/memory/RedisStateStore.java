package com.harness.memory;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.function.Predicate;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;

import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;
import redis.clients.jedis.params.ScanParams;

/**
 * Redis-backed shared-state store (production, distributed multi-agent).
 *
 * <p>Mirrors the Python SDK's {@code state/redis_store.RedisBackend}: each
 * {@link BlackboardItem} is stored as a Redis hash with a single {@code v} field
 * holding the Jackson JSON. CAS writes use an atomic Lua script (single-threaded
 * Redis guarantees no interleaving) to close the TOCTOU race in a naive
 * read-modify-write (H3: CAS must be atomic, not best-effort).</p>
 *
 * <p>Behaviour (verifier / expiry / read-authorization) is kept identical to
 * {@link FileStateStore} so the two Java backends are interchangeable.</p>
 *
 * <h3>Usage</h3>
 * <pre>{@code
 * RedisStateStore store = new RedisStateStore("localhost", 6379);
 * store.put(BlackboardItem.create("decision", content, "planner", 0.9f, "harness"));
 * store.writeIfVersion(item.id(), newContent, 0);
 * store.close();
 * }</pre>
 *
 * <p>Requires the {@code redis.clients:jedis} driver on the classpath.</p>
 */
public class RedisStateStore implements StateStore {

    private static final Logger logger = LoggerFactory.getLogger(RedisStateStore.class);

    private final JedisPool pool;
    private final int database;
    private final String prefix;
    private final ObjectMapper objectMapper;

    private final boolean readVerifierRaise;
    private final Predicate<BlackboardItem> writeVerifier;
    private final Predicate<BlackboardItem> readVerifier;

    // Atomic compare-and-set (mirrors Python _CAS_LUA): only write when the stored
    // version still equals the expected base_version; returns "OK" or "CONFLICT".
    private static final String CAS_LUA =
            "local key = KEYS[1]\n"
                    + "local expected = tonumber(ARGV[1])\n"
                    + "local new_json = ARGV[2]\n"
                    + "local raw = redis.call('HGET', key, 'v')\n"
                    + "local cur_ver = nil\n"
                    + "if raw then\n"
                    + "  local ok, cur = pcall(cjson.decode, raw)\n"
                    + "  if ok and type(cur) == 'table' then\n"
                    + "    cur_ver = tonumber(cur.version)\n"
                    + "  end\n"
                    + "end\n"
                    + "if cur_ver ~= nil and cur_ver ~= expected then\n"
                    + "  return 'CONFLICT'\n"
                    + "end\n"
                    + "redis.call('HSET', key, 'v', new_json)\n"
                    + "return 'OK'\n";

    public RedisStateStore(String host, int port) {
        this(host, port, 0, "harness:bb:", false, null, null);
    }

    public RedisStateStore(String host, int port, int database, String prefix) {
        this(host, port, database, prefix, false, null, null);
    }

    public RedisStateStore(
            String host,
            int port,
            int database,
            String prefix,
            boolean readVerifierRaise,
            Predicate<BlackboardItem> writeVerifier,
            Predicate<BlackboardItem> readVerifier) {
        this.database = database;
        this.prefix = prefix;
        this.readVerifierRaise = readVerifierRaise;
        this.writeVerifier = writeVerifier;
        this.readVerifier = readVerifier;

        this.objectMapper = new ObjectMapper();
        this.objectMapper.registerModule(new JavaTimeModule());
        this.objectMapper.configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);

        this.pool = new JedisPool(host, port);
    }

    private String key(String id) {
        return prefix + id;
    }

    private String serialize(BlackboardItem item) throws JsonProcessingException {
        return objectMapper.writeValueAsString(item);
    }

    private BlackboardItem deserialize(String json) throws JsonProcessingException {
        return objectMapper.readValue(json, BlackboardItem.class);
    }

    private interface JedisAction<T> {
        T run(Jedis j) throws Exception;
    }

    private <T> T withJedis(JedisAction<T> action) {
        try (Jedis j = pool.getResource()) {
            if (database != 0) {
                j.select(database);
            }
            try {
                return action.run(j);
            } catch (RuntimeException e) {
                throw e;
            } catch (Exception e) {
                throw new RuntimeException("Redis operation failed", e);
            }
        }
    }

    @Override
    public void put(BlackboardItem item) {
        Objects.requireNonNull(item, "BlackboardItem must not be null");

        if ("authoritative".equals(item.type()) && writeVerifier != null
                && !writeVerifier.test(item)) {
            throw new IllegalArgumentException(
                    "Write verifier rejected authoritative item: " + item.id());
        }

        String json = serializeSafe(item);
        withJedis(j -> {
            j.hset(key(item.id()), "v", json);
            return null;
        });
        logger.debug("Put item {}: type={}, source={}", item.id(), item.type(), item.sourceAgent());
    }

    @Override
    public BlackboardItem get(String id) {
        String raw = withJedis(j -> j.hget(key(id), "v"));
        if (raw == null) {
            return null;
        }
        BlackboardItem item = deserializeSafe(raw);
        if (item == null) {
            return null;
        }

        if (item.isExpired()) {
            withJedis(j -> {
                j.del(key(id));
                return null;
            });
            return null;
        }

        if (readVerifier != null && !readVerifier.test(item)) {
            if (readVerifierRaise) {
                throw new SecurityException(
                        "Forged/forbidden authoritative item rejected by readVerifier (H): " + id);
            }
            logger.warn("Read verifier rejected item {} (silently dropping)", id);
            return null;
        }
        return item;
    }

    @Override
    public List<BlackboardItem> listItems() {
        List<String> keys = scanKeys();
        List<BlackboardItem> result = new ArrayList<>();
        for (String fullKey : keys) {
            String id = fullKey.substring(prefix.length());
            BlackboardItem item = get(id);
            if (item != null) {
                result.add(item);
            }
        }
        return List.copyOf(result);
    }

    @Override
    public int size() {
        return scanKeys().size();
    }

    /**
     * CAS (Compare-And-Swap) write: update content only if the base version matches.
     *
     * @return true if write succeeded, false if version mismatch
     * @throws IllegalArgumentException if item not found
     */
    public boolean writeIfVersion(String id, Map<String, Object> newContent, int baseVersion) {
        BlackboardItem current = get(id);
        if (current == null) {
            throw new IllegalArgumentException("Item not found: " + id);
        }

        if (current.baseVersion() != baseVersion) {
            logger.warn("CAS version mismatch for item {}: expected={}, actual={}",
                    id, baseVersion, current.baseVersion());
            return false;
        }

        BlackboardItem candidate = new BlackboardItem(
                current.id(), current.type(), newContent, current.sourceAgent(),
                current.confidence(), current.baseVersion() + 1, current.ttlSeconds(),
                current.status(), current.writerId(), current.effectiveWriter(),
                current.provenance(), current.createdAt());
        if ("authoritative".equals(current.type()) && writeVerifier != null
                && !writeVerifier.test(candidate)) {
            throw new IllegalArgumentException(
                    "Write verifier rejected authoritative CAS write: " + id);
        }

        String json = serializeSafe(candidate);
        String result = withJedis(j -> (String) j.eval(CAS_LUA, 1, key(id),
                String.valueOf(baseVersion), json));
        boolean ok = "OK".equals(result);
        if (ok) {
            logger.debug("CAS write succeeded for item {}: v{} → v{}", id, baseVersion, baseVersion + 1);
        } else {
            logger.warn("CAS write conflict for item {} (version changed concurrently)", id);
        }
        return ok;
    }

    /**
     * Get the current base version of an item.
     *
     * @return current base version, or -1 if not found
     */
    public int getVersion(String id) {
        BlackboardItem item = get(id);
        return item != null ? item.baseVersion() : -1;
    }

    /**
     * Get conflicting authoritative items (same type, different content).
     */
    public List<ConflictSet> getConflicts() {
        List<BlackboardItem> items = listItems();
        Map<String, ConflictSet> conflicts = new LinkedHashMap<>();

        for (BlackboardItem item : items) {
            if (!"authoritative".equals(item.type())) {
                continue;
            }
            for (BlackboardItem other : items) {
                if (other.id().equals(item.id()) || !other.type().equals(item.type())) {
                    continue;
                }
                if ("authoritative".equals(other.type())
                        && !other.content().equals(item.content())) {
                    ConflictSet cs = conflicts.computeIfAbsent(
                            item.type(), k -> new ConflictSet(k, new ArrayList<>(), java.time.Instant.now()));
                    if (!cs.itemIds().contains(item.id())) {
                        cs.itemIds().add(item.id());
                    }
                    if (!cs.itemIds().contains(other.id())) {
                        cs.itemIds().add(other.id());
                    }
                }
            }
        }
        return new ArrayList<>(conflicts.values());
    }

    /**
     * Close the Redis connection pool.
     */
    public void close() {
        try {
            pool.close();
        } catch (Exception e) {
            logger.warn("Error closing Redis connection pool", e);
        }
    }

    private List<String> scanKeys() {
        return withJedis(j -> {
            List<String> keys = new ArrayList<>();
            String cursor = "0";
            ScanParams params = new ScanParams().match(prefix + "*").count(100);
            do {
                var sr = j.scan(cursor, params);
                keys.addAll(sr.getResult());
                cursor = sr.getCursor();
            } while (!"0".equals(cursor));
            return keys;
        });
    }

    private String serializeSafe(BlackboardItem item) {
        try {
            return serialize(item);
        } catch (JsonProcessingException e) {
            throw new RuntimeException("Failed to serialize item: " + item.id(), e);
        }
    }

    private BlackboardItem deserializeSafe(String json) {
        try {
            return deserialize(json);
        } catch (JsonProcessingException e) {
            logger.warn("Failed to deserialize blackboard item, skipping", e);
            return null;
        }
    }
}
