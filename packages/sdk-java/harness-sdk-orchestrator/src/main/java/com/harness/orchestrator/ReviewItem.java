package com.harness.orchestrator;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * A review item submitted to the {@link ReviewQueue} (M6-G).
 *
 * <p>Represents content that has been flagged by a deterministic gate
 * and requires human review before it can proceed.</p>
 */
public class ReviewItem {

    private final String id;
    private final List<Map<String, Object>> gateFindings;
    private final String content;
    private final String source;
    private final Map<String, String> metadata;

    /**
     * Create a review item.
     *
     * @param gateFindings list of gate finding descriptions
     * @param content      the content under review
     * @param source       origin of the review request
     * @param metadata     optional key-value metadata
     */
    public ReviewItem(
            List<Map<String, Object>> gateFindings,
            String content,
            String source,
            Map<String, String> metadata) {
        this.id = UUID.randomUUID().toString();
        this.gateFindings = gateFindings != null ? List.copyOf(gateFindings) : List.of();
        this.content = content;
        this.source = source;
        this.metadata = metadata != null ? Map.copyOf(metadata) : Map.of();
    }

    /**
     * Create a review item with minimal fields.
     */
    public static ReviewItem of(String content, String source, List<Map<String, Object>> findings) {
        return new ReviewItem(findings, content, source, Map.of());
    }

    public String getId() { return id; }
    public List<Map<String, Object>> getGateFindings() { return gateFindings; }
    public String getContent() { return content; }
    public String getSource() { return source; }
    public Map<String, String> getMetadata() { return metadata; }
}
