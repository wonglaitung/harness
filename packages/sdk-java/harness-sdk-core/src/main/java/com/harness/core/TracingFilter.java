package com.harness.core;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

/**
 * HTTP Filter for W3C TraceContext propagation.
 *
 * Extracts TraceContext from HTTP headers and makes it available
 * for the duration of the request. Compatible with Spring Cloud Gateway.
 *
 * Spring Cloud Gateway (Sleuth/Micrometer) uses W3C TraceContext format:
 * - traceparent: version-trace-id-parent-id-flags
 * - tracestate: vendor-specific key-value pairs
 *
 * Example header from Spring Cloud:
 *     traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
 *
 * Usage in Spring Boot:
 * <pre>
 * &#64;Bean
 * public FilterRegistrationBean&lt;TracingFilter&gt; tracingFilter(TracingManager manager) {
 *     FilterRegistrationBean&lt;TracingFilter&gt; registration = new FilterRegistrationBean&lt;&gt;();
 *     registration.setFilter(new TracingFilter(manager));
 *     registration.addUrlPatterns("/*");
 *     return registration;
 * }
 * </pre>
 *
 * For JAX-RS, register as a ContainerRequestFilter:
 * <pre>
 * &#64;Provider
 * public class TracingFilter implements ContainerRequestFilter, ContainerResponseFilter {
 *     // ... implementation
 * }
 * </pre>
 */
public class TracingFilter {

    private final TracingManager tracingManager;

    // Header names
    public static final String TRACEPARENT = "traceparent";
    public static final String TRACESTATE = "tracestate";
    public static final String X_TRACE_ID = "X-Trace-Id";
    public static final String X_USER_ID = "X-User-Id";
    public static final String X_TENANT_ID = "X-Tenant-Id";

    public TracingFilter(TracingManager tracingManager) {
        this.tracingManager = tracingManager;
    }

    public TracingFilter() {
        this(new TracingManager());
    }

    /**
     * Process incoming request - extract trace context from headers.
     *
     * This method should be called at the beginning of request processing.
     *
     * @param headers Request headers
     * @return TraceContext that was extracted (for testing/logging)
     */
    public TraceContext beforeRequest(Map<String, String> headers) {
        if (!tracingManager.isEnabled()) {
            return TraceContext.empty();
        }

        // Extract trace context from headers
        TraceContext context = tracingManager.extractContext(headers);

        if (!context.isEmpty()) {
            // Set as current context
            tracingManager.withSpan("request", context, () -> {});

            // Extract additional context from Gateway headers
            String userId = headers.get(X_USER_ID);
            String tenantId = headers.get(X_TENANT_ID);

            if (userId != null) {
                tracingManager.addAttribute("user.id", userId);
            }
            if (tenantId != null) {
                tracingManager.addAttribute("user.tenant_id", tenantId);
            }

            // Add request metadata
            tracingManager.addAttribute("http.method", headers.getOrDefault("method", "GET"));
        }

        return context;
    }

    /**
     * Process outgoing response - inject trace context into headers.
     *
     * This method should be called before sending the response.
     *
     * @param headers Response headers to inject into
     */
    public void afterResponse(Map<String, String> headers) {
        if (!tracingManager.isEnabled()) {
            return;
        }

        TraceContext context = tracingManager.getCurrentContext();
        if (context != null && !context.isEmpty()) {
            // Inject trace ID into response headers for debugging
            headers.put(X_TRACE_ID, context.traceId());
        }
    }

    /**
     * Build headers map from request object.
     *
     * For Servlet:
     * <pre>
     * Map&lt;String, String&gt; headers = new HashMap&lt;&gt;();
     * Enumeration&lt;String&gt; headerNames = request.getHeaderNames();
     * while (headerNames.hasMoreElements()) {
     *     String name = headerNames.nextElement();
     *     headers.put(name, request.getHeader(name));
     * }
     * </pre>
     *
     * @param request HttpServletRequest or similar
     * @return Map of headers
     */
    public static Map<String, String> extractHeaders(Object request) {
        Map<String, String> headers = new HashMap<>();

        // This is a placeholder - actual implementation depends on framework
        // For Servlet: cast to HttpServletRequest and iterate headers
        // For JAX-RS: cast to ContainerRequestContext and getHeaders()

        return headers;
    }

    /**
     * Get the TracingManager.
     */
    public TracingManager getTracingManager() {
        return tracingManager;
    }
}
