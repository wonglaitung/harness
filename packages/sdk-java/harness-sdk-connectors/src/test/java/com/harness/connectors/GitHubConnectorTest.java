package com.harness.connectors;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for GitHubConnector.
 */
class GitHubConnectorTest {

    private GitHubConfig config;

    @BeforeEach
    void setUp() {
        // Config without credentials for webhook-only testing
        config = new GitHubConfig.Builder()
                .webhookSecret("whsec_test")
                .events(Arrays.asList("push", "pull_request", "issues"))
                .build();
    }

    @Test
    void testConfigBuilder() {
        assertEquals("whsec_test", config.getWebhookSecret());
        assertEquals(3, config.getEvents().size());
        assertTrue(config.getEvents().contains("push"));
    }

    @Test
    void testConfigWithoutCredentials() {
        // appId and privateKey are now optional (for webhook-only mode)
        GitHubConfig noCredConfig = new GitHubConfig.Builder()
                .webhookSecret("whsec_test")
                .build();

        assertNull(noCredConfig.getAppId());
        assertNull(noCredConfig.getPrivateKey());
        assertEquals("whsec_test", noCredConfig.getWebhookSecret());
    }

    @Test
    void testStartStop() {
        GitHubConnector connector = new GitHubConnector(config);

        assertFalse(connector.isRunning());

        connector.start(event -> {}).join();
        assertTrue(connector.isRunning());

        connector.stop().join();
        assertFalse(connector.isRunning());
    }

    @Test
    void testHandleWebhookPush() {
        GitHubConnector connector = new GitHubConnector(config);
        AtomicReference<ConnectorEvent> capturedEvent = new AtomicReference<>();

        connector.start(capturedEvent::set).join();

        Map<String, Object> payload = new HashMap<>();
        payload.put("ref", "refs/heads/main");

        Map<String, Object> repo = new HashMap<>();
        repo.put("full_name", "owner/repo");
        payload.put("repository", repo);

        Map<String, Object> sender = new HashMap<>();
        sender.put("login", "testuser");
        payload.put("sender", sender);

        connector.handleWebhook("push", payload);

        assertNotNull(capturedEvent.get());
        assertEquals("github.push", capturedEvent.get().getEventType());
        assertEquals("owner/repo", capturedEvent.get().getSource());
        assertEquals("owner/repo", capturedEvent.get().getRoutingMetadata().get(RoutingKeys.GITHUB_REPO));
        assertEquals("testuser", capturedEvent.get().getRoutingMetadata().get(RoutingKeys.USER_ID));
    }

    @Test
    void testHandleWebhookPullRequest() {
        GitHubConnector connector = new GitHubConnector(config);
        AtomicReference<ConnectorEvent> capturedEvent = new AtomicReference<>();

        connector.start(capturedEvent::set).join();

        Map<String, Object> payload = new HashMap<>();

        Map<String, Object> pr = new HashMap<>();
        pr.put("number", 42);
        pr.put("title", "Test PR");
        payload.put("pull_request", pr);

        Map<String, Object> repo = new HashMap<>();
        repo.put("full_name", "owner/repo");
        payload.put("repository", repo);

        connector.handleWebhook("pull_request", payload);

        assertNotNull(capturedEvent.get());
        assertEquals("github.pull_request", capturedEvent.get().getEventType());
        assertEquals(42, capturedEvent.get().getRoutingMetadata().get(RoutingKeys.GITHUB_PR_NUMBER));
    }

    @Test
    void testHandleWebhookIssue() {
        GitHubConnector connector = new GitHubConnector(config);
        AtomicReference<ConnectorEvent> capturedEvent = new AtomicReference<>();

        connector.start(capturedEvent::set).join();

        Map<String, Object> payload = new HashMap<>();

        Map<String, Object> issue = new HashMap<>();
        issue.put("number", 123);
        payload.put("issue", issue);

        Map<String, Object> repo = new HashMap<>();
        repo.put("full_name", "owner/repo");
        payload.put("repository", repo);

        connector.handleWebhook("issues", payload);

        assertNotNull(capturedEvent.get());
        assertEquals("github.issues", capturedEvent.get().getEventType());
        assertEquals(123, capturedEvent.get().getRoutingMetadata().get(RoutingKeys.GITHUB_ISSUE_NUMBER));
    }

    @Test
    void testHandleWebhookFilteredEvent() {
        GitHubConnector connector = new GitHubConnector(config);
        AtomicReference<ConnectorEvent> capturedEvent = new AtomicReference<>();

        connector.start(capturedEvent::set).join();

        Map<String, Object> payload = new HashMap<>();
        payload.put("action", "created");

        // "release" is not in our events list
        connector.handleWebhook("release", payload);

        assertNull(capturedEvent.get());
    }

    @Test
    void testCreatePrCommentWithoutCredentials() {
        // Without valid credentials, API calls return false
        GitHubConfig noCredConfig = new GitHubConfig.Builder()
                .webhookSecret("whsec_test")
                .build();
        GitHubConnector connector = new GitHubConnector(noCredConfig);
        connector.start(event -> {}).join();

        Boolean result = connector.createPrComment("owner/repo", 42, "Test comment").join();
        assertFalse(result);
    }

    @Test
    void testCreateIssueCommentWithoutCredentials() {
        GitHubConfig noCredConfig = new GitHubConfig.Builder()
                .webhookSecret("whsec_test")
                .build();
        GitHubConnector connector = new GitHubConnector(noCredConfig);
        connector.start(event -> {}).join();

        Boolean result = connector.createIssueComment("owner/repo", 123, "Test comment").join();
        assertFalse(result);
    }

    @Test
    void testGetPrWithoutCredentials() {
        GitHubConfig noCredConfig = new GitHubConfig.Builder()
                .webhookSecret("whsec_test")
                .build();
        GitHubConnector connector = new GitHubConnector(noCredConfig);
        connector.start(event -> {}).join();

        Map<String, Object> pr = connector.getPr("owner/repo", 42).join();
        assertNull(pr);
    }

    @Test
    void testApiMethodsExist() {
        // Verify API methods exist and return CompletableFuture
        GitHubConnector connector = new GitHubConnector(config);
        connector.start(event -> {}).join();

        // These will fail with test credentials, but the methods should exist
        assertNotNull(connector.createPrComment("owner/repo", 42, "test"));
        assertNotNull(connector.createIssueComment("owner/repo", 123, "test"));
        assertNotNull(connector.getPr("owner/repo", 42));
        assertNotNull(connector.getIssue("owner/repo", 123));
        assertNotNull(connector.createReview("owner/repo", 42, "APPROVE", "LGTM"));
        assertNotNull(connector.approvePr("owner/repo", 42, "LGTM"));
        assertNotNull(connector.requestChanges("owner/repo", 42, "Please fix"));
    }

    @Test
    void testConnectorType() {
        GitHubConnector connector = new GitHubConnector(config);
        assertEquals(ConnectorType.GITHUB, connector.getConnectorType());
    }

    @Test
    void testCustomConnectorId() {
        GitHubConnector connector = new GitHubConnector(config, "custom-github-id");
        assertEquals("custom-github-id", connector.getId());
    }
}
