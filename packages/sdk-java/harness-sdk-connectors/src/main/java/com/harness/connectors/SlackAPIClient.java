package com.harness.connectors;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.http.HttpResponse;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * Slack API client with bot token authentication.
 *
 * <p>Supports:</p>
 * <ul>
 *   <li>Posting messages to channels</li>
 *   <li>Thread replies</li>
 *   <li>Ephemeral messages</li>
 *   <li>Block Kit messages</li>
 * </ul>
 *
 * <h2>Authentication</h2>
 * <p>Uses bot token (xoxb-) for API calls. For Socket Mode,
 * also requires app-level token (xapp-).</p>
 */
class SlackAPIClient {
    private static final Logger logger = LoggerFactory.getLogger(SlackAPIClient.class);

    private static final String API_BASE = "https://slack.com/api";

    private final String botToken;
    private final String appToken;
    private final HttpClient httpClient;

    SlackAPIClient(String botToken, String appToken) {
        this.botToken = botToken;
        this.appToken = appToken;
        this.httpClient = new HttpClient();
    }

    /**
     * Post a message to a channel.
     *
     * @param channel  Channel ID or name
     * @param text     Message text
     * @param blocks   Optional Block Kit blocks
     * @param threadTs Optional thread timestamp for replies
     * @return CompletableFuture with success status
     */
    CompletableFuture<Boolean> postMessage(
            String channel,
            String text,
            List<Map<String, Object>> blocks,
            String threadTs) {

        String url = API_BASE + "/chat.postMessage";

        Map<String, Object> requestBody = new HashMap<>();
        requestBody.put("channel", channel);
        requestBody.put("text", text);

        if (blocks != null && !blocks.isEmpty()) {
            requestBody.put("blocks", blocks);
        }

        if (threadTs != null && !threadTs.isEmpty()) {
            requestBody.put("thread_ts", threadTs);
        }

        try {
            HttpResponse<String> response = httpClient.post(url, requestBody, authHeaders());

            if (response.statusCode() == 200) {
                Map<String, Object> data = httpClient.parseJson(response.body());
                Boolean ok = (Boolean) data.get("ok");

                if (Boolean.TRUE.equals(ok)) {
                    logger.debug("Posted message to channel {}", channel);
                    return CompletableFuture.completedFuture(true);
                } else {
                    String error = (String) data.get("error");
                    logger.warn("Failed to post message: {}", error);
                    return CompletableFuture.completedFuture(false);
                }
            } else {
                logger.warn("Failed to post message: {} - {}", response.statusCode(), response.body());
                return CompletableFuture.completedFuture(false);
            }
        } catch (Exception e) {
            logger.error("Error posting message: {}", e.getMessage());
            return CompletableFuture.completedFuture(false);
        }
    }

    /**
     * Post an ephemeral message (visible only to a specific user).
     *
     * @param channel Channel ID
     * @param user    User ID
     * @param text    Message text
     * @param blocks  Optional Block Kit blocks
     * @return CompletableFuture with success status
     */
    CompletableFuture<Boolean> postEphemeral(
            String channel,
            String user,
            String text,
            List<Map<String, Object>> blocks) {

        String url = API_BASE + "/chat.postEphemeral";

        Map<String, Object> requestBody = new HashMap<>();
        requestBody.put("channel", channel);
        requestBody.put("user", user);
        requestBody.put("text", text);

        if (blocks != null && !blocks.isEmpty()) {
            requestBody.put("blocks", blocks);
        }

        try {
            HttpResponse<String> response = httpClient.post(url, requestBody, authHeaders());

            if (response.statusCode() == 200) {
                Map<String, Object> data = httpClient.parseJson(response.body());
                Boolean ok = (Boolean) data.get("ok");

                if (Boolean.TRUE.equals(ok)) {
                    logger.debug("Posted ephemeral message to {} for user {}", channel, user);
                    return CompletableFuture.completedFuture(true);
                } else {
                    String error = (String) data.get("error");
                    logger.warn("Failed to post ephemeral message: {}", error);
                    return CompletableFuture.completedFuture(false);
                }
            } else {
                logger.warn("Failed to post ephemeral message: {} - {}", response.statusCode(), response.body());
                return CompletableFuture.completedFuture(false);
            }
        } catch (Exception e) {
            logger.error("Error posting ephemeral message: {}", e.getMessage());
            return CompletableFuture.completedFuture(false);
        }
    }

    /**
     * Update an existing message.
     *
     * @param channel   Channel ID
     * @param ts        Message timestamp
     * @param text      New message text
     * @param blocks    Optional new blocks
     * @return CompletableFuture with success status
     */
    CompletableFuture<Boolean> updateMessage(
            String channel,
            String ts,
            String text,
            List<Map<String, Object>> blocks) {

        String url = API_BASE + "/chat.update";

        Map<String, Object> requestBody = new HashMap<>();
        requestBody.put("channel", channel);
        requestBody.put("ts", ts);
        requestBody.put("text", text);

        if (blocks != null && !blocks.isEmpty()) {
            requestBody.put("blocks", blocks);
        }

        try {
            HttpResponse<String> response = httpClient.post(url, requestBody, authHeaders());

            if (response.statusCode() == 200) {
                Map<String, Object> data = httpClient.parseJson(response.body());
                Boolean ok = (Boolean) data.get("ok");

                if (Boolean.TRUE.equals(ok)) {
                    logger.debug("Updated message {} in channel {}", ts, channel);
                    return CompletableFuture.completedFuture(true);
                } else {
                    String error = (String) data.get("error");
                    logger.warn("Failed to update message: {}", error);
                    return CompletableFuture.completedFuture(false);
                }
            } else {
                logger.warn("Failed to update message: {} - {}", response.statusCode(), response.body());
                return CompletableFuture.completedFuture(false);
            }
        } catch (Exception e) {
            logger.error("Error updating message: {}", e.getMessage());
            return CompletableFuture.completedFuture(false);
        }
    }

    /**
     * Delete a message.
     *
     * @param channel Channel ID
     * @param ts      Message timestamp
     * @return CompletableFuture with success status
     */
    CompletableFuture<Boolean> deleteMessage(String channel, String ts) {
        String url = API_BASE + "/chat.delete";

        Map<String, Object> requestBody = new HashMap<>();
        requestBody.put("channel", channel);
        requestBody.put("ts", ts);

        try {
            HttpResponse<String> response = httpClient.post(url, requestBody, authHeaders());

            if (response.statusCode() == 200) {
                Map<String, Object> data = httpClient.parseJson(response.body());
                Boolean ok = (Boolean) data.get("ok");

                if (Boolean.TRUE.equals(ok)) {
                    logger.debug("Deleted message {} in channel {}", ts, channel);
                    return CompletableFuture.completedFuture(true);
                } else {
                    String error = (String) data.get("error");
                    logger.warn("Failed to delete message: {}", error);
                    return CompletableFuture.completedFuture(false);
                }
            } else {
                logger.warn("Failed to delete message: {} - {}", response.statusCode(), response.body());
                return CompletableFuture.completedFuture(false);
            }
        } catch (Exception e) {
            logger.error("Error deleting message: {}", e.getMessage());
            return CompletableFuture.completedFuture(false);
        }
    }

    /**
     * Add a reaction to a message.
     *
     * @param channel Channel ID
     * @param ts      Message timestamp
     * @param emoji   Emoji name (without colons)
     * @return CompletableFuture with success status
     */
    CompletableFuture<Boolean> addReaction(String channel, String ts, String emoji) {
        String url = API_BASE + "/reactions.add";

        Map<String, Object> requestBody = new HashMap<>();
        requestBody.put("channel", channel);
        requestBody.put("timestamp", ts);
        requestBody.put("name", emoji);

        try {
            HttpResponse<String> response = httpClient.post(url, requestBody, authHeaders());

            if (response.statusCode() == 200) {
                Map<String, Object> data = httpClient.parseJson(response.body());
                Boolean ok = (Boolean) data.get("ok");

                if (Boolean.TRUE.equals(ok)) {
                    logger.debug("Added reaction :{}: to message {}", emoji, ts);
                    return CompletableFuture.completedFuture(true);
                } else {
                    // "already_reacted" is not really an error
                    String error = (String) data.get("error");
                    if ("already_reacted".equals(error)) {
                        return CompletableFuture.completedFuture(true);
                    }
                    logger.warn("Failed to add reaction: {}", error);
                    return CompletableFuture.completedFuture(false);
                }
            } else {
                logger.warn("Failed to add reaction: {} - {}", response.statusCode(), response.body());
                return CompletableFuture.completedFuture(false);
            }
        } catch (Exception e) {
            logger.error("Error adding reaction: {}", e.getMessage());
            return CompletableFuture.completedFuture(false);
        }
    }

    /**
     * Get user info.
     *
     * @param userId User ID
     * @return CompletableFuture with user data or null if not found
     */
    CompletableFuture<Map<String, Object>> getUserInfo(String userId) {
        String url = API_BASE + "/users.info?user=" + userId;

        try {
            HttpResponse<String> response = httpClient.get(url, authHeaders());

            if (response.statusCode() == 200) {
                Map<String, Object> data = httpClient.parseJson(response.body());
                Boolean ok = (Boolean) data.get("ok");

                if (Boolean.TRUE.equals(ok)) {
                    @SuppressWarnings("unchecked")
                    Map<String, Object> user = (Map<String, Object>) data.get("user");
                    return CompletableFuture.completedFuture(user);
                } else {
                    String error = (String) data.get("error");
                    logger.warn("Failed to get user info: {}", error);
                    return CompletableFuture.completedFuture(null);
                }
            } else {
                logger.warn("Failed to get user info: {} - {}", response.statusCode(), response.body());
                return CompletableFuture.completedFuture(null);
            }
        } catch (Exception e) {
            logger.error("Error getting user info: {}", e.getMessage());
            return CompletableFuture.completedFuture(null);
        }
    }

    /**
     * Test authentication.
     *
     * @return CompletableFuture with auth test result
     */
    CompletableFuture<Map<String, Object>> authTest() {
        String url = API_BASE + "/auth.test";

        try {
            HttpResponse<String> response = httpClient.post(url, new HashMap<>(), authHeaders());

            if (response.statusCode() == 200) {
                Map<String, Object> data = httpClient.parseJson(response.body());
                Boolean ok = (Boolean) data.get("ok");

                if (Boolean.TRUE.equals(ok)) {
                    logger.info("Slack auth test successful: bot_id={}, user={}",
                            data.get("bot_id"), data.get("user"));
                    return CompletableFuture.completedFuture(data);
                } else {
                    String error = (String) data.get("error");
                    logger.error("Slack auth test failed: {}", error);
                    return CompletableFuture.completedFuture(null);
                }
            } else {
                logger.error("Slack auth test failed: {} - {}", response.statusCode(), response.body());
                return CompletableFuture.completedFuture(null);
            }
        } catch (Exception e) {
            logger.error("Error testing auth: {}", e.getMessage());
            return CompletableFuture.completedFuture(null);
        }
    }

    /**
     * Create auth headers.
     */
    private Map<String, String> authHeaders() {
        Map<String, String> headers = new HashMap<>();
        headers.put("Authorization", "Bearer " + botToken);
        headers.put("Content-Type", "application/json; charset=utf-8");
        return headers;
    }
}
