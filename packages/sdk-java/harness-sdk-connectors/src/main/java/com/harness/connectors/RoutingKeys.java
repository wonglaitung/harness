package com.harness.connectors;

/**
 * Standard routing metadata keys.
 *
 * <p>Used in routingMetadata map to ensure naming consistency
 * across connectors and prevent typos.</p>
 */
public final class RoutingKeys {
    private RoutingKeys() {}

    // Slack related
    public static final String SLACK_THREAD_TS = "slack_thread_ts";
    public static final String SLACK_CHANNEL_ID = "slack_channel_id";

    // GitHub related
    public static final String GITHUB_PR_NUMBER = "github_pr_number";
    public static final String GITHUB_ISSUE_NUMBER = "github_issue_number";
    public static final String GITHUB_REPO = "github_repo";

    // Webhook related
    public static final String WEBHOOK_REQUEST_ID = "webhook_request_id";

    // Generic
    public static final String USER_ID = "user_id";
    public static final String TIMESTAMP = "timestamp";
}
