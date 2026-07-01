package com.harness.connectors;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;

/**
 * Webhook connector for receiving HTTP webhook events.
 *
 * <p>This connector provides a simple way to receive webhook events
 * from external systems like GitHub, Stripe, or custom services.</p>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * WebhookConnector webhook = new WebhookConnector()
 *     .withEndpoint("/webhook/github")
 *     .withSecret("my-secret-key");
 *
 * ConnectorManager manager = new ConnectorManager();
 * manager.registerConnector(webhook);
 * manager.start().join();
 *
 * // Handle incoming webhooks
 * webhook.handleRequest(requestBody, headers);
 * }</pre>
 */
public class WebhookConnector extends Connector {
    private String endpoint = "/webhook";
    private String secret;
    private List<String> allowedIps;
    private int rateLimit = 100;

    /**
     * Create a new WebhookConnector.
     */
    public WebhookConnector() {
        super(ConnectorType.WEBHOOK);
    }

    /**
     * Set the webhook endpoint path.
     */
    public WebhookConnector withEndpoint(String endpoint) {
        this.endpoint = endpoint;
        return this;
    }

    /**
     * Set the signature verification secret.
     */
    public WebhookConnector withSecret(String secret) {
        this.secret = secret;
        return this;
    }

    /**
     * Set allowed IP addresses.
     */
    public WebhookConnector withAllowedIps(List<String> allowedIps) {
        this.allowedIps = allowedIps;
        return this;
    }

    /**
     * Set rate limit (requests per minute).
     */
    public WebhookConnector withRateLimit(int rateLimit) {
        this.rateLimit = rateLimit;
        return this;
    }

    @Override
    public CompletableFuture<Void> start(Consumer<ConnectorEvent> eventCallback) {
        this.eventCallback = eventCallback;
        this.state = ConnectorState.RUNNING;
        return CompletableFuture.completedFuture(null);
    }

    @Override
    public CompletableFuture<Void> stop() {
        this.state = ConnectorState.STOPPED;
        return CompletableFuture.completedFuture(null);
    }

    /**
     * Handle an incoming webhook request.
     *
     * <p>This method should be called by your HTTP server when
     * a webhook request is received.</p>
     *
     * @param body Request body
     * @param headers Request headers
     * @return true if the webhook was processed successfully
     */
    public boolean handleRequest(String body, Map<String, String> headers) {
        if (!isRunning()) {
            return false;
        }

        // Verify signature if secret is configured
        if (secret != null && !verifySignature(body, headers)) {
            return false;
        }

        // Create event
        Map<String, Object> payload = new HashMap<>();
        payload.put("body", body);
        payload.put("headers", headers);

        // Detect event type from headers
        String eventType = detectEventType(headers);

        ConnectorEvent event = createEvent(eventType, payload, "webhook");

        if (eventCallback != null) {
            eventCallback.accept(event);
        }

        return true;
    }

    /**
     * Handle an incoming webhook request with custom event type.
     */
    public boolean handleRequest(String eventType, String body, Map<String, String> headers,
            Map<String, Object> routingMetadata) {

        if (!isRunning()) {
            return false;
        }

        // Verify signature if secret is configured
        if (secret != null && !verifySignature(body, headers)) {
            return false;
        }

        Map<String, Object> payload = new HashMap<>();
        payload.put("body", body);
        payload.put("headers", headers);

        ConnectorEvent event = createEvent(eventType, payload, "webhook", routingMetadata);

        if (eventCallback != null) {
            eventCallback.accept(event);
        }

        return true;
    }

    private boolean verifySignature(String body, Map<String, String> headers) {
        String signature = headers.get("X-Hub-Signature-256");
        if (signature == null) {
            signature = headers.get("X-Hub-Signature");
        }

        if (signature == null) {
            return false;
        }

        // Simple HMAC verification (implementation depends on security requirements)
        try {
            javax.crypto.Mac mac = javax.crypto.Mac.getInstance("HmacSHA256");
            mac.init(new javax.crypto.spec.SecretKeySpec(secret.getBytes(), "HmacSHA256"));
            byte[] hash = mac.doFinal(body.getBytes());
            String expected = "sha256=" + bytesToHex(hash);
            return expected.equals(signature);
        } catch (Exception e) {
            return false;
        }
    }

    private String bytesToHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder();
        for (byte b : bytes) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }

    private String detectEventType(Map<String, String> headers) {
        // GitHub
        String githubEvent = headers.get("X-GitHub-Event");
        if (githubEvent != null) {
            return "github." + githubEvent;
        }

        // Stripe
        String stripeEvent = headers.get("Stripe-Event");
        if (stripeEvent != null) {
            return "stripe." + stripeEvent;
        }

        // Generic
        return "webhook.received";
    }

    // Getters

    public String getEndpoint() {
        return endpoint;
    }

    public String getSecret() {
        return secret;
    }

    public List<String> getAllowedIps() {
        return allowedIps;
    }

    public int getRateLimit() {
        return rateLimit;
    }
}
