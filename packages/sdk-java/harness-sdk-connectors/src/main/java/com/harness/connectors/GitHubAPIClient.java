package com.harness.connectors;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.StringReader;
import java.net.http.HttpResponse;
import java.security.KeyFactory;
import java.security.PrivateKey;
import java.security.Signature;
import java.security.spec.PKCS8EncodedKeySpec;
import java.util.Base64;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;

/**
 * GitHub API client with GitHub App authentication.
 *
 * <p>Supports:</p>
 * <ul>
 *   <li>GitHub App JWT authentication</li>
 *   <li>Installation token generation</li>
 *   <li>Issue/PR comment creation</li>
 *   <li>PR/Issue retrieval</li>
 * </ul>
 *
 * <h2>Authentication Flow</h2>
 * <ol>
 *   <li>Generate JWT from private key (valid 10 minutes)</li>
 *   <li>Get installation access token using JWT</li>
 *   <li>Use installation token for API calls</li>
 * </ol>
 */
class GitHubAPIClient {
    private static final Logger logger = LoggerFactory.getLogger(GitHubAPIClient.class);

    private static final String API_BASE = "https://api.github.com";
    private static final long JWT_EXPIRY_SECONDS = 600; // 10 minutes

    private final String appId;
    private final PrivateKey privateKey;
    private final HttpClient httpClient;

    private String installationToken;
    private long tokenExpiresAt;

    GitHubAPIClient(String appId, String privateKeyPem) {
        this.appId = appId;
        this.privateKey = parsePrivateKey(privateKeyPem);
        this.httpClient = new HttpClient();
    }

    /**
     * Create a comment on an issue or PR.
     *
     * @param repo        Repository name (owner/repo)
     * @param issueNumber Issue or PR number
     * @param body        Comment body (markdown supported)
     * @return CompletableFuture with success status
     */
    CompletableFuture<Boolean> createIssueComment(String repo, int issueNumber, String body) {
        return withInstallationToken()
                .thenCompose(token -> {
                    String url = String.format("%s/repos/%s/issues/%d/comments", API_BASE, repo, issueNumber);

                    Map<String, Object> requestBody = new HashMap<>();
                    requestBody.put("body", body);

                    Map<String, String> headers = authHeaders(token);

                    try {
                        HttpResponse<String> response = httpClient.post(url, requestBody, headers);

                        if (response.statusCode() == 201) {
                            logger.info("Created comment on {}#{}", repo, issueNumber);
                            return CompletableFuture.completedFuture(true);
                        } else {
                            logger.warn("Failed to create comment: {} - {}", response.statusCode(), response.body());
                            return CompletableFuture.completedFuture(false);
                        }
                    } catch (Exception e) {
                        logger.error("Error creating comment: {}", e.getMessage());
                        return CompletableFuture.completedFuture(false);
                    }
                });
    }

    /**
     * Get pull request details.
     *
     * @param repo     Repository name (owner/repo)
     * @param prNumber PR number
     * @return CompletableFuture with PR data or null if not found
     */
    CompletableFuture<Map<String, Object>> getPr(String repo, int prNumber) {
        return withInstallationToken()
                .thenApply(token -> {
                    String url = String.format("%s/repos/%s/pulls/%d", API_BASE, repo, prNumber);

                    try {
                        HttpResponse<String> response = httpClient.get(url, authHeaders(token));

                        if (response.statusCode() == 200) {
                            return httpClient.parseJson(response.body());
                        } else if (response.statusCode() == 404) {
                            logger.warn("PR not found: {}#{}", repo, prNumber);
                            return null;
                        } else {
                            logger.warn("Failed to get PR: {} - {}", response.statusCode(), response.body());
                            return null;
                        }
                    } catch (Exception e) {
                        logger.error("Error getting PR: {}", e.getMessage());
                        return null;
                    }
                });
    }

    /**
     * Get issue details.
     *
     * @param repo       Repository name (owner/repo)
     * @param issueNumber Issue number
     * @return CompletableFuture with issue data or null if not found
     */
    CompletableFuture<Map<String, Object>> getIssue(String repo, int issueNumber) {
        return withInstallationToken()
                .thenApply(token -> {
                    String url = String.format("%s/repos/%s/issues/%d", API_BASE, repo, issueNumber);

                    try {
                        HttpResponse<String> response = httpClient.get(url, authHeaders(token));

                        if (response.statusCode() == 200) {
                            return httpClient.parseJson(response.body());
                        } else if (response.statusCode() == 404) {
                            logger.warn("Issue not found: {}#{}", repo, issueNumber);
                            return null;
                        } else {
                            logger.warn("Failed to get issue: {} - {}", response.statusCode(), response.body());
                            return null;
                        }
                    } catch (Exception e) {
                        logger.error("Error getting issue: {}", e.getMessage());
                        return null;
                    }
                });
    }

    /**
     * Create a review on a PR.
     *
     * @param repo     Repository name (owner/repo)
     * @param prNumber PR number
     * @param event    Review event (APPROVE, REQUEST_CHANGES, COMMENT)
     * @param body     Review body
     * @return CompletableFuture with success status
     */
    CompletableFuture<Boolean> createReview(String repo, int prNumber, String event, String body) {
        return withInstallationToken()
                .thenCompose(token -> {
                    String url = String.format("%s/repos/%s/pulls/%d/reviews", API_BASE, repo, prNumber);

                    Map<String, Object> requestBody = new HashMap<>();
                    requestBody.put("event", event);
                    if (body != null && !body.isEmpty()) {
                        requestBody.put("body", body);
                    }

                    try {
                        HttpResponse<String> response = httpClient.post(url, requestBody, authHeaders(token));

                        if (response.statusCode() == 200 || response.statusCode() == 201) {
                            logger.info("Created review on {}#{}", repo, prNumber);
                            return CompletableFuture.completedFuture(true);
                        } else {
                            logger.warn("Failed to create review: {} - {}", response.statusCode(), response.body());
                            return CompletableFuture.completedFuture(false);
                        }
                    } catch (Exception e) {
                        logger.error("Error creating review: {}", e.getMessage());
                        return CompletableFuture.completedFuture(false);
                    }
                });
    }

    /**
     * Get installation access token.
     *
     * <p>Generates a new token if the current one is expired or not set.</p>
     */
    private CompletableFuture<String> withInstallationToken() {
        // Check if we have a valid token
        if (installationToken != null && System.currentTimeMillis() < tokenExpiresAt) {
            return CompletableFuture.completedFuture(installationToken);
        }

        // Generate new token
        return generateInstallationToken();
    }

    /**
     * Generate installation access token using JWT.
     */
    private CompletableFuture<String> generateInstallationToken() {
        try {
            String jwt = generateJwt();

            // Get installation ID (for simplicity, we'll find it by app ID)
            return findInstallationId(jwt)
                    .thenCompose(installationId -> {
                        if (installationId == null) {
                            logger.error("No installation found for app {}", appId);
                            return CompletableFuture.completedFuture(null);
                        }

                        String url = String.format("%s/app/installations/%s/access_tokens", API_BASE, installationId);

                        Map<String, String> headers = new HashMap<>();
                        headers.put("Authorization", "Bearer " + jwt);
                        headers.put("Accept", "application/vnd.github+json");

                        try {
                            HttpResponse<String> response = httpClient.post(url, new HashMap<>(), headers);

                            if (response.statusCode() == 201) {
                                Map<String, Object> data = httpClient.parseJson(response.body());
                                installationToken = (String) data.get("token");
                                // Token expires in 1 hour
                                tokenExpiresAt = System.currentTimeMillis() + 3600 * 1000;
                                logger.debug("Generated installation token for app {}", appId);
                                return CompletableFuture.completedFuture(installationToken);
                            } else {
                                logger.error("Failed to get installation token: {} - {}", response.statusCode(), response.body());
                                return CompletableFuture.completedFuture(null);
                            }
                        } catch (Exception e) {
                            logger.error("Error getting installation token: {}", e.getMessage());
                            return CompletableFuture.completedFuture(null);
                        }
                    });
        } catch (Exception e) {
            logger.error("Error generating JWT: {}", e.getMessage());
            return CompletableFuture.completedFuture(null);
        }
    }

    /**
     * Find installation ID for this app.
     */
    private CompletableFuture<String> findInstallationId(String jwt) {
        String url = API_BASE + "/app/installations";

        Map<String, String> headers = new HashMap<>();
        headers.put("Authorization", "Bearer " + jwt);
        headers.put("Accept", "application/vnd.github+json");

        try {
            HttpResponse<String> response = httpClient.get(url, headers);

            if (response.statusCode() == 200) {
                java.util.List<Map<String, Object>> installations =
                        new com.fasterxml.jackson.databind.ObjectMapper()
                                .readValue(response.body(), java.util.List.class);

                if (!installations.isEmpty()) {
                    // Return the first installation
                    Map<String, Object> installation = installations.get(0);
                    return CompletableFuture.completedFuture(String.valueOf(installation.get("id")));
                }
            }

            return CompletableFuture.completedFuture(null);
        } catch (Exception e) {
            logger.error("Error finding installation: {}", e.getMessage());
            return CompletableFuture.completedFuture(null);
        }
    }

    /**
     * Generate JWT for GitHub App authentication.
     */
    private String generateJwt() {
        long now = System.currentTimeMillis() / 1000;

        return Jwts.builder()
                .issuer(appId)
                .issuedAt(new java.util.Date(now * 1000))
                .expiration(new java.util.Date((now + JWT_EXPIRY_SECONDS) * 1000))
                .signWith(privateKey)
                .compact();
    }

    /**
     * Create auth headers with installation token.
     */
    private Map<String, String> authHeaders(String token) {
        Map<String, String> headers = new HashMap<>();
        headers.put("Authorization", "Bearer " + token);
        headers.put("Accept", "application/vnd.github+json");
        headers.put("X-GitHub-Api-Version", "2022-11-28");
        return headers;
    }

    /**
     * Parse PEM private key.
     */
    private PrivateKey parsePrivateKey(String pem) {
        try {
            // Remove PEM header/footer and whitespace
            String privateKeyPEM = pem
                    .replace("-----BEGIN RSA PRIVATE KEY-----", "")
                    .replace("-----END RSA PRIVATE KEY-----", "")
                    .replace("-----BEGIN PRIVATE KEY-----", "")
                    .replace("-----END PRIVATE KEY-----", "")
                    .replaceAll("\\s", "");

            byte[] encoded = Base64.getDecoder().decode(privateKeyPEM);

            // Try PKCS8 first
            try {
                PKCS8EncodedKeySpec keySpec = new PKCS8EncodedKeySpec(encoded);
                KeyFactory keyFactory = KeyFactory.getInstance("RSA");
                return keyFactory.generatePrivate(keySpec);
            } catch (Exception e) {
                // Try PKCS1 format (needs conversion)
                logger.debug("Key not in PKCS8 format, attempting conversion");
                // For simplicity, we assume PKCS8 format
                throw new RuntimeException("Private key must be in PKCS8 format. Convert with: openssl pkcs8 -topk8 -inform PEM -outform PEM -nocrypt");
            }
        } catch (Exception e) {
            throw new RuntimeException("Failed to parse private key: " + e.getMessage(), e);
        }
    }
}
