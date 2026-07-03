package com.harness.connectors;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.HashMap;
import java.util.Map;

/**
 * Shared HTTP client for API calls.
 *
 * <p>Provides a simple, dependency-free HTTP client using Java 11+ HttpClient.
 * Supports JSON request/response handling.</p>
 */
class HttpClient {
    private static final Logger logger = LoggerFactory.getLogger(HttpClient.class);

    private final java.net.http.HttpClient client;
    private static final com.fasterxml.jackson.databind.ObjectMapper mapper =
            new com.fasterxml.jackson.databind.ObjectMapper();

    HttpClient() {
        this.client = java.net.http.HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(10))
                .build();
    }

    /**
     * Make a GET request.
     *
     * @param url     URL to request
     * @param headers Headers to include
     * @return Response as string
     */
    HttpResponse<String> get(String url, Map<String, String> headers) throws IOException, InterruptedException {
        HttpRequest.Builder builder = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .GET()
                .timeout(Duration.ofSeconds(30));

        headers.forEach(builder::header);

        HttpRequest request = builder.build();
        logger.debug("GET {}", url);

        return client.send(request, HttpResponse.BodyHandlers.ofString());
    }

    /**
     * Make a POST request with JSON body.
     *
     * @param url     URL to request
     * @param body    Request body (will be serialized to JSON)
     * @param headers Headers to include
     * @return Response as string
     */
    HttpResponse<String> post(String url, Object body, Map<String, String> headers) throws IOException, InterruptedException {
        String jsonBody = mapper.writeValueAsString(body);

        HttpRequest.Builder builder = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
                .timeout(Duration.ofSeconds(30));

        headers.forEach(builder::header);

        HttpRequest request = builder.build();
        logger.debug("POST {} (body: {} bytes)", url, jsonBody.length());

        return client.send(request, HttpResponse.BodyHandlers.ofString());
    }

    /**
     * Make a POST request with form data.
     *
     * @param url     URL to request
     * @param form    Form data
     * @param headers Headers to include
     * @return Response as string
     */
    HttpResponse<String> postForm(String url, Map<String, String> form, Map<String, String> headers) throws IOException, InterruptedException {
        StringBuilder formBody = new StringBuilder();
        boolean first = true;
        for (Map.Entry<String, String> entry : form.entrySet()) {
            if (!first) formBody.append("&");
            formBody.append(java.net.URLEncoder.encode(entry.getKey(), "UTF-8"));
            formBody.append("=");
            formBody.append(java.net.URLEncoder.encode(entry.getValue(), "UTF-8"));
            first = false;
        }

        HttpRequest.Builder builder = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("Content-Type", "application/x-www-form-urlencoded")
                .POST(HttpRequest.BodyPublishers.ofString(formBody.toString()))
                .timeout(Duration.ofSeconds(30));

        headers.forEach(builder::header);

        HttpRequest request = builder.build();
        logger.debug("POST {} (form)", url);

        return client.send(request, HttpResponse.BodyHandlers.ofString());
    }

    /**
     * Parse JSON response to Map.
     */
    @SuppressWarnings("unchecked")
    Map<String, Object> parseJson(String json) throws Exception {
        if (json == null || json.isEmpty()) {
            return new HashMap<>();
        }
        return mapper.readValue(json, Map.class);
    }

    /**
     * Parse JSON response to a specific type.
     */
    <T> T parseJson(String json, Class<T> type) throws Exception {
        if (json == null || json.isEmpty()) {
            return null;
        }
        return mapper.readValue(json, type);
    }

    /**
     * Serialize object to JSON.
     */
    String toJson(Object obj) throws Exception {
        return mapper.writeValueAsString(obj);
    }
}
