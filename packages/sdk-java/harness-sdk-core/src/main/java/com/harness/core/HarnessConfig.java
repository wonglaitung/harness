package com.harness.core;

import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Main configuration for AgentHarness.
 *
 * Provides a simple way to configure the agent without
 * building each component manually.
 *
 * Example:
 * <pre>
 * HarnessConfig config = HarnessConfig.builder()
 *     .model("claude-sonnet-4-6")
 *     .maxIterations(10)
 *     .toolTimeout(30.0)
 *     .build();
 *
 * AgentHarness agent = new AgentHarness(config);
 * </pre>
 */
public class HarnessConfig {

    /**
     * Action to take when document size exceeds limit.
     */
    public enum DocumentSizeAction {
        /** Log warning and continue processing */
        WARN,
        /** Throw DocumentTooLargeException */
        ERROR,
        /** Truncate document to limit size */
        TRUNCATE
    }

    // LLM settings
    private final String model;
    private final String apiKey;
    private final String provider; // "anthropic", "openai", "auto"
    private final String baseUrl;

    // Context settings
    private final int contextWindow;
    private final int maxTokens;
    private final double temperature;

    // Memory settings
    private final String memoryDir;
    private final String memoryMdPath;  // Path to MEMORY.md for UpdateCoreMemoryTool
    private final int sessionWindow;

    // Tool settings
    private final String sandboxWorkspace;
    private final boolean enableNetwork;

    // Compatibility settings
    private final String toolResultRole; // "tool" (native) or "user" (compatibility mode)

    // Loop settings
    private final int maxIterations;
    private final double toolTimeout;

    // System prompt
    private final String systemPrompt;

    // Document settings (文档大小检查)
    private final int maxDocumentSize;
    private final int maxTotalDocumentsSize;
    private final DocumentSizeAction documentSizeAction;
    private final double documentTokenWarningRatio;

    // Sub-configurations
    private final SecurityConfig security;
    private final CostControlConfig costControl;
    private final ObservabilityConfig observability;
    private final StorageConfig storage;
    private final OffloadConfig offload;
    private final RoutingConfig routing;

    private HarnessConfig(Builder builder) {
        this.model = builder.model;
        this.apiKey = builder.apiKey;
        this.provider = builder.provider;
        this.baseUrl = builder.baseUrl;
        this.contextWindow = builder.contextWindow;
        this.maxTokens = builder.maxTokens;
        this.temperature = builder.temperature;
        this.memoryDir = builder.memoryDir;
        this.memoryMdPath = builder.memoryMdPath;
        this.sessionWindow = builder.sessionWindow;
        this.sandboxWorkspace = builder.sandboxWorkspace;
        this.enableNetwork = builder.enableNetwork;
        this.toolResultRole = builder.toolResultRole;
        this.maxIterations = builder.maxIterations;
        this.toolTimeout = builder.toolTimeout;
        this.systemPrompt = builder.systemPrompt;
        this.maxDocumentSize = builder.maxDocumentSize;
        this.maxTotalDocumentsSize = builder.maxTotalDocumentsSize;
        this.documentSizeAction = builder.documentSizeAction;
        this.documentTokenWarningRatio = builder.documentTokenWarningRatio;
        this.security = builder.security;
        this.costControl = builder.costControl;
        this.observability = builder.observability;
        this.storage = builder.storage;
        this.offload = builder.offload;
        this.routing = builder.routing;
    }

    // Getters
    public String getModel() { return model; }
    public String getApiKey() { return apiKey; }
    public String getProvider() { return provider; }
    public String getBaseUrl() { return baseUrl; }
    public int getContextWindow() { return contextWindow; }
    public int getMaxTokens() { return maxTokens; }
    public double getTemperature() { return temperature; }
    public String getMemoryDir() { return memoryDir; }
    public String getMemoryMdPath() { return memoryMdPath; }
    public int getSessionWindow() { return sessionWindow; }
    public String getSandboxWorkspace() { return sandboxWorkspace; }
    public boolean isEnableNetwork() { return enableNetwork; }
    public String getToolResultRole() { return toolResultRole; }
    public int getMaxIterations() { return maxIterations; }
    public double getToolTimeout() { return toolTimeout; }
    public String getSystemPrompt() { return systemPrompt; }
    public int getMaxDocumentSize() { return maxDocumentSize; }
    public int getMaxTotalDocumentsSize() { return maxTotalDocumentsSize; }
    public DocumentSizeAction getDocumentSizeAction() { return documentSizeAction; }
    public double getDocumentTokenWarningRatio() { return documentTokenWarningRatio; }
    public SecurityConfig getSecurity() { return security; }
    public CostControlConfig getCostControl() { return costControl; }
    public ObservabilityConfig getObservability() { return observability; }
    public StorageConfig getStorage() { return storage; }
    public OffloadConfig getOffload() { return offload; }
    public RoutingConfig getRouting() { return routing; }

    /**
     * Create default configuration.
     */
    public static HarnessConfig defaults() {
        return builder().build();
    }

    /**
     * Create builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * Create configuration from environment variables.
     */
    public static HarnessConfig fromEnv() {
        Builder builder = builder();

        String apiKey = System.getenv("ANTHROPIC_API_KEY");
        if (apiKey == null) {
            apiKey = System.getenv("OPENAI_API_KEY");
        }

        String provider = "auto";
        if (System.getenv("ANTHROPIC_API_KEY") != null) {
            provider = "anthropic";
        } else if (System.getenv("OPENAI_API_KEY") != null) {
            provider = "openai";
        }

        String envProvider = System.getenv("HARNESS_PROVIDER");
        if (envProvider != null) {
            provider = envProvider;
        }

        builder.apiKey(apiKey);
        builder.provider(provider);

        String model = System.getenv("HARNESS_MODEL");
        if (model != null) {
            builder.model(model);
        }

        String baseUrl = System.getenv("HARNESS_BASE_URL");
        if (baseUrl != null) {
            builder.baseUrl(baseUrl);
        }

        String maxIterations = System.getenv("HARNESS_MAX_ITERATIONS");
        if (maxIterations != null) {
            builder.maxIterations(Integer.parseInt(maxIterations));
        }

        String systemPrompt = System.getenv("HARNESS_SYSTEM_PROMPT");
        if (systemPrompt != null) {
            builder.systemPrompt(systemPrompt);
        }

        String memoryDir = System.getenv("HARNESS_MEMORY_DIR");
        if (memoryDir != null) {
            builder.memoryDir(memoryDir);
        }

        return builder.build();
    }

    /**
     * Convert to map for serialization.
     */
    public Map<String, Object> toMap() {
        Map<String, Object> map = new HashMap<>();
        map.put("model", model);
        map.put("provider", provider);
        map.put("baseUrl", baseUrl);
        map.put("contextWindow", contextWindow);
        map.put("maxTokens", maxTokens);
        map.put("temperature", temperature);
        map.put("memoryDir", memoryDir);
        map.put("sessionWindow", sessionWindow);
        map.put("sandboxWorkspace", sandboxWorkspace);
        map.put("enableNetwork", enableNetwork);
        map.put("toolResultRole", toolResultRole);
        map.put("maxIterations", maxIterations);
        map.put("toolTimeout", toolTimeout);
        map.put("systemPrompt", systemPrompt);
        return map;
    }

    public static class Builder {
        private String model = "claude-sonnet-4-6";
        private String apiKey = null;
        private String provider = "auto";
        private String baseUrl = null;
        private int contextWindow = 200000;
        private int maxTokens = 4096;
        private double temperature = 1.0;
        private String memoryDir = ".harness/memory";
        private String memoryMdPath = null;  // Path to MEMORY.md, defaults to ~/.harness/
        private int sessionWindow = 100;
        private String sandboxWorkspace = null;
        private boolean enableNetwork = false;
        private String toolResultRole = "tool"; // "tool" (native) or "user" (compatibility mode)
        private int maxIterations = 10;
        private double toolTimeout = 30.0;
        private String systemPrompt = "";
        private int maxDocumentSize = 10 * 1024 * 1024;  // 10MB
        private int maxTotalDocumentsSize = 20 * 1024 * 1024;  // 20MB
        private DocumentSizeAction documentSizeAction = DocumentSizeAction.WARN;
        private double documentTokenWarningRatio = 0.5;
        private SecurityConfig security = null;
        private CostControlConfig costControl = null;
        private ObservabilityConfig observability = null;
        private StorageConfig storage = null;
        private OffloadConfig offload = null;
        private RoutingConfig routing = null;

        public Builder model(String model) {
            this.model = model;
            return this;
        }

        public Builder apiKey(String apiKey) {
            this.apiKey = apiKey;
            return this;
        }

        public Builder provider(String provider) {
            this.provider = provider;
            return this;
        }

        public Builder baseUrl(String baseUrl) {
            this.baseUrl = baseUrl;
            return this;
        }

        public Builder contextWindow(int contextWindow) {
            this.contextWindow = contextWindow;
            return this;
        }

        public Builder maxTokens(int maxTokens) {
            this.maxTokens = maxTokens;
            return this;
        }

        public Builder temperature(double temperature) {
            this.temperature = temperature;
            return this;
        }

        public Builder memoryDir(String memoryDir) {
            this.memoryDir = memoryDir;
            return this;
        }

        public Builder memoryMdPath(String memoryMdPath) {
            this.memoryMdPath = memoryMdPath;
            return this;
        }

        public Builder sessionWindow(int sessionWindow) {
            this.sessionWindow = sessionWindow;
            return this;
        }

        public Builder sandboxWorkspace(String sandboxWorkspace) {
            this.sandboxWorkspace = sandboxWorkspace;
            return this;
        }

        public Builder enableNetwork(boolean enableNetwork) {
            this.enableNetwork = enableNetwork;
            return this;
        }

        public Builder toolResultRole(String toolResultRole) {
            this.toolResultRole = toolResultRole;
            return this;
        }

        public Builder maxIterations(int maxIterations) {
            this.maxIterations = maxIterations;
            return this;
        }

        public Builder toolTimeout(double toolTimeout) {
            this.toolTimeout = toolTimeout;
            return this;
        }

        public Builder systemPrompt(String systemPrompt) {
            this.systemPrompt = systemPrompt;
            return this;
        }

        public Builder maxDocumentSize(int maxDocumentSize) {
            this.maxDocumentSize = maxDocumentSize;
            return this;
        }

        public Builder maxTotalDocumentsSize(int maxTotalDocumentsSize) {
            this.maxTotalDocumentsSize = maxTotalDocumentsSize;
            return this;
        }

        public Builder documentSizeAction(DocumentSizeAction documentSizeAction) {
            this.documentSizeAction = documentSizeAction;
            return this;
        }

        public Builder documentTokenWarningRatio(double documentTokenWarningRatio) {
            this.documentTokenWarningRatio = documentTokenWarningRatio;
            return this;
        }

        public Builder security(SecurityConfig security) {
            this.security = security;
            return this;
        }

        public Builder costControl(CostControlConfig costControl) {
            this.costControl = costControl;
            return this;
        }

        public Builder observability(ObservabilityConfig observability) {
            this.observability = observability;
            return this;
        }

        public Builder storage(StorageConfig storage) {
            this.storage = storage;
            return this;
        }

        public Builder offload(OffloadConfig offload) {
            this.offload = offload;
            return this;
        }

        public Builder routing(RoutingConfig routing) {
            this.routing = routing;
            return this;
        }

        public HarnessConfig build() {
            return new HarnessConfig(this);
        }
    }

    // -------------------------------------------------------------------------
    // Sub-configuration classes
    // -------------------------------------------------------------------------

    /**
     * Security configuration.
     */
    public static class SecurityConfig {
        private final boolean enableInputValidation;
        private final int maxInputLength;
        private final boolean checkPromptInjection;
        private final boolean enableOutputSanitization;
        private final int maxOutputLength;
        private final boolean enableAuditLog;
        private final String auditLogDir;
        private final int auditRetentionDays;
        private final boolean enableSandbox;
        private final double sandboxMaxExecutionTime;
        private final int sandboxMaxOutputSize;
        private final List<String> sandboxBlockedCommands;
        private final List<String> sandboxBlockedPatterns;
        private final List<String> sandboxAllowedCommands;
        private final List<String> sandboxAllowedEnvVars;

        private SecurityConfig(Builder builder) {
            this.enableInputValidation = builder.enableInputValidation;
            this.maxInputLength = builder.maxInputLength;
            this.checkPromptInjection = builder.checkPromptInjection;
            this.enableOutputSanitization = builder.enableOutputSanitization;
            this.maxOutputLength = builder.maxOutputLength;
            this.enableAuditLog = builder.enableAuditLog;
            this.auditLogDir = builder.auditLogDir;
            this.auditRetentionDays = builder.auditRetentionDays;
            this.enableSandbox = builder.enableSandbox;
            this.sandboxMaxExecutionTime = builder.sandboxMaxExecutionTime;
            this.sandboxMaxOutputSize = builder.sandboxMaxOutputSize;
            this.sandboxBlockedCommands = List.copyOf(builder.sandboxBlockedCommands);
            this.sandboxBlockedPatterns = List.copyOf(builder.sandboxBlockedPatterns);
            this.sandboxAllowedCommands = builder.sandboxAllowedCommands != null
                ? List.copyOf(builder.sandboxAllowedCommands) : null;
            this.sandboxAllowedEnvVars = List.copyOf(builder.sandboxAllowedEnvVars);
        }

        public static Builder builder() { return new Builder(); }

        public boolean isEnableInputValidation() { return enableInputValidation; }
        public int getMaxInputLength() { return maxInputLength; }
        public boolean isCheckPromptInjection() { return checkPromptInjection; }
        public boolean isEnableOutputSanitization() { return enableOutputSanitization; }
        public int getMaxOutputLength() { return maxOutputLength; }
        public boolean isEnableAuditLog() { return enableAuditLog; }
        public String getAuditLogDir() { return auditLogDir; }
        public int getAuditRetentionDays() { return auditRetentionDays; }
        public boolean isEnableSandbox() { return enableSandbox; }
        public double getSandboxMaxExecutionTime() { return sandboxMaxExecutionTime; }
        public int getSandboxMaxOutputSize() { return sandboxMaxOutputSize; }
        public List<String> getSandboxBlockedCommands() { return sandboxBlockedCommands; }
        public List<String> getSandboxBlockedPatterns() { return sandboxBlockedPatterns; }
        public List<String> getSandboxAllowedCommands() { return sandboxAllowedCommands; }
        public List<String> getSandboxAllowedEnvVars() { return sandboxAllowedEnvVars; }

        public static class Builder {
            private boolean enableInputValidation = true;
            private int maxInputLength = 100000;
            private boolean checkPromptInjection = true;
            private boolean enableOutputSanitization = true;
            private int maxOutputLength = 100000;
            private boolean enableAuditLog = true;
            private String auditLogDir = "~/.harness/audit";
            private int auditRetentionDays = 30;
            private boolean enableSandbox = true;
            private double sandboxMaxExecutionTime = 30.0;
            private int sandboxMaxOutputSize = 1_000_000;
            private List<String> sandboxBlockedCommands = Arrays.asList(
                "rm -rf /",
                "rm -rf ~",
                "sudo",
                "chmod -R 777",
                "mkfs",
                "dd if=",
                "> /dev/",
                ":(){ :|:& };:"
            );
            private List<String> sandboxBlockedPatterns = Arrays.asList(
                "rm -rf",
                "sudo",
                "chmod",
                "chown",
                "mkfs",
                "dd if=",
                "curl | bash",
                "wget | bash"
            );
            private List<String> sandboxAllowedCommands = null;
            private List<String> sandboxAllowedEnvVars = Arrays.asList(
                "PATH",
                "HOME",
                "USER",
                "LANG",
                "LC_ALL",
                "TERM"
            );

            public Builder enableInputValidation(boolean v) { this.enableInputValidation = v; return this; }
            public Builder maxInputLength(int v) { this.maxInputLength = v; return this; }
            public Builder checkPromptInjection(boolean v) { this.checkPromptInjection = v; return this; }
            public Builder enableOutputSanitization(boolean v) { this.enableOutputSanitization = v; return this; }
            public Builder maxOutputLength(int v) { this.maxOutputLength = v; return this; }
            public Builder enableAuditLog(boolean v) { this.enableAuditLog = v; return this; }
            public Builder auditLogDir(String v) { this.auditLogDir = v; return this; }
            public Builder auditRetentionDays(int v) { this.auditRetentionDays = v; return this; }
            public Builder enableSandbox(boolean v) { this.enableSandbox = v; return this; }
            public Builder sandboxMaxExecutionTime(double v) { this.sandboxMaxExecutionTime = v; return this; }
            public Builder sandboxMaxOutputSize(int v) { this.sandboxMaxOutputSize = v; return this; }
            public Builder sandboxBlockedCommands(List<String> v) { this.sandboxBlockedCommands = v; return this; }
            public Builder sandboxBlockedPatterns(List<String> v) { this.sandboxBlockedPatterns = v; return this; }
            public Builder sandboxAllowedCommands(List<String> v) { this.sandboxAllowedCommands = v; return this; }
            public Builder sandboxAllowedEnvVars(List<String> v) { this.sandboxAllowedEnvVars = v; return this; }

            public SecurityConfig build() { return new SecurityConfig(this); }
        }
    }

    /**
     * Cost control configuration.
     */
    public static class CostControlConfig {
        private final int maxTokensPerSession;
        private final int maxToolCallsPerSession;
        private final int maxIterationsPerRequest;
        private final int dailyTokenLimit;
        private final int hourlyRequestLimit;
        private final double globalDailyBudgetUsd;
        private final boolean autoThrottle;
        private final String fallbackModel;
        private final double contextReductionRatio;
        private final double warningThreshold;

        private CostControlConfig(Builder builder) {
            this.maxTokensPerSession = builder.maxTokensPerSession;
            this.maxToolCallsPerSession = builder.maxToolCallsPerSession;
            this.maxIterationsPerRequest = builder.maxIterationsPerRequest;
            this.dailyTokenLimit = builder.dailyTokenLimit;
            this.hourlyRequestLimit = builder.hourlyRequestLimit;
            this.globalDailyBudgetUsd = builder.globalDailyBudgetUsd;
            this.autoThrottle = builder.autoThrottle;
            this.fallbackModel = builder.fallbackModel;
            this.contextReductionRatio = builder.contextReductionRatio;
            this.warningThreshold = builder.warningThreshold;
        }

        public static Builder builder() { return new Builder(); }

        public int getMaxTokensPerSession() { return maxTokensPerSession; }
        public int getMaxToolCallsPerSession() { return maxToolCallsPerSession; }
        public int getMaxIterationsPerRequest() { return maxIterationsPerRequest; }
        public int getDailyTokenLimit() { return dailyTokenLimit; }
        public int getHourlyRequestLimit() { return hourlyRequestLimit; }
        public double getGlobalDailyBudgetUsd() { return globalDailyBudgetUsd; }
        public boolean isAutoThrottle() { return autoThrottle; }
        public String getFallbackModel() { return fallbackModel; }
        public double getContextReductionRatio() { return contextReductionRatio; }
        public double getWarningThreshold() { return warningThreshold; }

        public static class Builder {
            private int maxTokensPerSession = 1_000_000;
            private int maxToolCallsPerSession = 500;
            private int maxIterationsPerRequest = 20;
            private int dailyTokenLimit = 10_000_000;
            private int hourlyRequestLimit = 100;
            private double globalDailyBudgetUsd = 100.0;
            private boolean autoThrottle = true;
            private String fallbackModel = null;
            private double contextReductionRatio = 0.5;
            private double warningThreshold = 0.8;

            public Builder maxTokensPerSession(int v) { this.maxTokensPerSession = v; return this; }
            public Builder maxToolCallsPerSession(int v) { this.maxToolCallsPerSession = v; return this; }
            public Builder maxIterationsPerRequest(int v) { this.maxIterationsPerRequest = v; return this; }
            public Builder dailyTokenLimit(int v) { this.dailyTokenLimit = v; return this; }
            public Builder hourlyRequestLimit(int v) { this.hourlyRequestLimit = v; return this; }
            public Builder globalDailyBudgetUsd(double v) { this.globalDailyBudgetUsd = v; return this; }
            public Builder autoThrottle(boolean v) { this.autoThrottle = v; return this; }
            public Builder fallbackModel(String v) { this.fallbackModel = v; return this; }
            public Builder contextReductionRatio(double v) { this.contextReductionRatio = v; return this; }
            public Builder warningThreshold(double v) { this.warningThreshold = v; return this; }

            public CostControlConfig build() { return new CostControlConfig(this); }
        }
    }

    /**
     * Observability configuration.
     */
    public static class ObservabilityConfig {
        private final boolean enabled;
        private final String serviceName;
        private final String serviceVersion;
        private final boolean exportConsole;
        private final boolean exportOtlp;
        private final String otlpEndpoint;
        private final double sampleRate;

        private ObservabilityConfig(Builder builder) {
            this.enabled = builder.enabled;
            this.serviceName = builder.serviceName;
            this.serviceVersion = builder.serviceVersion;
            this.exportConsole = builder.exportConsole;
            this.exportOtlp = builder.exportOtlp;
            this.otlpEndpoint = builder.otlpEndpoint;
            this.sampleRate = builder.sampleRate;
        }

        public static Builder builder() { return new Builder(); }

        public boolean isEnabled() { return enabled; }
        public String getServiceName() { return serviceName; }
        public String getServiceVersion() { return serviceVersion; }
        public boolean isExportConsole() { return exportConsole; }
        public boolean isExportOtlp() { return exportOtlp; }
        public String getOtlpEndpoint() { return otlpEndpoint; }
        public double getSampleRate() { return sampleRate; }

        public static class Builder {
            private boolean enabled = false;
            private String serviceName = "harness-agent";
            private String serviceVersion = "0.1.0";
            private boolean exportConsole = false;
            private boolean exportOtlp = false;
            private String otlpEndpoint = "http://localhost:4317";
            private double sampleRate = 1.0;

            public Builder enabled(boolean v) { this.enabled = v; return this; }
            public Builder serviceName(String v) { this.serviceName = v; return this; }
            public Builder serviceVersion(String v) { this.serviceVersion = v; return this; }
            public Builder exportConsole(boolean v) { this.exportConsole = v; return this; }
            public Builder exportOtlp(boolean v) { this.exportOtlp = v; return this; }
            public Builder otlpEndpoint(String v) { this.otlpEndpoint = v; return this; }
            public Builder sampleRate(double v) { this.sampleRate = v; return this; }

            public ObservabilityConfig build() { return new ObservabilityConfig(this); }
        }
    }

    /**
     * Storage configuration.
     */
    public static class StorageConfig {
        private final String type; // "file" or "sqlite"
        private final String storageDir;
        private final String sqlitePath;
        private final boolean asyncMode;
        private final int poolSize;

        private StorageConfig(Builder builder) {
            this.type = builder.type;
            this.storageDir = builder.storageDir;
            this.sqlitePath = builder.sqlitePath;
            this.asyncMode = builder.asyncMode;
            this.poolSize = builder.poolSize;
        }

        public static Builder builder() { return new Builder(); }

        public String getType() { return type; }
        public String getStorageDir() { return storageDir; }
        public String getSqlitePath() { return sqlitePath; }
        public boolean isAsyncMode() { return asyncMode; }
        public int getPoolSize() { return poolSize; }

        public static class Builder {
            private String type = "file";
            private String storageDir = ".harness/sessions";
            private String sqlitePath = ".harness/harness.db";
            private boolean asyncMode = true;
            private int poolSize = 5;

            public Builder type(String v) { this.type = v; return this; }
            public Builder storageDir(String v) { this.storageDir = v; return this; }
            public Builder sqlitePath(String v) { this.sqlitePath = v; return this; }
            public Builder asyncMode(boolean v) { this.asyncMode = v; return this; }
            public Builder poolSize(int v) { this.poolSize = v; return this; }

            public StorageConfig build() { return new StorageConfig(this); }
        }
    }

    /**
     * Routing configuration for LLM request routing.
     */
    public static class RoutingConfig {
        private final String highModel;
        private final String highProvider;
        private final String highApiKey;
        private final String highBaseUrl;
        private final String highDescription;
        private final String lowModel;
        private final String lowProvider;
        private final String lowApiKey;
        private final String lowBaseUrl;
        private final String lowDescription;
        private final String routerModelPath;
        private final String routerUrl;
        private final int routerContextWindow;
        private final String defaultRoute;
        private final double routerTimeout;
        private final int historyWindow;
        private final String routePromptTemplate;

        private RoutingConfig(Builder builder) {
            this.highModel = builder.highModel;
            this.highProvider = builder.highProvider;
            this.highApiKey = builder.highApiKey;
            this.highBaseUrl = builder.highBaseUrl;
            this.highDescription = builder.highDescription;
            this.lowModel = builder.lowModel;
            this.lowProvider = builder.lowProvider;
            this.lowApiKey = builder.lowApiKey;
            this.lowBaseUrl = builder.lowBaseUrl;
            this.lowDescription = builder.lowDescription;
            this.routerModelPath = builder.routerModelPath;
            this.routerUrl = builder.routerUrl;
            this.routerContextWindow = builder.routerContextWindow;
            this.defaultRoute = builder.defaultRoute;
            this.routerTimeout = builder.routerTimeout;
            this.historyWindow = builder.historyWindow;
            this.routePromptTemplate = builder.routePromptTemplate;
        }

        public static Builder builder() { return new Builder(); }

        public String getHighModel() { return highModel; }
        public String getHighProvider() { return highProvider; }
        public String getHighApiKey() { return highApiKey; }
        public String getHighBaseUrl() { return highBaseUrl; }
        public String getHighDescription() { return highDescription; }
        public String getLowModel() { return lowModel; }
        public String getLowProvider() { return lowProvider; }
        public String getLowApiKey() { return lowApiKey; }
        public String getLowBaseUrl() { return lowBaseUrl; }
        public String getLowDescription() { return lowDescription; }
        public String getRouterModelPath() { return routerModelPath; }
        public String getRouterUrl() { return routerUrl; }
        public int getRouterContextWindow() { return routerContextWindow; }
        public String getDefaultRoute() { return defaultRoute; }
        public double getRouterTimeout() { return routerTimeout; }
        public int getHistoryWindow() { return historyWindow; }
        public String getRoutePromptTemplate() { return routePromptTemplate; }

        public static class Builder {
            private String highModel = "";
            private String highProvider = "auto";
            private String highApiKey = null;
            private String highBaseUrl = null;
            private String highDescription = "高级模型，适合复杂任务";
            private String lowModel = "";
            private String lowProvider = "auto";
            private String lowApiKey = null;
            private String lowBaseUrl = null;
            private String lowDescription = "基础模型，适合简单任务";
            private String routerModelPath = null;
            private String routerUrl = null;
            private int routerContextWindow = 4096;
            private String defaultRoute = "high";
            private double routerTimeout = 0.2;
            private int historyWindow = 5;
            private String routePromptTemplate = null;

            public Builder highModel(String v) { this.highModel = v; return this; }
            public Builder highProvider(String v) { this.highProvider = v; return this; }
            public Builder highApiKey(String v) { this.highApiKey = v; return this; }
            public Builder highBaseUrl(String v) { this.highBaseUrl = v; return this; }
            public Builder highDescription(String v) { this.highDescription = v; return this; }
            public Builder lowModel(String v) { this.lowModel = v; return this; }
            public Builder lowProvider(String v) { this.lowProvider = v; return this; }
            public Builder lowApiKey(String v) { this.lowApiKey = v; return this; }
            public Builder lowBaseUrl(String v) { this.lowBaseUrl = v; return this; }
            public Builder lowDescription(String v) { this.lowDescription = v; return this; }
            public Builder routerModelPath(String v) { this.routerModelPath = v; return this; }
            public Builder routerUrl(String v) { this.routerUrl = v; return this; }
            public Builder routerContextWindow(int v) { this.routerContextWindow = v; return this; }
            public Builder defaultRoute(String v) { this.defaultRoute = v; return this; }
            public Builder routerTimeout(double v) { this.routerTimeout = v; return this; }
            public Builder historyWindow(int v) { this.historyWindow = v; return this; }
            public Builder routePromptTemplate(String v) { this.routePromptTemplate = v; return this; }

            public RoutingConfig build() { return new RoutingConfig(this); }
        }
    }
}
