package com.harness.core.hooks;

/**
 * Result of user confirmation for dangerous operations.
 *
 * When a ConfirmationHook intercepts a dangerous tool call,
 * it asks the user for confirmation and returns this result.
 *
 * @param confirmed Whether the user approved the operation
 * @param trustSession Whether to trust this command for the entire session
 * @param trustKey The key to use for caching trust decisions (e.g., "bash:ls", "write")
 */
public record ConfirmationResult(
    boolean confirmed,
    boolean trustSession,
    String trustKey
) {

    /**
     * Create a simple confirmed result.
     */
    public static ConfirmationResult approved() {
        return new ConfirmationResult(true, false, null);
    }

    /**
     * Create a confirmed result with session trust.
     */
    public static ConfirmationResult approvedForSession(String trustKey) {
        return new ConfirmationResult(true, true, trustKey);
    }

    /**
     * Create a rejected result.
     */
    public static ConfirmationResult rejected() {
        return new ConfirmationResult(false, false, null);
    }

    /**
     * Create a builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private boolean confirmed = false;
        private boolean trustSession = false;
        private String trustKey = null;

        public Builder confirmed(boolean confirmed) {
            this.confirmed = confirmed;
            return this;
        }

        public Builder trustSession(boolean trustSession) {
            this.trustSession = trustSession;
            return this;
        }

        public Builder trustKey(String trustKey) {
            this.trustKey = trustKey;
            return this;
        }

        public ConfirmationResult build() {
            return new ConfirmationResult(confirmed, trustSession, trustKey);
        }
    }
}
