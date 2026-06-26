# 05 - 记忆系统 (Java 实现)

## 概述

记忆系统允许 Agent 跨会话保持上下文，是实现长期记忆的关键组件。本文档详细说明 Java 版本的记忆系统设计。

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                      Memory System                          │
│                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐  │
│  │   MEMORY.md │ ←── │   Memory    │ ←── │   Session   │  │
│  │   (文件)     │     │   Manager   │     │   Manager   │  │
│  └─────────────┘     └──────┬──────┘     └─────────────┘  │
│                             │                               │
│                             ↓                               │
│                    ┌────────────────┐                       │
│                    │ ContextBuilder │                       │
│                    │   (上下文构建)   │                       │
│                    └────────┬───────┘                       │
│                             │                               │
│         ┌───────────────────┼───────────────────┐          │
│         ↓                   ↓                   ↓          │
│  ┌────────────┐     ┌────────────┐     ┌────────────┐     │
│  │   Token    │     │   Memory   │     │  Working   │     │
│  │   Counter  │     │   Types    │     │  Memory    │     │
│  └────────────┘     └────────────┘     └────────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 核心类设计

### MemoryManager

```java
package com.harness.memory;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * 记忆管理器 - 管理持久化记忆。
 */
public class MemoryManager {

    private final Path memoryDir;
    private final Path memoryMdPath;
    private final TokenCounter tokenCounter;
    private MemoryIndex index;

    public MemoryManager(Path memoryDir, Path memoryMdPath) {
        this.memoryDir = memoryDir;
        this.memoryMdPath = memoryMdPath;
        this.tokenCounter = new TokenCounter();
        this.index = new MemoryIndex();

        // 确保目录存在
        try {
            Files.createDirectories(memoryDir);
        } catch (IOException e) {
            throw new RuntimeException("无法创建记忆目录: " + memoryDir, e);
        }

        // 加载现有记忆
        loadMemories();
    }

    /**
     * 添加用户记忆。
     */
    public void addUserMemory(String name, String description, String type, String content) {
        Memory memory = Memory.builder()
            .name(name)
            .description(description)
            .type(MemoryType.valueOf(type.toUpperCase()))
            .content(content)
            .createdAt(Instant.now())
            .build();

        index.addMemory(memory);
        saveMemory(memory);
        updateMemoryMd();
    }

    /**
     * 添加反馈记忆。
     */
    public void addFeedbackMemory(String name, String description, String content) {
        addUserMemory(name, description, "FEEDBACK", content);
    }

    /**
     * 添加项目记忆。
     */
    public void addProjectMemory(String name, String description, String content) {
        addUserMemory(name, description, "PROJECT", content);
    }

    /**
     * 添加引用记忆。
     */
    public void addReferenceMemory(String name, String description, String content) {
        addUserMemory(name, description, "REFERENCE", content);
    }

    /**
     * 获取所有记忆。
     */
    public List<Memory> getAllMemories() {
        return index.getMemories();
    }

    /**
     * 按类型获取记忆。
     */
    public List<Memory> getMemoriesByType(MemoryType type) {
        return index.getMemories().stream()
            .filter(m -> m.type() == type)
            .toList();
    }

    /**
     * 搜索记忆。
     */
    public List<Memory> searchMemories(String query) {
        String lowerQuery = query.toLowerCase();
        return index.getMemories().stream()
            .filter(m -> m.name().toLowerCase().contains(lowerQuery) ||
                        m.description().toLowerCase().contains(lowerQuery) ||
                        m.content().toLowerCase().contains(lowerQuery))
            .toList();
    }

    /**
     * 更新记忆。
     */
    public void updateMemory(String name, String newContent) {
        Optional<Memory> existing = index.getMemory(name);
        if (existing.isPresent()) {
            Memory updated = existing.get().withContent(newContent);
            index.updateMemory(updated);
            saveMemory(updated);
            updateMemoryMd();
        }
    }

    /**
     * 删除记忆。
     */
    public void deleteMemory(String name) {
        index.removeMemory(name);
        deleteMemoryFile(name);
        updateMemoryMd();
    }

    /**
     * 构建系统提示词中的记忆部分。
     */
    public String buildMemoryPrompt() {
        StringBuilder sb = new StringBuilder();

        List<Memory> memories = index.getMemories();
        if (memories.isEmpty()) {
            return "";
        }

        sb.append("## 记忆\n\n");
        sb.append("以下是跨会话持久化的记忆信息：\n\n");

        // 按类型分组
        Map<MemoryType, List<Memory>> grouped = memories.stream()
            .collect(Collectors.groupingBy(Memory::type));

        for (Map.Entry<MemoryType, List<Memory>> entry : grouped.entrySet()) {
            sb.append("### ").append(entry.getKey().getDisplayName()).append("\n\n");

            for (Memory memory : entry.getValue()) {
                sb.append("#### ").append(memory.name()).append("\n");
                sb.append(memory.description()).append("\n\n");
                sb.append(memory.content()).append("\n\n");
            }
        }

        return sb.toString();
    }

    /**
     * 估算记忆的 Token 数量。
     */
    public int estimateTokens() {
        return tokenCounter.count(buildMemoryPrompt());
    }

    // 私有方法
    private void loadMemories() {
        try {
            if (Files.exists(memoryMdPath)) {
                String content = Files.readString(memoryMdPath);
                index = MemoryParser.parse(content);
            }
        } catch (IOException e) {
            // 忽略，使用空索引
        }
    }

    private void saveMemory(Memory memory) {
        Path filePath = memoryDir.resolve(memory.name() + ".md");
        try {
            Files.writeString(filePath, formatMemoryFile(memory));
        } catch (IOException e) {
            throw new RuntimeException("无法保存记忆: " + memory.name(), e);
        }
    }

    private void updateMemoryMd() {
        try {
            String content = formatMemoryMd();
            Files.writeString(memoryMdPath, content);
        } catch (IOException e) {
            throw new RuntimeException("无法更新 MEMORY.md", e);
        }
    }

    private String formatMemoryFile(Memory memory) {
        return String.format("""
            ---
            name: %s
            description: %s
            type: %s
            created_at: %s
            ---

            %s
            """,
            memory.name(),
            memory.description(),
            memory.type().name(),
            memory.createdAt(),
            memory.content()
        );
    }

    private String formatMemoryMd() {
        StringBuilder sb = new StringBuilder();
        sb.append("# Memory Index\n\n");

        for (Memory memory : index.getMemories()) {
            sb.append("- [").append(memory.name()).append("](")
              .append(memory.name()).append(".md) — ")
              .append(memory.description()).append("\n");
        }

        return sb.toString();
    }
}
```

### Memory 类型

```java
package com.harness.memory;

/**
 * 记忆类型枚举。
 */
public enum MemoryType {
    USER("用户信息"),
    FEEDBACK("反馈指导"),
    PROJECT("项目信息"),
    REFERENCE("引用资源");

    private final String displayName;

    MemoryType(String displayName) {
        this.displayName = displayName;
    }

    public String getDisplayName() {
        return displayName;
    }
}

/**
 * 记忆实体。
 */
public record Memory(
    String name,
    String description,
    MemoryType type,
    String content,
    Instant createdAt,
    Instant updatedAt
) {

    public static Builder builder() {
        return new Builder();
    }

    public Memory withContent(String newContent) {
        return new Memory(name, description, type, newContent, createdAt, Instant.now());
    }

    public static class Builder {
        private String name;
        private String description;
        private MemoryType type;
        private String content;
        private Instant createdAt;
        private Instant updatedAt;

        public Builder name(String name) { this.name = name; return this; }
        public Builder description(String description) { this.description = description; return this; }
        public Builder type(MemoryType type) { this.type = type; return this; }
        public Builder content(String content) { this.content = content; return this; }
        public Builder createdAt(Instant createdAt) { this.createdAt = createdAt; return this; }
        public Builder updatedAt(Instant updatedAt) { this.updatedAt = updatedAt; return this; }

        public Memory build() {
            return new Memory(name, description, type, content, createdAt, updatedAt);
        }
    }
}
```

### Token 计数器

```java
package com.harness.memory;

import com.knuddelsgmbh.jtokkit.Encodings;
import com.knuddelsgmbh.jtokkit.api.Encoding;
import com.knuddelsgmbh.jtokkit.api.EncodingType;

import java.util.concurrent.TimeUnit;

import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;

/**
 * Token 计数器 - 使用 jtokkit 库。
 */
public class TokenCounter {

    private final Encoding encoding;
    private final Cache<String, Integer> cache;

    public TokenCounter() {
        // Claude 使用 cl100k_base 编码（与 GPT-4 相同）
        this.encoding = Encodings.newDefaultEncodingRegistry()
            .getEncoding(EncodingType.CL100K_BASE);

        // 缓存计数结果
        this.cache = Caffeine.newBuilder()
            .maximumSize(10000)
            .expireAfterAccess(10, TimeUnit.MINUTES)
            .build();
    }

    /**
     * 计算文本的 Token 数量。
     */
    public int count(String text) {
        if (text == null || text.isEmpty()) {
            return 0;
        }

        return cache.get(text, t -> encoding.encode(t).size());
    }

    /**
     * 批量计算。
     */
    public int countAll(List<String> texts) {
        return texts.stream()
            .mapToInt(this::count)
            .sum();
    }

    /**
     * 清除缓存。
     */
    public void clearCache() {
        cache.invalidateAll();
    }
}
```

### 上下文构建器

```java
package com.harness.memory;

import java.util.ArrayList;
import java.util.List;

/**
 * 上下文构建器 - 构建发送给 LLM 的完整上下文。
 */
public class ContextBuilder {

    private final MemoryManager memoryManager;
    private final TokenCounter tokenCounter;
    private final int contextWindow;
    private final int maxMemoryTokens;

    public ContextBuilder(MemoryManager memoryManager, int contextWindow, double memoryRatio) {
        this.memoryManager = memoryManager;
        this.tokenCounter = new TokenCounter();
        this.contextWindow = contextWindow;
        this.maxMemoryTokens = (int) (contextWindow * memoryRatio);
    }

    /**
     * 构建完整的上下文。
     */
    public Context build(Session session) {
        List<Message> messages = new ArrayList<>();

        // 1. 添加系统提示词
        String systemPrompt = buildSystemPrompt(session);
        messages.add(Message.system(systemPrompt));

        // 2. 添加历史消息（在 Token 预算内）
        List<Message> history = truncateHistory(session.messages());
        messages.addAll(history);

        // 3. 计算 Token 使用量
        int totalTokens = tokenCounter.countAll(
            messages.stream().map(Message::content).toList()
        );

        return new Context(messages, totalTokens, contextWindow - totalTokens);
    }

    /**
     * 构建系统提示词。
     */
    private String buildSystemPrompt(Session session) {
        StringBuilder sb = new StringBuilder();

        // 基础系统提示
        sb.append(session.systemPrompt()).append("\n\n");

        // 添加记忆
        String memoryPrompt = memoryManager.buildMemoryPrompt();
        if (!memoryPrompt.isEmpty()) {
            sb.append(memoryPrompt).append("\n");
        }

        // 添加工作目录信息
        sb.append("工作目录: ").append(session.workingDirectory()).append("\n");

        return sb.toString();
    }

    /**
     * 截断历史消息以适应 Token 预算。
     */
    private List<Message> truncateHistory(List<Message> messages) {
        int availableTokens = contextWindow - maxMemoryTokens;

        List<Message> result = new ArrayList<>();
        int currentTokens = 0;

        // 从最新消息开始添加
        for (int i = messages.size() - 1; i >= 0; i--) {
            Message msg = messages.get(i);
            int msgTokens = tokenCounter.count(msg.content());

            if (currentTokens + msgTokens > availableTokens) {
                // 如果超出预算，添加截断提示
                if (i > 0) {
                    result.add(0, Message.system(
                        String.format("... 已省略 %d 条历史消息 ...", i)
                    ));
                }
                break;
            }

            result.add(0, msg);
            currentTokens += msgTokens;
        }

        return result;
    }
}

/**
 * 上下文结果。
 */
public record Context(
    List<Message> messages,
    int usedTokens,
    int remainingTokens
) {
    public boolean isNearLimit() {
        return remainingTokens < 1000;
    }
}
```

## 工作记忆

```java
package com.harness.memory;

/**
 * 工作记忆 - 会话内的临时记忆。
 */
public class WorkingMemory {

    private final Map<String, Object> data;
    private final List<String> recentActions;
    private final int maxActions;

    public WorkingMemory(int maxActions) {
        this.data = new ConcurrentHashMap<>();
        this.recentActions = new ArrayList<>();
        this.maxActions = maxActions;
    }

    /**
     * 存储数据。
     */
    public void put(String key, Object value) {
        data.put(key, value);
    }

    /**
     * 获取数据。
     */
    @SuppressWarnings("unchecked")
    public <T> T get(String key) {
        return (T) data.get(key);
    }

    /**
     * 记录动作。
     */
    public void recordAction(String action) {
        recentActions.add(action);
        if (recentActions.size() > maxActions) {
            recentActions.remove(0);
        }
    }

    /**
     * 获取最近的动作。
     */
    public List<String> getRecentActions() {
        return new ArrayList<>(recentActions);
    }

    /**
     * 清除工作记忆。
     */
    public void clear() {
        data.clear();
        recentActions.clear();
    }

    /**
     * 构建工作记忆摘要。
     */
    public String buildSummary() {
        StringBuilder sb = new StringBuilder();

        if (!recentActions.isEmpty()) {
            sb.append("最近的操作:\n");
            for (String action : recentActions) {
                sb.append("- ").append(action).append("\n");
            }
        }

        if (!data.isEmpty()) {
            sb.append("\n已记录的数据:\n");
            for (Map.Entry<String, Object> entry : data.entrySet()) {
                sb.append("- ").append(entry.getKey()).append("\n");
            }
        }

        return sb.toString();
    }
}
```

## 记忆文件格式

### MEMORY.md 格式

```markdown
# Memory Index

- [user_role](user_role.md) — 用户角色和偏好
- [project_structure](project_structure.md) — 项目结构说明
- [coding_style](coding_style.md) — 编码风格偏好
```

### 单个记忆文件格式

```markdown
---
name: user_role
description: 用户角色和偏好
type: USER
created_at: 2026-06-17T10:00:00Z
---

用户是一名高级 Java 开发工程师，专注于银行系统开发。

偏好：
- 使用 Java 17 特性
- 遵循阿里巴巴 Java 编码规范
- 偏好函数式编程风格
```

## 使用示例

### 初始化记忆系统

```java
import com.harness.memory.MemoryManager;
import com.harness.memory.ContextBuilder;
import java.nio.file.Path;

// 创建记忆管理器
Path memoryDir = Path.of(System.getProperty("user.home"), ".harness");
Path memoryMdPath = memoryDir.resolve("MEMORY.md");

MemoryManager memoryManager = new MemoryManager(memoryDir, memoryMdPath);

// 添加记忆
memoryManager.addUserMemory(
    "user_role",
    "用户角色和偏好",
    "USER",
    "用户是一名高级 Java 开发工程师，专注于银行系统开发。"
);

memoryManager.addFeedbackMemory(
    "code_review",
    "代码审查反馈",
    "避免使用过时的 API，优先使用 Java 17 新特性。"
);
```

### 集成到 Agent

```java
import com.harness.Harness;
import com.harness.HarnessConfig;

HarnessConfig config = HarnessConfig.builder()
    .model("claude-sonnet-4-6")
    .apiKey(System.getenv("ANTHROPIC_API_KEY"))
    .memoryDir(memoryDir.toString())
    .memoryMdPath(memoryMdPath.toString())
    .contextWindow(200000)
    .build();

Harness agent = new Harness(config);

// Agent 会自动加载记忆并注入到上下文中
LoopResult result = agent.run("帮我优化这个方法");
```

### 动态更新记忆

```java
// 在 Agent 执行过程中更新记忆
agent.addHook(new LifecycleHook() {
    @Override
    public Set<HookPoint> hookPoints() {
        return Set.of(HookPoint.ON_LOOP_END);
    }

    @Override
    public CompletableFuture<HookResult> execute(HookContext ctx) {
        // 检查是否需要更新记忆
        if (ctx.session().metadata().containsKey("new_learning")) {
            String learning = ctx.session().metadata().get("new_learning").toString();
            memoryManager.addFeedbackMemory(
                "auto_learning_" + System.currentTimeMillis(),
                "自动学习",
                learning
            );
        }
        return CompletableFuture.completedFuture(HookResult.continue_());
    }
});
```

## 性能优化

### 1. Token 计数缓存

```java
// 使用 Caffeine 缓存
Cache<String, Integer> cache = Caffeine.newBuilder()
    .maximumSize(10000)
    .expireAfterAccess(10, TimeUnit.MINUTES)
    .recordStats()  // 记录统计信息
    .build();
```

### 2. 增量更新

```java
public class IncrementalMemoryUpdater {
    private final MemoryManager memoryManager;
    private final Queue<MemoryUpdate> pendingUpdates = new ConcurrentLinkedQueue<>();

    public void queueUpdate(MemoryUpdate update) {
        pendingUpdates.offer(update);
    }

    public void flush() {
        List<MemoryUpdate> batch = new ArrayList<>();
        MemoryUpdate update;
        while ((update = pendingUpdates.poll()) != null) {
            batch.add(update);
        }

        if (!batch.isEmpty()) {
            memoryManager.batchUpdate(batch);
        }
    }
}
```

### 3. 异步持久化

```java
public class AsyncMemoryPersister {
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final MemoryManager memoryManager;

    public CompletableFuture<Void> saveAsync(Memory memory) {
        return CompletableFuture.runAsync(
            () -> memoryManager.addMemory(memory),
            executor
        );
    }
}
```

## UpdateCoreMemoryTool

允许 Agent 自主更新 Core Memory 的工具，遵循 Mem0 模式。

### 使用方式

```java
import com.harness.Harness;
import com.harness.HarnessConfig;
import com.harness.tools.UpdateCoreMemoryTool;

HarnessConfig config = HarnessConfig.builder()
    .model("claude-sonnet-4-6")
    .apiKey(System.getenv("ANTHROPIC_API_KEY"))
    .build();

Harness agent = new Harness(config);

// 添加 UpdateCoreMemoryTool 到工具列表
agent.addTool(new UpdateCoreMemoryTool());

// Agent 现在可以自主更新记忆
LoopResult result = agent.run("我使用 Windows 系统");
```

### 工具描述（引导内容提炼）

工具的 description 引导 Agent 提炼用户原话，而不是直接存储：

```
更新用户偏好或项目约定到长期记忆。

重要规则：
1. **提炼内容**：不要存储用户原话，要提炼成简洁的陈述
   - 用户说「使用 cmd，不要用 powershell」→ 存储「Shell：使用 cmd（不使用 PowerShell）」
   - 用户说「我使用 Windows」→ 存储「操作系统：Windows」
2. **避免重复**：添加前先检查是否已有类似记忆，如有则不要重复添加
3. **适用场景**：用户提到长期偏好、工作环境、项目约束等
```

### Input Schema

```java
Map<String, Object> inputSchema() {
    return Map.of(
        "type", "object",
        "properties", Map.of(
            "category", Map.of(
                "type", "string",
                "enum", List.of("user_profile", "key_decisions", "learned_patterns", "project_context"),
                "description", "记忆类别"
            ),
            "content", Map.of(
                "type", "string",
                "description", "记忆内容"
            ),
            "action", Map.of(
                "type", "string",
                "enum", List.of("add", "remove"),
                "description", "操作类型"
            )
        ),
        "required", List.of("category", "content", "action")
    );
}
```

### Metadata 支持

ToolResult 包含 `metadata` 字段，用于传递 UI 刷新信号：

```java
// 添加成功时返回 refresh_memory 信号
return ToolResult.success(
    "",
    "已添加到 user_profile: 操作系统：Windows",
    name(),
    Map.of("refresh_memory", true)  // UI 刷新信号
);
```

## 记忆去重机制

MemoryFileManager 使用字符级 Jaccard 相似度检测重复记忆，支持中英文混合文本。

### 去重算法

```java
/**
 * Calculate text similarity using character-level Jaccard similarity.
 * Supports both Chinese and English text without requiring word segmentation.
 */
private double calculateSimilarity(String text1, String text2) {
    text1 = text1.toLowerCase();
    text2 = text2.toLowerCase();

    if (text1.isEmpty() || text2.isEmpty()) {
        return 0.0;
    }

    // 字符级 bigram（支持中文，无需分词）
    Set<String> ngrams1 = getNgrams(text1, 2);
    Set<String> ngrams2 = getNgrams(text2, 2);

    Set<String> intersection = new HashSet<>(ngrams1);
    intersection.retainAll(ngrams2);

    Set<String> union = new HashSet<>(ngrams1);
    union.addAll(ngrams2);

    return (double) intersection.size() / union.size();
}

private Set<String> getNgrams(String text, int n) {
    if (text.length() < n) {
        return Set.of(text);
    }
    Set<String> ngrams = new HashSet<>();
    for (int i = 0; i <= text.length() - n; i++) {
        ngrams.add(text.substring(i, i + n));
    }
    return ngrams;
}
```

### 使用示例

```java
MemoryFileManager manager = new MemoryFileManager();

// 添加第一条记忆
MemoryEntry entry1 = new MemoryEntry(
    MemoryCategory.USER_PROFILE,
    "操作系统：Windows",
    MemorySource.USER_INPUT
);
boolean added1 = manager.addEntry(entry1);  // 返回 true

// 尝试添加相似记忆
MemoryEntry entry2 = new MemoryEntry(
    MemoryCategory.USER_PROFILE,
    "操作系统：Windows 10",  // 相似内容
    MemorySource.USER_INPUT
);
boolean added2 = manager.addEntry(entry2);  // 返回 false（跳过重复）

// 添加不同记忆
MemoryEntry entry3 = new MemoryEntry(
    MemoryCategory.USER_PROFILE,
    "主题偏好：深色",
    MemorySource.USER_INPUT
);
boolean added3 = manager.addEntry(entry3);  // 返回 true
```

### 相似度阈值

- 默认阈值：`0.7`（70% 相似度）
- 阈值越高，去重越严格
- 可通过 `addEntry(entry, false)` 跳过去重检查

## MemoryCategory 扩展

### getValue() 和 fromValue()

支持小写字符串格式，与 Python SDK 保持一致：

```java
public enum MemoryCategory {
    USER_PROFILE("User Profile", "user_profile"),
    KEY_DECISIONS("Key Decisions", "key_decisions"),
    LEARNED_PATTERNS("Learned Patterns", "learned_patterns"),
    PROJECT_CONTEXT("Project Context", "project_context");

    private final String header;
    private final String value;

    public String getValue() {
        return value;  // 返回 "user_profile" 等小写格式
    }

    public static MemoryCategory fromValue(String value) {
        for (MemoryCategory cat : values()) {
            if (cat.value.equals(value)) {
                return cat;
            }
        }
        return PROJECT_CONTEXT;
    }
}
```

## SessionStore 接口

### 概述

SessionStore 提供会话持久化能力，支持跨应用重启恢复会话状态。

### 接口定义

```java
package com.harness.memory;

/**
 * Session storage interface.
 */
public interface SessionStore {

    /**
     * Save a session.
     */
    void save(Session session);

    /**
     * Load a session by ID.
     */
    Optional<Session> load(String sessionId);

    /**
     * Delete a session.
     */
    void delete(String sessionId);

    /**
     * Check if a session exists.
     */
    default boolean exists(String sessionId) {
        return load(sessionId).isPresent();
    }

    /**
     * List all session IDs.
     */
    List<String> listSessions();

    /**
     * Delete all sessions.
     */
    void deleteAll();
}
```

### FileSessionStore

JSON 文件存储实现：

```java
import com.harness.memory.FileSessionStore;

// 创建文件存储
Path storageDir = Path.of(System.getProperty("user.home"), ".harness", "sessions");
SessionStore store = new FileSessionStore(storageDir);

// 保存会话
Session session = Session.builder()
    .id("session-123")
    .messages(messages)
    .build();
store.save(session);

// 加载会话
Optional<Session> loaded = store.load("session-123");

// 列出所有会话
List<String> sessionIds = store.listSessions();

// 删除会话
store.delete("session-123");
```

**文件格式**：每个会话存储为独立的 JSON 文件 `{sessionId}.json`

### SQLiteSessionStore

SQLite 数据库存储实现：

```java
import com.harness.memory.SQLiteSessionStore;

// 创建 SQLite 存储
Path dbPath = Path.of(System.getProperty("user.home"), ".harness", "sessions.db");
SessionStore store = new SQLiteSessionStore(dbPath);

// 使用方式与 FileSessionStore 相同
store.save(session);
Optional<Session> loaded = store.load("session-123");
```

**特性**：
- 单文件数据库，便于备份
- 支持事务操作
- 自动创建表结构
- 更高效的查询性能

### 集成到 Agent

```java
import com.harness.Harness;
import com.harness.HarnessConfig;
import com.harness.memory.FileSessionStore;

// 创建会话存储
SessionStore sessionStore = new FileSessionStore(Path.of(".harness/sessions"));

// 配置 Agent
HarnessConfig config = HarnessConfig.builder()
    .model("claude-sonnet-4-6")
    .apiKey(System.getenv("ANTHROPIC_API_KEY"))
    .sessionStore(sessionStore)
    .build();

Harness agent = new Harness(config);

// 恢复之前的会话
Optional<Session> previousSession = sessionStore.load("session-123");
if (previousSession.isPresent()) {
    agent.resume(previousSession.get());
}

// 运行 Agent（会话会自动保存）
LoopResult result = agent.run("继续之前的工作");
```

## 下一步

- [06-mcp-integration.md](./06-mcp-integration.md) - 了解 MCP 集成
- [07-sdk-api.md](./07-sdk-api.md) - 查看完整 API 参考
