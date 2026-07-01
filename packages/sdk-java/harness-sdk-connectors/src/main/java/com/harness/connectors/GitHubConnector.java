package com.harness.connectors;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;

/**
 * GitHub connector for GitHub App integration.
 *
 * <p>Features:</p>
 * <ul>
 *   <li>Receive GitHub webhook events</li>
 *   <li>Create PR/Issue comments</li>
 *   <li>Extract routing metadata for PR/Issue context</li>
 * </ul>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * GitHubConnector github = new GitHubConnector(
 *     new GitHubConfig.Builder()
 *         .appId("123456")
 *         .privateKey("-----BEGIN RSA PRIVATE KEY-----\n...")
 *         .webhookSecret("whsec_...")
 *         .build()
 * );
 *
 * github.start(event -> {
 *     System.out.println("Received event: " + event.getEventType());
 * }).join();
 *
 * // Handle webhook
 * github.handleWebhook("pull_request", payload);
 *
 * // Create PR comment
 * github.createPrComment("owner/repo", 42, "Review complete!");
 * }</pre>
 */
public class GitHubConnector extends Connector {
    private static final Logger logger = LoggerFactory.getLogger(GitHubConnector.class);

    private final GitHubConfig config;
    private GitHubAPIClient apiClient;

    /**
     * Create a new GitHubConnector.
     *
     * @param config GitHub configuration
     */
    public GitHubConnector(GitHubConfig config) {
        super(ConnectorType.GITHUB);
        this.config = config;
    }

    /**
     * Create a new GitHubConnector with a specific ID.
     *
     * @param config GitHub configuration
     * @param connectorId Connector ID
     */
    public GitHubConnector(GitHubConfig config, String connectorId) {
        super(ConnectorType.GITHUB);
        this.config = config;
        this.id = connectorId;
    }

    @Override
    public CompletableFuture<Void> start(Consumer<ConnectorEvent> eventCallback) {
        this.eventCallback = eventCallback;

        try {
            // Initialize GitHub API client
            this.apiClient = new GitHubAPIClient(config.getAppId(), config.getPrivateKey());
            this.state = ConnectorState.RUNNING;
            logger.info("GitHubConnector started: {}", id);
            return CompletableFuture.completedFuture(null);
        } catch (Exception e) {
            logger.error("Failed to initialize GitHub client: {}", e.getMessage());
            this.state = ConnectorState.ERROR;
            return CompletableFuture.failedFuture(e);
        }
    }

    /**
     * Handle a GitHub webhook event.
     *
     * <p>Called by WebhookConnector when a GitHub webhook is received.</p>
     *
     * @param eventType GitHub event type (e.g., "push", "pull_request")
     * @param payload Webhook payload
     */
    public void handleWebhook(String eventType, Map<String, Object> payload) {
        // Check if we should handle this event
        if (!config.getEvents().contains(eventType)) {
            return;
        }

        // Extract routing metadata
        Map<String, Object> routingMetadata = extractRoutingMetadata(eventType, payload);

        // Get repository name
        @SuppressWarnings("unchecked")
        Map<String, Object> repo = (Map<String, Object>) payload.get("repository");
        String source = repo != null ? (String) repo.get("full_name") : "unknown";

        // Create event
        ConnectorEvent connectorEvent = createEvent(
                "github." + eventType,
                payload,
                source,
                routingMetadata
        );

        // Callback
        if (eventCallback != null) {
            eventCallback.accept(connectorEvent);
        }
    }

    /**
     * Extract routing metadata from GitHub payload.
     *
     * <p>Enables "reply to PR" functionality.</p>
     */
    @SuppressWarnings("unchecked")
    private Map<String, Object> extractRoutingMetadata(String eventType, Map<String, Object> payload) {
        Map<String, Object> metadata = new HashMap<>();

        // Pull request events
        if ("pull_request".equals(eventType) && payload.containsKey("pull_request")) {
            Map<String, Object> pr = (Map<String, Object>) payload.get("pull_request");
            metadata.put(RoutingKeys.GITHUB_PR_NUMBER, pr.get("number"));
        }

        // Issue events
        if (("issues".equals(eventType) || "issue_comment".equals(eventType))
                && payload.containsKey("issue")) {
            Map<String, Object> issue = (Map<String, Object>) payload.get("issue");
            metadata.put(RoutingKeys.GITHUB_ISSUE_NUMBER, issue.get("number"));
        }

        // Repository info
        Map<String, Object> repo = (Map<String, Object>) payload.get("repository");
        if (repo != null && repo.get("full_name") != null) {
            metadata.put(RoutingKeys.GITHUB_REPO, repo.get("full_name"));
        }

        // User info
        Map<String, Object> sender = (Map<String, Object>) payload.get("sender");
        if (sender != null && sender.get("login") != null) {
            metadata.put(RoutingKeys.USER_ID, sender.get("login"));
        }

        return metadata;
    }

    /**
     * Create a comment on a pull request.
     *
     * @param repo Repository name (owner/repo)
     * @param prNumber PR number
     * @param body Comment body
     * @return CompletableFuture with success status
     */
    public CompletableFuture<Boolean> createPrComment(String repo, int prNumber, String body) {
        if (apiClient == null) {
            logger.warn("GitHub client not initialized");
            return CompletableFuture.completedFuture(false);
        }

        return apiClient.createIssueComment(repo, prNumber, body)
                .thenApply(success -> {
                    if (success) {
                        logger.info("Created PR comment on {}#{}", repo, prNumber);
                    }
                    return success;
                })
                .exceptionally(e -> {
                    logger.error("Failed to create PR comment: {}", e.getMessage());
                    return false;
                });
    }

    /**
     * Create a comment on an issue.
     *
     * @param repo Repository name (owner/repo)
     * @param issueNumber Issue number
     * @param body Comment body
     * @return CompletableFuture with success status
     */
    public CompletableFuture<Boolean> createIssueComment(String repo, int issueNumber, String body) {
        // Issues and PRs share the same API
        return createPrComment(repo, issueNumber, body);
    }

    /**
     * Get pull request details.
     *
     * @param repo Repository name (owner/repo)
     * @param prNumber PR number
     * @return CompletableFuture with PR data or null if not found
     */
    public CompletableFuture<Map<String, Object>> getPr(String repo, int prNumber) {
        if (apiClient == null) {
            return CompletableFuture.completedFuture(null);
        }

        return apiClient.getPr(repo, prNumber)
                .exceptionally(e -> {
                    logger.error("Failed to get PR: {}", e.getMessage());
                    return null;
                });
    }

    @Override
    public CompletableFuture<Void> stop() {
        this.apiClient = null;
        this.eventCallback = null;
        this.state = ConnectorState.STOPPED;
        logger.info("GitHubConnector stopped: {}", id);
        return CompletableFuture.completedFuture(null);
    }

    /**
     * Internal GitHub API client.
     *
     * <p>A lightweight client for GitHub App authentication and API calls.
     * In production, this would use a library like org.kohsuke:github-api.</p>
     */
    private static class GitHubAPIClient {
        private final String appId;
        private final String privateKey;

        GitHubAPIClient(String appId, String privateKey) {
            this.appId = appId;
            this.privateKey = privateKey;
        }

        CompletableFuture<Boolean> createIssueComment(String repo, int issueNumber, String body) {
            // In production, use: POST /repos/{owner}/{repo}/issues/{issue_number}/comments
            logger.info("Would create comment on {}#{}: {}...", repo, issueNumber,
                    body.length() > 50 ? body.substring(0, 50) : body);
            return CompletableFuture.completedFuture(true);
        }

        CompletableFuture<Map<String, Object>> getPr(String repo, int prNumber) {
            // In production, use: GET /repos/{owner}/{repo}/pulls/{pull_number}
            Map<String, Object> result = new HashMap<>();
            result.put("number", prNumber);
            result.put("title", "PR #" + prNumber);
            result.put("state", "open");
            return CompletableFuture.completedFuture(result);
        }
    }
}
