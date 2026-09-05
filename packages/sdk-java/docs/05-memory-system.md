# 04 - 记忆系统详解

## 概述

记忆系统解决 LLM 无状态问题，提供跨会话的持久化和上下文管理。Harness 的记忆系统包含四层记忆架构、MEMORY.md 标准格式、向量检索和动态系统提示组装。

## 四层记忆架构

```
┌─────────────────────────────────────────────────┐
│ Layer 1: Working Memory（工作记忆）              │
│ - 当前会话消息列表                               │
│ - 当前任务状态                                   │
│ - 临时变量和上下文                               │
├─────────────────────────────────────────────────┤
│ Layer 2: Session Memory（会话记忆）              │
│ - 会话摘要                                       │
│ - 关键决策记录                                   │
│ - 用户偏好                                       │
├─────────────────────────────────────────────────┤
│ Layer 3: Long-term Memory（长期记忆）            │
│ - MEMORY.md 持久记忆文件                         │
│ - 技能和模式                                     │
│ - 项目知识                                       │
│ - 历史经验                                       │
├─────────────────────────────────────────────────┤
│ Layer 4: Retrieved Memory（检索记忆）            │
│ - 向量语义搜索                                   │
│ - 历史对话检索                                   │
│ - 技能/文档检索                                  │
│ - 按需加载                                       │
└─────────────────────────────────────────────────┘
```


## MEMORY.md 标准

MEMORY.md 是 Harness 的持久记忆文件格式，用于跨会话保存重要信息。它采用分章节的 Markdown 格式，便于人工阅读和编辑。

### 文件格式

```markdown
# MEMORY.md

## User Profile
- Role: Software Developer
- Preferred Language: Python

## Key Decisions
- 2024-01-15: Chose SQLite for session storage due to its simplicity and performance
- 2024-01-16: Use qasync for PyQt integration instead of QThread

## Learned Patterns
- User prefers detailed explanations with code examples
- Avoid mocking database in integration tests

## Project Context
- This project uses Python 3.11+ with async/await patterns
- Code style follows Black formatting with 88 character line length
```

### 记忆类别

Harness 定义了四种记忆类别，每种对应一个专门的章节：

| 类别 | 章节标题 | 说明 | 示例 |
|------|----------|------|------|
| `USER_PROFILE` | User Profile | 用户角色、偏好、技能 | 用户是后端工程师，偏好 Python |
| `KEY_DECISIONS` | Key Decisions | 重要技术决策，带时间戳 | 2024-01-15: 选择 SQLite 作为会话存储 |
| `LEARNED_PATTERNS` | Learned Patterns | Agent 学习到的用户模式 | 用户喜欢详细的代码示例 |
| `PROJECT_CONTEXT` | Project Context | 项目特定约定和配置 | 代码遵循 Black 格式化，行宽 88 字符 |



### 核心类型

```java
// 核心类型
import com.harness.memory.MemoryEntry;
import com.harness.memory.MemoryCategory;
import com.harness.memory.MemorySource;
import com.harness.memory.MemorySections;
import com.harness.memory.MemoryFileManager;
import java.nio.file.Path;
import java.time.Instant;
import java.util.Map;

// MemoryEntry - 单个记忆条目
MemoryEntry entry = MemoryEntry.builder()
    .category(MemoryCategory.KEY_DECISIONS)
    .content("Chose SQLite for session storage")
    .source(MemorySource.AGENT_OBSERVATION)
    .createdAt(Instant.now())        // 自动设置创建时间
    .metadata(Map.of("session_id", "abc123"))  // 可选元数据
    .build();

// MemorySections - 所有记忆章节
MemorySections sections = new MemorySections();
sections.getUserProfile().add("Role: Software Developer");
sections.getUserProfile().add("Preferred Language: Python");
sections.getKeyDecisions().add("2024-01-15: Chose SQLite for session storage");
sections.getLearnedPatterns().add("User prefers detailed explanations");
sections.getProjectContext().add("Project uses Python 3.11+");

// MemoryFileManager - 管理 MEMORY.md 文件
MemoryFileManager manager = new MemoryFileManager(Path.of("."));
```

### 使用方式

```java
// 使用方式
import com.harness.memory.MemoryFileManager;
import com.harness.memory.MemoryEntry;
import com.harness.memory.MemoryCategory;
import com.harness.memory.MemorySource;
import com.harness.memory.MemorySections;
import java.nio.file.Path;
import java.time.Instant;

// 初始化管理器
MemoryFileManager manager = new MemoryFileManager(Path.of("/path/to/project"));

// 检查是否存在 MEMORY.md
if (manager.exists()) {
    // 加载现有记忆
    MemorySections sections = manager.load();

    // 访问特定章节
    for (String pattern : sections.getLearnedPatterns()) {
        System.out.println("学习到的模式: " + pattern);
    }
} else {
    // 创建默认记忆文件
    MemoryFileManager.createDefault(Path.of("/path/to/project"));
}

// 添加新条目
MemoryEntry newEntry = MemoryEntry.builder()
    .category(MemoryCategory.KEY_DECISIONS)
    .content("Use qasync for PyQt integration")
    .source(MemorySource.AGENT_OBSERVATION)
    .createdAt(Instant.now())
    .metadata(Map.of("source", "agent_observation"))
    .build();
manager.addEntry(newEntry);

// 获取所有条目
java.util.List<MemoryEntry> keyDecisions = manager.getEntries(MemoryCategory.KEY_DECISIONS);
for (int i = 0; i < keyDecisions.size(); i++) {
    System.out.println("决策 " + i + ": " + keyDecisions.get(i));
}

// 格式化为 LLM 上下文字符串
String contextString = manager.toContextString();
System.out.println("上下文长度: " + contextString.length() + " 字符");

// 删除条目
manager.removeEntry(MemoryCategory.KEY_DECISIONS, 0);

// 清空所有记忆
manager.clear();
```

## VectorMemoryStore（向量检索）

向量检索提供语义搜索能力，可以搜索历史对话、技能和文档。这是一个可选功能，需要安装额外依赖：`pip install harness-sdk[vector]`。

### 核心协议

```java
// 核心协议（Java 中使用接口）
import com.harness.memory.VectorMemoryStore;
import com.harness.memory.VectorSearchResult;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

// VectorMemoryStore 接口（Java SDK 已实现）
public interface VectorMemoryStore {
    CompletableFuture<Void> add(String id, String content, Map<String, Object> metadata);
    CompletableFuture<Void> addBatch(List<String> ids, List<String> contents,
        List<Map<String, Object>> metadatas);
    CompletableFuture<List<VectorSearchResult>> search(String query, int topK,
        Map<String, Object> filter);
    CompletableFuture<Void> delete(List<String> ids);
    CompletableFuture<Void> clear();
    CompletableFuture<Void> addConversation(String sessionId,
        List<Map<String, Object>> messages);
    CompletableFuture<List<VectorSearchResult>> searchConversations(String query,
        String sessionId, int topK);
    CompletableFuture<Void> addSkill(String skillName, String content,
        Map<String, Object> metadata);
    CompletableFuture<List<VectorSearchResult>> searchSkills(String query, int topK);
}
```

### VectorMemoryConfig

```java
// VectorMemoryConfig（Java SDK 已在 VectorMemoryConfig.java 中定义）
import com.harness.memory.VectorMemoryConfig;
import java.nio.file.Path;

VectorMemoryConfig config = VectorMemoryConfig.builder()
    .embeddingModel("mock")          // "mock", "openai", "sentence-transformers"
    .persistDir(null)                // 持久化目录
    .collectionName("harness_memory") // 集合名称
    .embeddingDimension(384)         // 嵌入维度
    .build();
```

### VectorSearchResult

```java
// VectorSearchResult（Java SDK 已在 VectorSearchResult.java 中定义）
import com.harness.memory.VectorSearchResult;

// Java VectorSearchResult record fields：
// - String id          // 文档唯一标识符
// - String content     // 匹配内容
// - double score       // 相似度分数 (0-1)
// - Map<String, Object> metadata  // 元数据
```

### VectorMemoryStore 类

```java
// VectorMemoryStore 类（Java SDK 已实现）
import com.harness.memory.VectorMemoryStore;
import com.harness.memory.VectorMemoryConfig;
import com.harness.memory.VectorSearchResult;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

// Java VectorMemoryStore 已在 VectorMemoryStore.java 中实现
// 通过 VectorMemoryStore.builder() 创建实例
VectorMemoryStore store = VectorMemoryStore.builder()
    .config(VectorMemoryConfig.builder().build())
    .build();
```

### 使用场景

```java
// 使用场景
import com.harness.memory.VectorMemoryStore;
import com.harness.memory.VectorMemoryConfig;
import com.harness.memory.VectorSearchResult;
import java.util.List;
import java.util.Map;

// 创建配置
VectorMemoryConfig config = VectorMemoryConfig.builder()
    .embeddingModel("mock")  // 使用模拟嵌入模型（测试用）
    .build();

// 创建向量存储
VectorMemoryStore store = VectorMemoryStore.builder().config(config).build();

// 添加文档
store.add("doc1", "用户偏好使用 PostgreSQL 而非 MySQL",
    Map.of("session_id", "abc123", "type", "preference")).join();

// 批量添加文档
store.addBatch(
    List.of("doc2", "doc3", "doc4"),
    List.of(
        "项目使用 Python 3.11 和 async/await 模式",
        "代码风格遵循 Black 格式化，行宽 88 字符",
        "测试使用 pytest 框架，避免 mock 数据库"),
    List.of(
        Map.of("type", "project_context"),
        Map.of("type", "coding_standard"),
        Map.of("type", "testing"))).join();

// 语义搜索
List<VectorSearchResult> results = store.search("数据库选择", 3).join();
for (VectorSearchResult result : results) {
    System.out.printf("[%.3f] %s%n", result.score(), result.content());
    System.out.println("  元数据: " + result.metadata());
}

// 添加对话历史
List<Map<String, Object>> messages = List.of(
    Map.of("role", "user", "content", "如何设置 Python 异步编程？"),
    Map.of("role", "assistant", "content", "使用 asyncio 库和 async/await 语法。"));
store.addConversation("session_123", messages).join();

// 搜索对话历史
List<VectorSearchResult> convResults = store.searchConversations("异步编程", "session_123", 10).join();
for (VectorSearchResult result : convResults) {
    System.out.println("对话匹配: " + result.content());
}

// 添加技能
store.addSkill("code_review", "代码审查时检查错误处理、类型注解和测试覆盖率。",
    Map.of("category", "development")).join();

// 搜索技能
List<VectorSearchResult> skillResults = store.searchSkills("代码审查", 2).join();
for (VectorSearchResult result : skillResults) {
    System.out.println("技能匹配: " + result.content());
}

// 删除文档
store.delete(List.of("doc1")).join();

// 清空存储
store.clear().join();
```

## SystemPromptBuilder（动态系统提示组装）

SystemPromptBuilder 负责动态组装系统提示，将多个来源的内容合并为最终系统提示。

### SystemPromptSource

```java
// SystemPromptSource（Java SDK 已在 SystemPromptSource.java 中定义）
import com.harness.memory.SystemPromptSource;
import java.nio.file.Path;
import java.util.function.Supplier;

// Java SystemPromptSource fields：
// - String name
// - int priority               // 优先级越高，在最终提示中越靠前
// - String content             // 静态内容（或 null）
// - Supplier<String> supplier  // 动态内容提供者（或 null）
// - Path filePath              // 文件路径（或 null）
// - boolean required           // 文件不存在时是否抛出错误
```

### SystemPromptConfig

```java
// SystemPromptConfig（Java SDK 已在 SystemPromptConfig.java 中定义）
import com.harness.memory.SystemPromptConfig;
import com.harness.memory.SystemPromptSource;
import java.nio.file.Path;
import java.util.Map;

// Java SystemPromptConfig fields：
// - String basePrompt                  // 基础系统提示
// - Path agentsMdPath                  // AGENTS.md 文件路径
// - Path memoryMdPath                  // MEMORY.md 文件路径
// - Path projectRoot                   // 项目根目录
// - boolean autoDiscover               // 自动发现 AGENTS.md 和 MEMORY.md
// - Map<String, SystemPromptSource> customSources  // 自定义源
// - String sectionSeparator            // 片段分隔符

// 通过 Builder 创建
SystemPromptConfig config = SystemPromptConfig.builder()
    .basePrompt("You are a helpful assistant.")
    .projectRoot(Path.of("."))
    .autoDiscover(true)
    .build();
```

### SystemPromptBuilder

```java
// SystemPromptBuilder（Java SDK 已在 SystemPromptBuilder.java 中定义）
import com.harness.memory.SystemPromptBuilder;
import com.harness.memory.SystemPromptConfig;
import com.harness.memory.SystemPromptSource;

// Java SystemPromptBuilder methods：
// - addSource(SystemPromptSource source)   // 添加新的提示源
// - removeSource(String name)              // 通过名称移除提示源
// - build()                               // 构建最终系统提示
// - getAvailableSources()                  // 获取有内容的源名称列表
// - getSourceContent(String name)          // 获取特定源的内容
```

### 组装优先级

```
1. 安全规则（最高优先级）
2. 角色定义
3. AGENTS.md 内容
4. 技能指令
5. 记忆上下文
6. 用户偏好
7. 基础提示（最低优先级）
```

### 使用方式

```java
// 使用方式
import com.harness.memory.SystemPromptConfig;
import com.harness.memory.SystemPromptBuilder;
import com.harness.memory.SystemPromptSource;
import java.nio.file.Path;
import java.util.Map;

// 创建配置
SystemPromptConfig config = SystemPromptConfig.builder()
    .basePrompt("You are a helpful assistant.")
    .projectRoot(Path.of("."))  // 设置项目根目录以自动发现文件
    .autoDiscover(true)  // 自动发现 AGENTS.md 和 MEMORY.md
    .build();

// 创建构建器
SystemPromptBuilder builder = new SystemPromptBuilder(config);

// 添加自定义源
SystemPromptSource securitySource = SystemPromptSource.builder()
    .name("security")
    .priority(100)
    .content("Never execute destructive operations without confirmation.")
    .build();
builder.addSource(securitySource);

// 构建最终提示
String systemPrompt = builder.build();
System.out.println("系统提示长度: " + systemPrompt.length() + " 字符");
```

### discover_project_context() 函数

```java
// discover_project_context() 函数（Java SDK 已在 SystemPromptBuilder 内部实现）
import com.harness.memory.SystemPromptBuilder;
import java.nio.file.Path;
import java.util.Map;

// SystemPromptBuilder 在 build() 时自动发现项目上下文
// 通过 autoDiscover 配置启用
SystemPromptConfig config = SystemPromptConfig.builder()
    .projectRoot(Path.of("."))
    .autoDiscover(true)
    .build();

SystemPromptBuilder builder = new SystemPromptBuilder(config);
String context = builder.build();

// 发现的文件内容已包含在构建结果中
// 可通过 getSourceContent() 获取特定源内容
String agentsContent = builder.getSourceContent("AGENTS.md");
String memoryContent = builder.getSourceContent("MEMORY.md");
```

## 记忆后端

Harness 支持多种记忆存储后端：

| 后端 | 说明 | 适用场景 |
|------|------|----------|
| **文件系统** | 默认，使用 JSON/YAML 文件 | 开发、小规模 |
| **SQLite** | 轻量数据库 | 中等规模 |
| **向量存储** | 语义搜索 | 大规模、需要检索 |

```java
// 记忆后端配置
import com.harness.integration.AgentHarness;
import com.harness.types.HarnessConfig;

// 默认文件系统后端
AgentHarness agent = AgentHarness.builder()
    .memoryDir(Path.of(".harness/memory"))
    .build();

// 启用向量检索
AgentHarness agentWithVector = AgentHarness.builder()
    .memoryDir(Path.of(".harness/memory"))
    .vectorStore(true)  // 自动创建 VectorMemoryStore
    .build();
```

## 上下文压缩

当工作记忆超过阈值时，Agent Loop 自动触发压缩：

1. 保留最近 N 条消息
2. 将更早的消息压缩为摘要
3. 摘要替换原始消息，释放上下文空间
4. 原始消息仍可通过向量检索访问

```java
// 上下文压缩配置
import com.harness.integration.AgentHarness;
import com.harness.types.HarnessConfig;

// AgentHarness 配置压缩阈值
AgentHarness agent = AgentHarness.builder()
    .maxInputTokens(100000)  // 最大输入 token 数
    .build();

// 当 token 数超过 compression_threshold 时自动触发压缩
// Ralph Loop 中自动压缩
```

## 与技能系统的集成

记忆系统与技能系统紧密集成：

1. **技能加载**：ProgressiveSkillLoader 根据上下文预算决定加载级别
2. **MEMORY.md**：技能执行过程中的经验可保存为记忆
3. **向量检索**：技能内容被索引用于语义搜索
4. **系统提示**：技能指令通过 SystemPromptBuilder 注入系统提示

```java
// 技能经验保存为记忆
import com.harness.integration.AgentHarness;
import com.harness.core.HookPoint;
import com.harness.core.HookContext;
import com.harness.core.HookResult;
import com.harness.memory.MemoryFileManager;
import com.harness.memory.MemoryEntry;
import com.harness.memory.MemoryCategory;
import com.harness.memory.MemorySource;
import com.harness.memory.VectorMemoryStore;
import java.util.Map;

AgentHarness agent = AgentHarness.builder().build();

agent.addHook(HookPoint.AFTER_TOOL_EXECUTE, ctx -> {
    if (ctx.toolResult() != null && ctx.toolResult().isError()) {
        // 将错误经验保存到 MEMORY.md
        MemoryFileManager manager = new MemoryFileManager(Path.of("."));
        MemoryEntry entry = MemoryEntry.builder()
            .category(MemoryCategory.LEARNED_PATTERNS)
            .content("Avoid " + ctx.toolName() + " when " + ctx.toolResult().error() + " occurs")
            .source(MemorySource.AGENT_OBSERVATION)
            .metadata(Map.of(
                "skill", "code-review",
                "error", ctx.toolResult().error(),
                "tool", ctx.toolName()))
            .build();
        manager.addEntry(entry);
    }

    // 向量检索技能内容
    if ("code_review".equals(ctx.toolName())) {
        VectorMemoryStore vectorStore = VectorMemoryStore.builder().build();
        vectorStore.addSkill("code_review_pattern",
            "Code review pattern: " + ctx.toolResult().content().substring(0, Math.min(100, ctx.toolResult().content().length())) + "...",
            Map.of("session_id", ctx.sessionId()));
    }

    return HookResult.continue_();
});
```

## 全局记忆配置

Harness SDK 支持配置全局记忆文件路径，让 Agent 自动加载全局 MEMORY.md 文件。

### 配置方式

```java
// 全局记忆配置
import com.harness.integration.AgentHarness;
import com.harness.memory.SystemPromptSource;
import java.nio.file.Path;

// 方式 1：通过 HarnessConfig 配置
AgentHarness agent1 = AgentHarness.builder()
    .model("claude-sonnet-4-6")
    .memoryMdPath(Path.of(System.getProperty("user.home"), ".harness", "MEMORY.md"))
    .build();

// 方式 2：通过 ContextBuilder 添加自定义记忆源
AgentHarness agent2 = AgentHarness.builder()
    .model("claude-sonnet-4-6")
    .build();
agent2.contextBuilder().addPromptSource(SystemPromptSource.builder()
    .name("GlobalMemory")
    .priority(40)
    .filePath(Path.of(System.getProperty("user.home"), ".harness", "MEMORY.md"))
    .build());
```

### 配置项说明

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `memory_md_path` | `Path \| None` | `None` | 全局 MEMORY.md 文件路径，设置后自动加载到上下文 |

### 使用场景

- **用户偏好存储**：保存用户常用的编码风格、语言偏好等
- **跨项目知识共享**：在多个项目间共享通用的技术决策和模式
- **客户端集成**：桌面客户端可通过 UI 管理全局记忆
- **即时更新**：MEMORY.md 修改后在下一次 run() 调用时自动生效

---

## 记忆评分与衰减机制

基于 Mem0 的 Recency-Aware Ranking 和 Bjork 新遗忘理论，Harness 实现了智能的记忆生命周期管理。

### 核心理念

**不删除记忆，只影响检索排序**。这遵循 Bjork 新遗忘理论的两个强度概念：

- **Storage Strength (importance)**：创建时决定，之后不再变化，用于归档决策
- **Retrieval Strength**：动态变化（时间衰减 + 访问恢复），用于检索排序

### 分层记忆架构

```
Layer 1: Core Memory (MEMORY.md) = Agent 的 "RAM"
- 用户偏好、项目约定
- 始终注入系统提示（无条件可见）
- 不需要检索，不需要 Retrieval Strength
- 容量超限时 Archive 到 Retrieved Memory（不丢失）

Layer 2: Retrieved Memory (VectorMemoryStore) = Agent 的 "Hard Drive"
- 历史对话、特定事件、已归档记忆
- 查询时按需检索
- 需要 Retrieval Strength 加权排序
```

### Retrieval Strength 计算

```
检索分数 = 语义相似度 × Retrieval Strength

Retrieval Strength = 时间衰减因子 × 访问奖励因子

其中：
- 时间衰减因子 = min_strength + (1 - min_strength) × e^(-λ × 未访问天数)
  - 最近访问：≈ 1.0（接近满分）
  - 长期未访问：→ 0.3（保底分数，默认 min_strength=0.3）
- 访问奖励因子 = 1 + 0.5 × log(1 + access_count)
  - 从未访问：1.0
  - 访问 10 次：≈ 2.0
  - 访问 100 次：≈ 2.5
```

**关键设计**：最低 0.3× 保底分数确保旧记忆仍能被检索，只是排序靠后。

### MemoryEntry 增强

```java
// MemoryEntry 增强（Java SDK 已在 MemoryEntry.java 中定义）
import com.harness.memory.MemoryEntry;
import com.harness.memory.MemoryCategory;
import com.harness.memory.MemorySource;
import java.time.Instant;
import java.util.Map;

// Java MemoryEntry fields（包含增强字段）：
// - MemoryCategory category
// - String content
// - MemorySource source
// - Instant createdAt
// - Map<String, Object> metadata
// - double importance            // Storage Strength（用于归档决策）
// - Instant lastAccessed         // 最后访问时间
// - int accessCount              // 访问次数

// 通过 Builder 创建
MemoryEntry entry = MemoryEntry.builder()
    .category(MemoryCategory.KEY_DECISIONS)
    .content("Chose SQLite for session storage")
    .source(MemorySource.AGENT_OBSERVATION)
    .importance(1.0)
    .build();

// calculateRetrievalStrength 方法已内置
double score = entry.calculateRetrievalStrength(0.05, 0.3);

// touch 方法更新访问时间和计数
entry.touch();
```

### MemoryScoringConfig

```java
// MemoryScoringConfig（Java SDK 已在 MemoryScoringConfig.java 中定义）
import com.harness.memory.MemoryScoringConfig;
import com.harness.memory.ArchiveFallback;

// Java MemoryScoringConfig fields：
// - double decayLambda               // 衰减速度（λ 越大衰减越快）
// - double minRetrievalStrength       // 最低检索强度（保底）
// - int maxCoreMemoryTokens           // Core Memory 最大 token 数
// - boolean enableLlmEvaluation       // 是否启用 LLM 评估 importance
// - ArchiveFallback archiveFallback   // 归档降级策略

// 通过 Builder 创建
MemoryScoringConfig scoringConfig = MemoryScoringConfig.builder()
    .decayLambda(0.05)
    .minRetrievalStrength(0.3)
    .maxCoreMemoryTokens(2000)
    .enableLlmEvaluation(false)
    .archiveFallback(ArchiveFallback.FILE)  // file: 归档到 MEMORY_ARCHIVE.md
    .build();
```

### 使用配置

```java
// 使用配置
import com.harness.integration.AgentHarness;
import com.harness.types.HarnessConfig;
import com.harness.memory.MemoryScoringConfig;
import com.harness.memory.ArchiveFallback;

HarnessConfig config = HarnessConfig.builder()
    .memoryScoring(MemoryScoringConfig.builder()
        .decayLambda(0.05)
        .maxCoreMemoryTokens(2000)
        .enableLlmEvaluation(true)
        .archiveFallback(ArchiveFallback.FILE)
        .build())
    .build();
AgentHarness agent = AgentHarness.builder().config(config).build();
```

---

## Archive 机制

当 Core Memory 超过容量限制时，自动归档低 importance 的 Entry 到 Retrieved Memory。

### 触发时机

**触发时机**：仅 `run()` 时检查并执行。

```java
// 触发时机（AgentLoop.run() 中的实现）
// Java SDK 中 archiveLowImportance() 在 AgentHarness.run() 时自动调用
// 伪代码：
// public LoopResult run(String prompt) {
//     // 检查 Core Memory 容量
//     var capacity = memoryManager.fileStore().checkCapacity();
//     if (capacity.isOver()) {
//         memoryManager.archiveLowImportance().join();
//     }
//     // 继续执行 Agent Loop
//     ...
// }
```

**不在 `add_entry()` 时标记**，理由：
- 容量检查开销很小（只是计算字符串长度/token）
- 每次都检查确保不遗漏
- 无状态设计更可靠

### 归档策略（Entry 级别）

**关键设计**：归档是 Entry 级别，不是 Section 级别。即使某 Section 有 10 条 Entry，也只归档 importance 最低的那几条。

```java
// 归档策略（Entry 级别）
// Java SDK 中 archiveLowImportance() 已在 MemoryManager.java 中实现
// 伪代码：
// public CompletableFuture<Integer> archiveLowImportance() {
//     // 收集所有 section 的所有 Entry
//     List<ArchivableEntry> allEntries = new ArrayList<>();
//     for (MemoryCategory category : MemoryCategory.values()) {
//         List<MemoryEntry> entries = loadEntriesWithMetadata(category);
//         for (int i = 0; i < entries.size(); i++) {
//             allEntries.add(new ArchivableEntry(category, i, entries.get(i)));
//         }
//     }
//     // 按 importance 排序（低分优先归档）
//     allEntries.sort(Comparator.comparingDouble(e -> e.entry().importance()));
//     int archived = 0;
//     for (ArchivableEntry item : allEntries) {
//         archiveEntry(item.entry());
//         removeEntry(item.category(), item.index() - archived);
//         archived++;
//         if (checkCapacity().tokens() <= MAX_CORE_MEMORY_TOKENS * 0.8) {
//             break;
//         }
//     }
//     return CompletableFuture.completedFuture(archived);
// }
```

### 无向量数据库的降级方案

当用户未配置 VectorMemoryStore 时，归档的 Entry 写入 `MEMORY_ARCHIVE.md` 文件：

```markdown
# Archived Memory

> 以下记忆已从 Core Memory 归档。可通过全文搜索查找。

## User Profile
- [2026-01-15, importance=0.3] 旧偏好：用户曾使用 macOS

## Key Decisions
- [2025-12-01, importance=0.4] 历史决策：选择 Redis 作为缓存

## Learned Patterns
- [2025-11-15, importance=0.2] 临时模式：用户当时偏好简短回复

## Project Context
- [2025-10-01, importance=0.3] 过时信息：项目使用 Python 3.9
```

### 行为对比

| 场景 | VectorMemoryStore | MEMORY_ARCHIVE.md |
|------|-------------------|-------------------|
| **数据丢失** | 不丢失 | 不丢失 |
| **检索方式** | 语义搜索 | 全文搜索/手动查看 |
| **Retrieval Strength** | 适用 | 不适用 |
| **Agent 自动访问** | 是（通过 search()） | 否（需手动查看文件） |

---

## Importance 的来源与评估

### Importance 的生命周期

```
1. 创建时：LLM 评估（或默认值 1.0）
   ↓
2. 存储后：不再变化（Storage Strength 是静态的）
   ↓
3. 归档决策：按 importance 排序，低分优先归档
```

### LLM 评估触发时机

**异步评估**：添加 Entry 后，后台异步评估 importance，不阻塞主流程。

```java
// LLM 评估触发时机（Java SDK 中的实现）
// 异步评估：添加 Entry 后，后台异步评估 importance，不阻塞主流程
// 伪代码：
// public CompletableFuture<Void> addEntryAsync(MemoryEntry entry, LLMClient llmClient) {
//     // 先添加（importance=1.0）
//     entries.add(entry);
//     save();
//     // 后台评估
//     if (config.enableLlmEvaluation() && llmClient != null) {
//         return evaluateImportance(entry, llmClient)
//             .thenAccept(importance -> {
//                 entry.setImportance(importance);
//                 save();
//             });
//     }
//     return CompletableFuture.completedFuture(null);
// }
```

### 评估示例

| 记忆内容 | 类别 | LLM 评估结果 | 说明 |
|---------|------|-------------|------|
| "用户使用 Windows" | user_profile | 0.85 | 核心偏好，长期有效 |
| "选择 SQLite 作为存储" | key_decisions | 0.75 | 重要决策 |
| "用户喜欢详细的代码示例" | learned_patterns | 0.6 | 一般有用 |
| "上次讨论了 Python 异步" | project_context | 0.4 | 可能过时 |
| "今天天气很好" | project_context | 0.1 | 快速过时 |

---

## MemoryManager（统一接口）

MemoryManager 是分层记忆架构的统一入口，管理 Core Memory 和 Retrieved Memory。

### 核心接口

```java
// MemoryManager（Java SDK 已在 MemoryManager.java 中定义）
import com.harness.memory.MemoryManager;
import com.harness.memory.MemoryFileManager;
import com.harness.memory.VectorMemoryStore;
import com.harness.memory.MemoryScoringConfig;
import com.harness.memory.MemoryEntry;
import com.harness.memory.MemoryCategory;
import java.util.concurrent.CompletableFuture;

// Java MemoryManager methods：
// - getContext(String query)              // 获取完整记忆上下文
// - addMemory(MemoryEntry entry, Target target)  // 添加记忆到指定层级
// - archiveToRetrieved(MemoryCategory category, int index)  // 归档到 Retrieved Memory
// - checkCapacity()                       // 检查 Core Memory 容量
// - archiveLowImportance()                // 归档低 importance 的 Entry

// 通过 Builder 创建
MemoryManager manager = MemoryManager.builder()
    .fileStore(new MemoryFileManager(Path.of(".")))
    .vectorStore(VectorMemoryStore.builder().build())
    .config(MemoryScoringConfig.builder().build())
    .build();

// 获取记忆上下文
String context = manager.getContext("用户偏好").join();

// 添加记忆到 Core Memory
MemoryEntry entry = MemoryEntry.builder()
    .category(MemoryCategory.USER_PROFILE)
    .content("操作系统：Windows")
    .build();
manager.addMemory(entry, MemoryManager.Target.CORE).join();

// 归档到 Retrieved Memory
manager.archiveToRetrieved(MemoryCategory.KEY_DECISIONS, 0).join();
```

---

## UpdateCoreMemoryTool

Agent 可通过工具更新 Core Memory（MEMORY.md）。采用 **Mem0 模式**：显式添加到工具列表。

### 工具定义

```java
// UpdateCoreMemoryTool（Java SDK 已在 UpdateCoreMemoryTool.java 中定义）
import com.harness.tools.UpdateCoreMemoryTool;
import com.harness.core.Tool;
import com.harness.core.ToolResult;
import com.harness.core.ToolContext;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

// Java UpdateCoreMemoryTool 实现了 Tool 接口
public class UpdateCoreMemoryToolImpl implements Tool {
    @Override
    public String name() { return "update_core_memory"; }

    @Override
    public String description() {
        return "更新用户偏好或项目约定到长期记忆。\n\n"
            + "重要规则：\n"
            + "1. 提炼内容：不要存储用户原话，要提炼成简洁的陈述\n"
            + "2. 避免重复：添加前先检查是否已有类似记忆，如有则不要重复添加\n"
            + "3. 适用场景：用户提到长期偏好、工作环境、项目约束等\n\n"
            + "示例：\n"
            + "- 用户：「我习惯用深色主题」→ category=user_profile, content=\"主题偏好：深色\"\n"
            + "- 用户：「以后回复简短一点」→ category=learned_patterns, content=\"回复风格：简洁\"";
    }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "category", Map.of("type", "string", "enum",
                    java.util.List.of("user_profile", "key_decisions", "learned_patterns", "project_context")),
                "content", Map.of("type", "string"),
                "action", Map.of("type", "string", "enum", java.util.List.of("add", "remove"))),
            "required", java.util.List.of("category", "content", "action"));
    }

    @Override
    public CompletableFuture<ToolResult> execute(ToolContext ctx) {
        // 实现逻辑
        return CompletableFuture.completedFuture(
            ToolResult.success("已添加到 " + ctx.args().get("category") + ": " + ctx.args().get("content"),
                Map.of("refresh_memory", true)));
    }
}
```

### 内容提炼规则

工具的 description 引导 Agent 提炼用户原话，而不是直接存储：

| 用户原话 | 提炼后的存储内容 |
|---------|-----------------|
| "使用 cmd，不要用 powershell" | `Shell：使用 cmd（不使用 PowerShell）` |
| "我使用 Windows" | `操作系统：Windows` |
| "我习惯用深色主题" | `主题偏好：深色` |
| "以后回复简短一点" | `回复风格：简洁` |

### 去重机制

`MemoryFileManager.add_entry()` 使用字符级 Jaccard 相似度检测重复：

```java
// 去重机制（Java SDK 已在 MemoryFileManager.java 中实现）
// MemoryFileManager.addEntry() 使用字符级 Jaccard 相似度检测重复
// 伪代码：
// public boolean addEntry(MemoryEntry entry, boolean checkDuplicate) {
//     if (checkDuplicate) {
//         for (String existing : section) {
//             double similarity = calculateSimilarity(entry.content(), existing);
//             if (similarity > 0.7) {  // 70% 相似度阈值
//                 logger.info("Skipping duplicate memory: '" + entry.content() + "'");
//                 return false;
//             }
//         }
//     }
//     section.add(entry.content());
//     save(sections);
//     return true;
// }
//
// private double calculateSimilarity(String text1, String text2) {
//     // 字符级 bigram Jaccard 相似度，支持中英文混合
//     Set<String> ngrams1 = new HashSet<>();
//     Set<String> ngrams2 = new HashSet<>();
//     for (int i = 0; i < text1.length() - 1; i++) {
//         ngrams1.add(text1.substring(i, i + 2));
//     }
//     for (int i = 0; i < text2.length() - 1; i++) {
//         ngrams2.add(text2.substring(i, i + 2));
//     }
//     Set<String> intersection = new HashSet<>(ngrams1);
//     intersection.retainAll(ngrams2);
//     Set<String> union = new HashSet<>(ngrams1);
//     union.addAll(ngrams2);
//     return (double) intersection.size() / union.size();
// }
```

### Metadata 支持

`ToolResult.metadata` 用于传递 UI 刷新信号：

```java
// Metadata 支持（Java SDK 已在 ToolResult.java 中实现）
import com.harness.core.ToolResult;
import java.util.Map;

// 添加成功时返回 refresh_memory 信号
ToolResult result = ToolResult.success(
    "已添加到 " + category + ": " + content,
    Map.of("refresh_memory", true));  // UI 刷新信号
```

客户端收到此信号后会刷新记忆面板显示。

### 使用方式

```java
// 使用方式
import com.harness.integration.AgentHarness;
import com.harness.tools.UpdateCoreMemoryTool;

// 显式添加工具
AgentHarness agent = AgentHarness.builder()
    .model("claude-sonnet-4-6")
    .tools(java.util.List.of(new UpdateCoreMemoryTool()))
    .build();
```

### 触发机制

**主机制**：Agent 在对话过程中自主判断是否需要更新 Core Memory。

```
用户: "我使用的是 Windows"

Agent 内部推理:
1. 识别到这是长期偏好信息
2. 判断应该存入 Core Memory
3. 调用 update_core_memory 工具

→ Tool 被触发，将 "Platform: Windows" 写入 MEMORY.md
```

**可选补充**：CoreMemoryExtractionHook 在对话结束后自动提取遗漏的记忆。

---

## 上下文压缩（Context Compression）

当对话历史超过 token 预算时，Harness 自动压缩上下文以保持响应能力。压缩遵循 **chat template 要求**：system 消息必须在消息列表开头。

### 压缩流程

```
1. 检测：estimated_tokens > budget.available_for_input * threshold
2. 压缩：保留最近 N 条消息，生成旧消息摘要
3. 合并：将摘要合并到真正的 system prompt 中
4. 返回：[system(prompt + summary), user, assistant, ...]
```

### ContextCompressor

压缩器负责生成摘要，**不再插入 system 消息**：

```java
// ContextCompressor（Java SDK 已在 ContextCompressor.java 中定义）
import com.harness.memory.ContextCompressor;
import com.harness.memory.CompressionConfig;
import com.harness.memory.CompressionResult;

ContextCompressor compressor = new ContextCompressor(tokenCounter,
    CompressionConfig.builder()
        .minMessagesBeforeCompress(10)
        .keepRecentMessages(5)
        .summaryMaxTokens(500)
        .build());

CompressionResult result = compressor.compress(messages, targetTokens);

// result.compressedMessages() - 压缩后的消息列表
// result.summary() - 摘要字符串
```

### ContextBuilder

上下文构建器负责组装消息、处理压缩，并**将摘要合并到 system prompt**：

```java
// ContextBuilder（Java SDK 已在 ContextBuilder.java 中定义）
import com.harness.memory.ContextBuilder;
import com.harness.memory.BuiltContext;

ContextBuilder builder = new ContextBuilder()
    .withMaxTokens(200000)
    .withSystemPrompt("You are a helpful assistant.")
    .withWindowSize(100)
    .withCompressionEnabled(true);  // 默认已启用

BuiltContext context = builder.build(session);
// context.messages() - 消息列表
// context.systemPrompt() - 系统提示（包含压缩摘要）
```

**注意**：Java SDK 使用链式调用方法（`with*`），而不是 Builder 模式。

### 关键设计：避免 system 消息冲突

**问题**：vLLM 等推理引擎的 chat template 要求 system 消息必须在开头。如果压缩器插入 system 消息，会导致消息列表变成：

```
[system(real_prompt), system(compression_summary), user, assistant, ...]  ❌ 错误
```

**解决方案**：压缩器只返回摘要字符串，由 ContextBuilder 合并到真正的 system prompt：

```
[system(real_prompt + summary), user, assistant, ...]  ✅ 正确
```

### BuiltContext 结构

```java
// BuiltContext 结构（Java SDK 已在 BuiltContext.java 中定义）
import com.harness.memory.BuiltContext;
import com.harness.memory.CompressionResult;
import com.harness.memory.ContextBudget;
import com.harness.types.Message;
import java.util.List;

// Java BuiltContext record：
// public record BuiltContext(
//     List<Message> messages,        // 消息列表
//     String systemPrompt,           // 系统提示（含摘要）
//     int estimatedTokens,           // 估算 token 数
//     ContextBudget budget,          // Token 预算
//     boolean compressionNeeded,     // 是否触发了压缩
//     CompressionResult compressionResult  // 压缩结果详情
// ) {}
```

### 使用示例

```java
// 使用示例（Java SDK 中通过 LoopConfig 配置）
import com.harness.integration.AgentHarness;
import com.harness.types.LoopConfig;

AgentHarness agent = AgentHarness.builder()
    .model("claude-sonnet-4-6")
    .contextWindow(200000)
    .sessionWindow(100)
    .enableCompression(true)
    .build();

// 长对话会自动压缩
LoopResult result = agent.run("分析这个大型代码库...").join();
```

---

## 设计总结

| 特性 | Core Memory (MEMORY.md) | Retrieved Memory (VectorMemoryStore) |
|------|------------------------|-------------------------------------|
| **加载方式** | 全量加载 | 按需检索 |
| **access_count** | 不追踪 | 追踪，影响排序 |
| **Retrieval Strength** | 不适用 | 适用（时间衰减 + 访问奖励） |
| **容量管理** | 按 importance 归档低分 Entry | 无容量限制，检索时排序 |
| **淘汰粒度** | Entry 级别（跨 section） | 不淘汰，只降权 |
| **importance 来源** | LLM 评估（可选） | 从 Core Memory 归档时继承 |
| **无向量数据库时** | 归档到 MEMORY_ARCHIVE.md | 不适用 |

## 下一步

- [03-agent-loop.md](./03-agent-loop.md) - 了解 Agent Loop
- [04-tool-system.md](./04-tool-system.md) - 了解工具系统（含 UpdateCoreMemoryTool）
- [16-skills-system.md](./16-skills-system.md) - 了解技能系统
- [03-agent-loop.md](./03-agent-loop.md#上下文压缩) - 了解 AgentLoop 如何集成上下文压缩
