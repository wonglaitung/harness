package com.harness.connectors;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * GitHub connector configuration.
 *
 * <p>Configuration for GitHub App integration.</p>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * GitHubConfig config = new GitHubConfig.Builder()
 *     .appId("123456")
 *     .privateKey("-----BEGIN RSA PRIVATE KEY-----\n...")
 *     .webhookSecret("whsec_...")
 *     .events(Arrays.asList("push", "pull_request"))
 *     .build();
 * }</pre>
 */
public class GitHubConfig {
    private final String appId;
    private final String privateKey;
    private final String webhookSecret;
    private final List<String> events;

    private GitHubConfig(Builder builder) {
        this.appId = builder.appId;
        this.privateKey = builder.privateKey;
        this.webhookSecret = builder.webhookSecret;
        this.events = builder.events;
    }

    public String getAppId() {
        return appId;
    }

    public String getPrivateKey() {
        return privateKey;
    }

    public String getWebhookSecret() {
        return webhookSecret;
    }

    public List<String> getEvents() {
        return events;
    }

    public static class Builder {
        private String appId;
        private String privateKey;
        private String webhookSecret;
        private List<String> events = Arrays.asList("push", "pull_request", "issues", "issue_comment");

        public Builder appId(String appId) {
            this.appId = appId;
            return this;
        }

        public Builder privateKey(String privateKey) {
            this.privateKey = privateKey;
            return this;
        }

        public Builder webhookSecret(String webhookSecret) {
            this.webhookSecret = webhookSecret;
            return this;
        }

        public Builder events(List<String> events) {
            this.events = new ArrayList<>(events);
            return this;
        }

        public GitHubConfig build() {
            // appId and privateKey are optional for webhook-only mode
            // They are required for API calls (create comments, get PRs, etc.)
            return new GitHubConfig(this);
        }
    }
}
