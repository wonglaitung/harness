package com.harness.core;

import java.util.List;
import java.util.concurrent.TimeUnit;

import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;

import com.knuddelsgmbh.jtokkit.Encodings;
import com.knuddelsgmbh.jtokkit.api.Encoding;
import com.knuddelsgmbh.jtokkit.api.EncodingType;

/**
 * Token counter using jtokkit library.
 *
 * Uses cl100k_base encoding which is compatible with Claude and GPT-4.
 */
public class TokenCounter {

    private final Encoding encoding;
    private final Cache<String, Integer> cache;

    public TokenCounter() {
        // Claude uses cl100k_base encoding (same as GPT-4)
        this.encoding = Encodings.newDefaultEncodingRegistry()
            .getEncoding(EncodingType.CL100K_BASE);

        // Cache token counts
        this.cache = Caffeine.newBuilder()
            .maximumSize(10000)
            .expireAfterAccess(10, TimeUnit.MINUTES)
            .build();
    }

    /**
     * Count tokens in text.
     */
    public int count(String text) {
        if (text == null || text.isEmpty()) {
            return 0;
        }
        return cache.get(text, t -> encoding.encode(t).size());
    }

    /**
     * Count tokens in multiple texts.
     */
    public int countAll(List<String> texts) {
        return texts.stream()
            .mapToInt(this::count)
            .sum();
    }

    /**
     * Count tokens in a list of messages.
     */
    public int countMessages(List<Message> messages) {
        int total = 0;
        for (Message msg : messages) {
            total += count(msg.contentAsString());
            // Add overhead for role and formatting
            total += 4; // Approximate overhead per message
        }
        return total;
    }

    /**
     * Clear cache.
     */
    public void clearCache() {
        cache.invalidateAll();
    }
}