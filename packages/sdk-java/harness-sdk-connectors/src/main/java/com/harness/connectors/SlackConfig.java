package com.harness.connectors;

import java.util.ArrayList;
import java.util.List;

/**
 * Slack connector configuration.
 *
 * <p>Configuration for Slack App integration.</p>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * SlackConfig config = new SlackConfig.Builder()
 *     .botToken("xoxb-...")
 *     .appToken("xapp-...")  // For Socket Mode
 *     .commandPrefix("/harness")
 *     .build();
 * }</pre>
 */
public class SlackConfig {
    private final String botToken;
    private final String appToken;
    private final String signingSecret;
    private final String commandPrefix;
    private final List<String> allowedChannels;

    private SlackConfig(Builder builder) {
        this.botToken = builder.botToken;
        this.appToken = builder.appToken;
        this.signingSecret = builder.signingSecret;
        this.commandPrefix = builder.commandPrefix != null ? builder.commandPrefix : "/harness";
        this.allowedChannels = builder.allowedChannels;
    }

    public String getBotToken() {
        return botToken;
    }

    public String getAppToken() {
        return appToken;
    }

    public String getSigningSecret() {
        return signingSecret;
    }

    public String getCommandPrefix() {
        return commandPrefix;
    }

    public List<String> getAllowedChannels() {
        return allowedChannels;
    }

    public static class Builder {
        private String botToken;
        private String appToken;
        private String signingSecret;
        private String commandPrefix = "/harness";
        private List<String> allowedChannels = new ArrayList<>();

        public Builder botToken(String botToken) {
            this.botToken = botToken;
            return this;
        }

        public Builder appToken(String appToken) {
            this.appToken = appToken;
            return this;
        }

        public Builder signingSecret(String signingSecret) {
            this.signingSecret = signingSecret;
            return this;
        }

        public Builder commandPrefix(String commandPrefix) {
            this.commandPrefix = commandPrefix;
            return this;
        }

        public Builder allowedChannels(List<String> allowedChannels) {
            this.allowedChannels = new ArrayList<>(allowedChannels);
            return this;
        }

        public SlackConfig build() {
            if (botToken == null || botToken.isEmpty()) {
                throw new IllegalArgumentException("botToken is required");
            }
            return new SlackConfig(this);
        }
    }
}
