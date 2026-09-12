package com.harness.memory;

import java.time.Instant;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

/**
 * A single item on the multi-agent blackboard (M6-H).
 *
 * <p>Fields mirror the Python SDK's {@code BlackboardItem}.  The {@code writerId}
 * and {@code effectiveWriter} fields enable the write-verifier to distinguish
 * between direct writes and delegated/authorized writes.</p>
 *
 * @param id               unique item identifier
 * @param type             category (e.g., "decision", "observation", "proposal")
 * @param content          structured content (JSON-serializable map)
 * @param sourceAgent      agent that produced the content
 * @param confidence       confidence score [0, 1]
 * @param baseVersion      version for CAS (optimistic concurrency)
 * @param ttlSeconds       time-to-live in seconds (0 = no expiry)
 * @param status           item status ("active", "resolved", "archived")
 * @param writerId         identity of the writer
 * @param effectiveWriter  effective writer when writing on behalf of another agent
 * @param provenance       A4: mandatory for authoritative writes — a trusted source
 *                         reference (e.g. "file:report.pdf:page=3", "db:accounts:row=42")
 * @param createdAt        creation timestamp
 */
public record BlackboardItem(
    String id,
    String type,
    Map<String, Object> content,
    String sourceAgent,
    float confidence,
    int baseVersion,
    int ttlSeconds,
    String status,
    String writerId,
    String effectiveWriter,
    String provenance,
    Instant createdAt
) {

    /**
     * Create a new item with auto-generated id and current timestamp.
     */
    public static BlackboardItem create(
            String type,
            Map<String, Object> content,
            String sourceAgent,
            float confidence,
            String writerId) {
        return new BlackboardItem(
            UUID.randomUUID().toString(),
            type,
            content != null ? Map.copyOf(content) : Map.of(),
            sourceAgent,
            confidence,
            0,  // baseVersion starts at 0
            0,  // no expiry by default
            "active",
            writerId,
            null,
            null,  // provenance — optional for additive, required for authoritative
            Instant.now()
        );
    }

    /**
     * Create a new item with TTL.
     */
    public static BlackboardItem create(
            String type,
            Map<String, Object> content,
            String sourceAgent,
            float confidence,
            String writerId,
            int ttlSeconds) {
        BlackboardItem item = create(type, content, sourceAgent, confidence, writerId);
        return new BlackboardItem(
            item.id, item.type, item.content, item.sourceAgent, item.confidence,
            item.baseVersion, ttlSeconds, item.status, item.writerId,
            item.effectiveWriter, item.provenance, item.createdAt
        );
    }

    /**
     * Check if this item has expired based on TTL.
     */
    public boolean isExpired() {
        if (ttlSeconds <= 0) {
            return false;
        }
        return Instant.now().isAfter(createdAt.plusSeconds(ttlSeconds));
    }

    /**
     * Create a copy with incremented version.
     */
    public BlackboardItem withIncrementedVersion() {
        return new BlackboardItem(
            id, type, content, sourceAgent, confidence,
            baseVersion + 1, ttlSeconds, status, writerId,
            effectiveWriter, provenance, createdAt
        );
    }

    /**
     * Create a copy with a different status.
     */
    public BlackboardItem withStatus(String newStatus) {
        return new BlackboardItem(
            id, type, content, sourceAgent, confidence,
            baseVersion, ttlSeconds, newStatus, writerId,
            effectiveWriter, provenance, createdAt
        );
    }

    /**
     * A4: Create a copy with provenance set.
     */
    public BlackboardItem withProvenance(String provenance) {
        return new BlackboardItem(
            id, type, content, sourceAgent, confidence,
            baseVersion, ttlSeconds, status, writerId,
            effectiveWriter, provenance, createdAt
        );
    }
}
