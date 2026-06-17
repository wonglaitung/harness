package com.harness.types;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * A conversation session.
 */
public record Session(
    String id,
    List<Message> messages,
    Instant createdAt,
    Instant updatedAt,
    Map<String, Object> metadata,
    TokenUsage tokenUsage,
    String systemPrompt
) {

    public Session(String id) {
        this(id, new ArrayList<>(), Instant.now(), Instant.now(), Map.of(), new TokenUsage(), null);
    }

    public static Session create() {
        return new Session(UUID.randomUUID().toString());
    }

    public static Session create(String id) {
        return new Session(id);
    }

    /**
     * Add a message to the session.
     */
    public Session addMessage(Message message) {
        List<Message> newMessages = new ArrayList<>(this.messages);
        newMessages.add(message);
        return new Session(
            this.id,
            newMessages,
            this.createdAt,
            Instant.now(),
            this.metadata,
            this.tokenUsage,
            this.systemPrompt
        );
    }

    /**
     * Clear all messages in the session.
     */
    public Session clear() {
        return new Session(
            this.id,
            new ArrayList<>(),
            this.createdAt,
            Instant.now(),
            this.metadata,
            this.tokenUsage,
            this.systemPrompt
        );
    }

    /**
     * Get the last N messages.
     */
    public List<Message> getLastNMessages(int n) {
        if (n <= 0 || messages.isEmpty()) {
            return List.of();
        }
        int start = Math.max(0, messages.size() - n);
        return messages.subList(start, messages.size());
    }

    /**
     * Update token usage.
     */
    public Session withTokenUsage(TokenUsage usage) {
        return new Session(
            this.id,
            this.messages,
            this.createdAt,
            Instant.now(),
            this.metadata,
            usage,
            this.systemPrompt
        );
    }

    /**
     * Set system prompt.
     */
    public Session withSystemPrompt(String systemPrompt) {
        return new Session(
            this.id,
            this.messages,
            this.createdAt,
            Instant.now(),
            this.metadata,
            this.tokenUsage,
            systemPrompt
        );
    }

    /**
     * Builder for Session.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String id = UUID.randomUUID().toString();
        private List<Message> messages = new ArrayList<>();
        private Instant createdAt = Instant.now();
        private Instant updatedAt = Instant.now();
        private Map<String, Object> metadata = Map.of();
        private TokenUsage tokenUsage = new TokenUsage();
        private String systemPrompt;

        public Builder id(String id) {
            this.id = id;
            return this;
        }

        public Builder messages(List<Message> messages) {
            this.messages = messages;
            return this;
        }

        public Builder addMessage(Message message) {
            this.messages.add(message);
            return this;
        }

        public Builder metadata(Map<String, Object> metadata) {
            this.metadata = metadata;
            return this;
        }

        public Builder tokenUsage(TokenUsage tokenUsage) {
            this.tokenUsage = tokenUsage;
            return this;
        }

        public Builder systemPrompt(String systemPrompt) {
            this.systemPrompt = systemPrompt;
            return this;
        }

        public Session build() {
            return new Session(id, messages, createdAt, updatedAt, metadata, tokenUsage, systemPrompt);
        }
    }
}
