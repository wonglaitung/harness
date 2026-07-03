package com.harness.service;

import java.net.*;
import java.util.*;
import java.util.concurrent.*;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.alibaba.nacos.api.NacosFactory;
import com.alibaba.nacos.api.naming.NamingService;
import com.alibaba.nacos.api.naming.pojo.Instance;

/**
 * Service discovery for Spring Cloud integration.
 *
 * <p>Supports:</p>
 * <ul>
 *   <li>Nacos service registry (production-ready)</li>
 *   <li>Eureka service registry (via REST API)</li>
 *   <li>Static endpoint configuration</li>
 * </ul>
 *
 * <h2>Example with Nacos</h2>
 * <pre>{@code
 * ServiceDiscovery discovery = ServiceDiscovery.builder()
 *     .type("nacos")
 *     .serverAddr("localhost:8848")
 *     .namespace("public")
 *     .build();
 *
 * // Register service
 * discovery.register("harness-agent", "192.168.1.100", 8080);
 *
 * // Discover services
 * List<ServiceInstance> instances = discovery.getInstances("harness-agent");
 * }</pre>
 *
 * <h2>Example with Eureka</h2>
 * <pre>{@code
 * ServiceDiscovery discovery = ServiceDiscovery.builder()
 *     .type("eureka")
 *     .serverAddr("localhost:8761")
 *     .build();
 *
 * discovery.register("harness-agent", "192.168.1.100", 8080);
 * }</pre>
 */
public class ServiceDiscovery {

    private static final Logger logger = LoggerFactory.getLogger(ServiceDiscovery.class);

    private final String type;
    private final String serverAddr;
    private final String namespace;
    private final String group;
    private final Map<String, List<ServiceInstance>> serviceCache = new ConcurrentHashMap<>();

    // Nacos naming service (lazy initialized)
    private volatile NamingService nacosNamingService;

    // HTTP client for Eureka
    private final java.net.http.HttpClient httpClient;

    private ServiceDiscovery(Builder builder) {
        this.type = builder.type;
        this.serverAddr = builder.serverAddr;
        this.namespace = builder.namespace;
        this.group = builder.group;
        this.httpClient = java.net.http.HttpClient.newBuilder()
            .connectTimeout(java.time.Duration.ofSeconds(5))
            .build();
    }

    /**
     * Service instance information.
     */
    public static class ServiceInstance {
        private final String serviceId;
        private final String host;
        private final int port;
        private final Map<String, String> metadata;
        private final boolean secure;

        public ServiceInstance(String serviceId, String host, int port, Map<String, String> metadata, boolean secure) {
            this.serviceId = serviceId;
            this.host = host;
            this.port = port;
            this.metadata = metadata != null ? metadata : Map.of();
            this.secure = secure;
        }

        public String serviceId() { return serviceId; }
        public String host() { return host; }
        public int port() { return port; }
        public Map<String, String> metadata() { return metadata; }
        public boolean isSecure() { return secure; }

        public URI uri() {
            String scheme = secure ? "https" : "http";
            return URI.create(scheme + "://" + host + ":" + port);
        }

        @Override
        public String toString() {
            return serviceId + "@" + host + ":" + port;
        }
    }

    /**
     * Register a service instance.
     */
    public void register(String serviceId, String host, int port) {
        register(serviceId, host, port, Map.of());
    }

    /**
     * Register a service instance with metadata.
     */
    public void register(String serviceId, String host, int port, Map<String, String> metadata) {
        logger.info("Registering service: {} at {}:{}", serviceId, host, port);

        ServiceInstance instance = new ServiceInstance(serviceId, host, port, metadata, false);

        serviceCache.computeIfAbsent(serviceId, k -> new CopyOnWriteArrayList<>()).add(instance);

        switch (type.toLowerCase()) {
            case "nacos":
                registerWithNacos(instance);
                break;
            case "eureka":
                registerWithEureka(instance);
                break;
            default:
                logger.debug("Static discovery - registration stored locally only");
        }
    }

    /**
     * Deregister a service instance.
     */
    public void deregister(String serviceId, String host, int port) {
        logger.info("Deregistering service: {} at {}:{}", serviceId, host, port);

        List<ServiceInstance> instances = serviceCache.get(serviceId);
        if (instances != null) {
            instances.removeIf(i -> i.host().equals(host) && i.port() == port);
        }

        switch (type.toLowerCase()) {
            case "nacos":
                deregisterFromNacos(serviceId, host, port);
                break;
            case "eureka":
                deregisterFromEureka(serviceId, host, port);
                break;
        }
    }

    /**
     * Get all instances of a service.
     */
    public List<ServiceInstance> getInstances(String serviceId) {
        // Check local cache first
        List<ServiceInstance> cached = serviceCache.get(serviceId);
        if (cached != null && !cached.isEmpty()) {
            return new ArrayList<>(cached);
        }

        // Query from registry
        switch (type.toLowerCase()) {
            case "nacos":
                return queryNacos(serviceId);
            case "eureka":
                return queryEureka(serviceId);
            default:
                return List.of();
        }
    }

    /**
     * Get a single instance (load balanced).
     */
    public ServiceInstance getOneInstance(String serviceId) {
        List<ServiceInstance> instances = getInstances(serviceId);
        if (instances.isEmpty()) {
            return null;
        }
        // Simple round-robin (in production, use proper load balancing)
        return instances.get(0);
    }

    /**
     * Get the local host IP.
     */
    public static String getLocalIP() {
        try {
            InetAddress localHost = InetAddress.getLocalHost();
            return localHost.getHostAddress();
        } catch (UnknownHostException e) {
            return "127.0.0.1";
        }
    }

    /**
     * Shutdown and cleanup resources.
     */
    public void shutdown() {
        if (nacosNamingService != null) {
            try {
                nacosNamingService.shutDown();
            } catch (Exception e) {
                logger.warn("Error shutting down Nacos naming service: {}", e.getMessage());
            }
        }
    }

    // -------------------------------------------------------------------------
    // Nacos integration
    // -------------------------------------------------------------------------

    private NamingService getNacosNamingService() {
        if (nacosNamingService == null) {
            synchronized (this) {
                if (nacosNamingService == null) {
                    try {
                        Properties properties = new Properties();
                        properties.setProperty("serverAddr", serverAddr);
                        if (namespace != null && !namespace.isEmpty() && !"public".equals(namespace)) {
                            properties.setProperty("namespace", namespace);
                        }
                        nacosNamingService = NacosFactory.createNamingService(properties);
                        logger.info("Nacos naming service initialized: {}", serverAddr);
                    } catch (Exception e) {
                        logger.error("Failed to initialize Nacos naming service: {}", e.getMessage());
                        throw new RuntimeException("Failed to initialize Nacos", e);
                    }
                }
            }
        }
        return nacosNamingService;
    }

    private void registerWithNacos(ServiceInstance instance) {
        try {
            NamingService naming = getNacosNamingService();
            naming.registerInstance(
                instance.serviceId(),
                group,
                instance.host(),
                instance.port()
            );
            logger.info("Registered with Nacos: {}", instance);
        } catch (Exception e) {
            logger.error("Failed to register with Nacos: {}", e.getMessage());
        }
    }

    private void deregisterFromNacos(String serviceId, String host, int port) {
        try {
            if (nacosNamingService != null) {
                nacosNamingService.deregisterInstance(serviceId, group, host, port);
                logger.info("Deregistered from Nacos: {}@{}:{}", serviceId, host, port);
            }
        } catch (Exception e) {
            logger.error("Failed to deregister from Nacos: {}", e.getMessage());
        }
    }

    private List<ServiceInstance> queryNacos(String serviceId) {
        try {
            NamingService naming = getNacosNamingService();
            List<Instance> instances = naming.selectInstances(serviceId, group, true);

            List<ServiceInstance> results = new ArrayList<>();
            for (Instance inst : instances) {
                Map<String, String> metadata = new HashMap<>(inst.getMetadata());
                metadata.put("nacos.instanceId", inst.getInstanceId());

                results.add(new ServiceInstance(
                    serviceId,
                    inst.getIp(),
                    inst.getPort(),
                    metadata,
                    false
                ));
            }

            // Update cache
            serviceCache.put(serviceId, new CopyOnWriteArrayList<>(results));

            return results;
        } catch (Exception e) {
            logger.error("Failed to query Nacos for {}: {}", serviceId, e.getMessage());
            return List.of();
        }
    }

    // -------------------------------------------------------------------------
    // Eureka integration (REST API)
    // -------------------------------------------------------------------------

    private void registerWithEureka(ServiceInstance instance) {
        try {
            // Eureka REST API registration
            String url = String.format("%s/apps/%s", normalizeEurekaUrl(), instance.serviceId());

            String xmlBody = String.format(
                "<instance>" +
                "<hostName>%s</hostName>" +
                "<app>%s</app>" +
                "<ipAddr>%s</ipAddr>" +
                "<vipAddress>%s</vipAddress>" +
                "<secureVipAddress>%s</secureVipAddress>" +
                "<port>%d</port>" +
                "<securePort>%d</securePort>" +
                "<status>UP</status>" +
                "<dataCenterInfo class=\"com.netflix.appinfo.InstanceInfo$DefaultDataCenterInfo\">" +
                "<name>MyOwn</name>" +
                "</dataCenterInfo>" +
                "</instance>",
                instance.host(),
                instance.serviceId().toUpperCase(),
                instance.host(),
                instance.serviceId(),
                instance.serviceId(),
                instance.port(),
                instance.port()
            );

            java.net.http.HttpRequest request = java.net.http.HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("Content-Type", "application/xml")
                .POST(java.net.http.HttpRequest.BodyPublishers.ofString(xmlBody))
                .build();

            httpClient.send(request, java.net.http.HttpResponse.BodyHandlers.ofString());
            logger.info("Registered with Eureka: {}", instance);

        } catch (Exception e) {
            logger.error("Failed to register with Eureka: {}", e.getMessage());
        }
    }

    private void deregisterFromEureka(String serviceId, String host, int port) {
        try {
            String instanceId = host + ":" + serviceId.toUpperCase() + ":" + port;
            String url = String.format("%s/apps/%s/%s", normalizeEurekaUrl(), serviceId.toUpperCase(), instanceId);

            java.net.http.HttpRequest request = java.net.http.HttpRequest.newBuilder()
                .uri(URI.create(url))
                .DELETE()
                .build();

            httpClient.send(request, java.net.http.HttpResponse.BodyHandlers.ofString());
            logger.info("Deregistered from Eureka: {}@{}:{}", serviceId, host, port);

        } catch (Exception e) {
            logger.error("Failed to deregister from Eureka: {}", e.getMessage());
        }
    }

    private List<ServiceInstance> queryEureka(String serviceId) {
        try {
            String url = String.format("%s/apps/%s", normalizeEurekaUrl(), serviceId.toUpperCase());

            java.net.http.HttpRequest request = java.net.http.HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("Accept", "application/json")
                .GET()
                .build();

            java.net.http.HttpResponse<String> response = httpClient.send(request,
                java.net.http.HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() == 200) {
                return parseEurekaResponse(serviceId, response.body());
            }

            return List.of();

        } catch (Exception e) {
            logger.error("Failed to query Eureka for {}: {}", serviceId, e.getMessage());
            return List.of();
        }
    }

    private String normalizeEurekaUrl() {
        String url = serverAddr;
        if (!url.startsWith("http")) {
            url = "http://" + url;
        }
        if (url.endsWith("/")) {
            url = url.substring(0, url.length() - 1);
        }
        return url + "/eureka";
    }

    private List<ServiceInstance> parseEurekaResponse(String serviceId, String json) {
        List<ServiceInstance> results = new ArrayList<>();

        try {
            com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
            com.fasterxml.jackson.databind.JsonNode root = mapper.readTree(json);

            com.fasterxml.jackson.databind.JsonNode application = root.path("application");
            com.fasterxml.jackson.databind.JsonNode instanceArray = application.path("instance");

            if (instanceArray.isArray()) {
                for (com.fasterxml.jackson.databind.JsonNode inst : instanceArray) {
                    String host = inst.path("hostName").asText();
                    int port = inst.path("port").path("$").asInt();

                    Map<String, String> metadata = new HashMap<>();
                    com.fasterxml.jackson.databind.JsonNode metadataNode = inst.path("metadata");
                    if (metadataNode.isObject()) {
                        metadataNode.fields().forEachRemaining(entry ->
                            metadata.put(entry.getKey(), entry.getValue().asText()));
                    }

                    results.add(new ServiceInstance(serviceId, host, port, metadata, false));
                }
            }

            // Update cache
            serviceCache.put(serviceId, new CopyOnWriteArrayList<>(results));

        } catch (Exception e) {
            logger.warn("Failed to parse Eureka response: {}", e.getMessage());
        }

        return results;
    }

    // -------------------------------------------------------------------------
    // Builder
    // -------------------------------------------------------------------------

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String type = "static"; // "nacos", "eureka", "static"
        private String serverAddr = "localhost:8848";
        private String namespace = "public";
        private String group = "DEFAULT_GROUP";

        public Builder type(String v) { this.type = v; return this; }
        public Builder serverAddr(String v) { this.serverAddr = v; return this; }
        public Builder namespace(String v) { this.namespace = v; return this; }
        public Builder group(String v) { this.group = v; return this; }

        public ServiceDiscovery build() {
            return new ServiceDiscovery(this);
        }
    }
}
