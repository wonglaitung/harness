package com.harness.types;

import java.util.ArrayList;
import java.util.List;

/**
 * Result from agent loop execution.
 */
public record LoopResult(
    LoopState status,
    Session session,
    List<Message> messages,
    String finalResponse,
    int iterations,
    String error,
    TokenUsage tokenUsage
) {

    /**
     * Check if loop completed successfully.
     */
    public boolean isSuccess() {
        return status == LoopState.COMPLETED;
    }

    /**
     * Get the final response content.
     */
    public String content() {
        return finalResponse != null ? finalResponse : "";
    }

    /**
     * Check if result has error.
     */
    public boolean hasError() {
        return status == LoopState.ERROR || error != null;
    }

    /**
     * Check if loop was interrupted.
     */
    public boolean isInterrupted() {
        return status == LoopState.INTERRUPTED;
    }

    // Factory methods

    /**
     * Create a completed result.
     */
    public static LoopResult completed(Session session, String response, int iterations, TokenUsage usage) {
        return new LoopResult(
            LoopState.COMPLETED,
            session,
            new ArrayList<>(session.messages()),
            response,
            iterations,
            null,
            usage
        );
    }

    /**
     * Create an interrupted result.
     */
    public static LoopResult interrupted(Session session, int iterations) {
        return new LoopResult(
            LoopState.INTERRUPTED,
            session,
            new ArrayList<>(session.messages()),
            null,
            iterations,
            null,
            session.tokenUsage()
        );
    }

    /**
     * Create an error result.
     */
    public static LoopResult error(Session session, int iterations, String error) {
        return new LoopResult(
            LoopState.ERROR,
            session,
            new ArrayList<>(session.messages()),
            null,
            iterations,
            error,
            session.tokenUsage()
        );
    }

    /**
     * Create a max iterations reached result.
     */
    public static LoopResult maxIterations(Session session, int iterations) {
        return new LoopResult(
            LoopState.MAX_ITERATIONS,
            session,
            new ArrayList<>(session.messages()),
            null,
            iterations,
            "Max iterations reached: " + iterations,
            session.tokenUsage()
        );
    }

    /**
     * Create a stuck result.
     */
    public static LoopResult stuck(Session session, int iterations, String reason) {
        return new LoopResult(
            LoopState.STUCK,
            session,
            new ArrayList<>(session.messages()),
            null,
            iterations,
            "Agent stuck: " + reason,
            session.tokenUsage()
        );
    }

    /**
     * Builder for LoopResult.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private LoopState status = LoopState.IDLE;
        private Session session;
        private List<Message> messages = new ArrayList<>();
        private String finalResponse;
        private int iterations;
        private String error;
        private TokenUsage tokenUsage = new TokenUsage();

        public Builder status(LoopState status) {
            this.status = status;
            return this;
        }

        public Builder session(Session session) {
            this.session = session;
            return this;
        }

        public Builder messages(List<Message> messages) {
            this.messages = messages;
            return this;
        }

        public Builder finalResponse(String finalResponse) {
            this.finalResponse = finalResponse;
            return this;
        }

        public Builder iterations(int iterations) {
            this.iterations = iterations;
            return this;
        }

        public Builder error(String error) {
            this.error = error;
            return this;
        }

        public Builder tokenUsage(TokenUsage tokenUsage) {
            this.tokenUsage = tokenUsage;
            return this;
        }

        public LoopResult build() {
            return new LoopResult(status, session, messages, finalResponse, iterations, error, tokenUsage);
        }
    }
}