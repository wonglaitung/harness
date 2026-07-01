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
        config = new GitHubConfig.Builder()
                .appId("123456")
                .privateKey("-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----")
                .webhookSecret("whsec_test")
                .events(Arrays.asList("push", "pull_request", "issues"))
                .build();
    }

    @Test
    void testConfigBuilder() {
        assertEquals("123456", config.getAppId());
        assertEquals("whsec_test", config.getWebhookSecret());
        assertEquals(3, config.getEvents().size());
        assertTrue(config.getEvents().contains("push"));
    }

    @Test
    void testConfigValidation() {
        // Missing appId
        assertThrows(IllegalArgumentException.class, () ->
                new GitHubConfig.Builder()
                        .privateKey("key")
                        .build());

        // Missing privateKey
        assertThrows(IllegalArgumentException.class, () ->
                new GitHubConfig.Builder()
                        .appId("123")
                        .build());
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
    void testCreatePrComment() {
        GitHubConnector connector = new GitHubConnector(config);
        connector.start(event -> {}).join();

        Boolean result = connector.createPrComment("owner/repo", 42, "Test comment").join();
        assertTrue(result);
    }

    @Test
    void testCreateIssueComment() {
        GitHubConnector connector = new GitHubConnector(config);
        connector.start(event -> {}).join();

        Boolean result = connector.createIssueComment("owner/repo", 123, "Test comment").join();
        assertTrue(result);
    }

    @Test
    void testGetPr() {
        GitHubConnector connector = new GitHubConnector(config);
        connector.start(event -> {}).join();

        Map<String, Object> pr = connector.getPr("owner/repo", 42).join();
        assertNotNull(pr);
        assertEquals(42, pr.get("number"));
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
