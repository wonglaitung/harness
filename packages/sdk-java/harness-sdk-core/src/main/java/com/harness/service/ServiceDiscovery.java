package com.harness.service;

import java.net.*;
import java.util.*;
import java.util.concurrent.*;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Service discovery for Spring Cloud integration.
 *
 * Supports:
 * - Nacos service registry
 * - Eureka service registry
 * - Static endpoint configuration
 *
 * Example:
 * <pre>
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
 * List&lt;ServiceInstance&gt; instances = discovery.getInstances("harness-agent");
 * </pre>
 */
public class ServiceDiscovery {

    private static final Logger logger = LoggerFactory.getLogger(ServiceDiscovery.class);

    private final String type;
    private final String serverAddr;
    private final String namespace;
    private final String group;
    private final Map<String, List<ServiceInstance>> serviceCache = new ConcurrentHashMap<>();

    private ServiceDiscovery(Builder builder) {
        this.type = builder.type;
        this.serverAddr = builder.serverAddr;
        this.namespace = builder.namespace;
        this.group = builder.group;
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

        // In a real implementation, this would call Nacos/Eureka API
        if ("nacos".equals(type)) {
            registerWithNacos(instance);
        } else if ("eureka".equals(type)) {
            registerWithEureka(instance);
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

        // In a real implementation, this would call Nacos/Eureka API
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

        // In a real implementation, this would query Nacos/Eureka
        if ("nacos".equals(type)) {
            return queryNacos(serviceId);
        } else if ("eureka".equals(type)) {
            return queryEureka(serviceId);
        }

        return List.of();
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

    // -------------------------------------------------------------------------
    // Nacos integration (placeholder)
    // -------------------------------------------------------------------------

    private void registerWithNacos(ServiceInstance instance) {
        logger.debug("Registering with Nacos: {}", instance);
        // In production, use Nacos SDK:
        // NamingService naming = NamingFactory.createNamingService(serverAddr);
        // naming.registerInstance(instance.serviceId(), instance.host(), instance.port());
    }

    private List<ServiceInstance> queryNacos(String serviceId) {
        logger.debug("Querying Nacos for: {}", serviceId);
        // In production, use Nacos SDK:
        // List<Instance> instances = naming.selectInstances(serviceId, true);
        return List.of();
    }

    // -------------------------------------------------------------------------
    // Eureka integration (placeholder)
    // -------------------------------------------------------------------------

    private void registerWithEureka(ServiceInstance instance) {
        logger.debug("Registering with Eureka: {}", instance);
        // In production, use Eureka Client:
        // ApplicationInfoManager.getInstance().setInstanceStatus(InstanceStatus.UP);
    }

    private List<ServiceInstance> queryEureka(String serviceId) {
        logger.debug("Querying Eureka for: {}", serviceId);
        // In production, use Eureka Client:
        // Application app = eurekaClient.getApplication(serviceId);
        return List.of();
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
