# 05 - 技能系统详解

## 概述

技能系统定义 Agent 的行为边界。技能是 Markdown 文件，包含指令、工具限制和行为规范。Harness 支持渐进式技能加载和技能文件自动发现。

## 技能文件格式

### 基本格式

```markdown
---
name: code-review
description: Review code for issues
tools:
  allowed: [read, grep, glob]
  restricted: [write, edit]
  default_permission: deny
triggers:
  keywords: [review, check, audit]
  patterns: ["review this", "check my code"]
version: 1.0.0
author: harness-team
---

# Code Review Skill

You are a code reviewer. Your task is to:
1. Read the code files
2. Identify bugs, security issues, performance problems
3. Provide actionable suggestions

## Guidelines

- Focus on correctness first, then performance
- Always check for security vulnerabilities
- Provide concrete fix suggestions
```

### SkillMetadata（渐进式加载元数据）

SkillMetadata 是渐进式技能加载中使用的轻量级元数据类，仅包含基本信息和触发条件，用于技能匹配和选择。

```java
import com.harness.skills.ProgressiveSkillLoader;

public class SkillMetadata {
    private String name;                    // 技能名称（必需）
    private String description;             // 技能描述（必需）
    private Path path;                      // 技能文件路径
    private Map<String, List<String>> triggers;  // 触发条件
    private String version = "1.0.0";       // 版本号

    // 内部缓存字段
    private Skill cachedSkill;              // 缓存的完整技能对象
    private boolean loaded = false;         // 是否已加载完整内容

    public String toListItem() {
        return "- " + name + ": " + description;
    }

    public boolean matches(String text) {
        // 实现细节：检查关键词和正则表达式匹配
        // ...
    }
}
```

### Frontmatter 字段说明

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 技能唯一标识 |
| `description` | string | 是 | 技能描述（LLM 可见） |
| `tools` | dict | 否 | 工具配置字典，包含 `allowed`、`restricted`、`default_permission` |
| `triggers` | dict | 否 | 触发条件字典，包含 `keywords`、`patterns`、`tools` |
| `parameters` | dict | 否 | 参数字典，定义可配置参数 |
| `version` | string | 否 | 版本号 |
| `author` | string | 否 | 作者 |
| `metadata` | dict | 否 | 元数据字典 |
| `tags` | string[] | 否 | 标签，用于分类和搜索 |

## SkillRegistry（技能注册）

SkillRegistry 管理技能的注册、发现和查询。

```java
import com.harness.skills.SkillRegistry;
import java.nio.file.Path;

public class SkillRegistry {
    public SkillRegistry() {
        // 初始化技能注册表
    }

    public void addSkillDir(Path directory) {
        // 添加技能目录并自动加载所有技能
    }

    public void register(Skill skill) {
        // 注册技能（同名技能按版本号覆盖）
    }

    public boolean unregister(String name) {
        // 注销技能，返回是否成功
    }

    public Skill get(String name) {
        // 获取技能
    }

    public List<Skill> listSkills() {
        // 列出所有注册技能
    }

    public List<Skill> findMatchingSkills(String userInput) {
        // 根据用户输入查找匹配的技能
    }

    public boolean activate(String skillName) {
        // 激活技能，返回是否成功
    }

    public boolean deactivate(String skillName) {
        // 停用技能，返回是否成功
    }

    public List<Skill> getActiveSkills() {
        // 获取所有激活的技能
    }

    public void clearActive() {
        // 清除所有激活的技能
    }

    public boolean isToolAllowed(String toolName) {
        // 检查工具是否被所有激活技能允许
    }

    public void reload() {
        // 重新加载所有技能目录
    }

    public int size() {
        // 返回注册技能数量
    }

    public boolean contains(String name) {
        // 检查技能是否已注册
    }

    public Iterator<Skill> iterator() {
        // 迭代所有技能
    }
}
```

### 技能发现

```
skill_dirs/
├── code-review.md       → 自动注册为 skill
├── debugging.md         → 自动注册为 skill
├── security/
│   ├── audit.md         → 自动注册为 skill
│   └── compliance.md    → 自动注册为 skill
└── data/
    └── analysis.md      → 自动注册为 skill
```

## ProgressiveSkillLoader（渐进式技能加载）

渐进式技能加载解决上下文预算问题——不是一次性加载所有技能的完整内容，而是根据需要逐级加载。

### LoadingLevel（加载级别）

```java
import com.harness.skills.ProgressiveSkillLoader;

public class LoadingLevel {
    /** Level 1: 仅加载元数据 */
    public static final int FRONTMATTER = 1;
    /** Level 2: 加载完整内容 */
    public static final int FULL_CONTENT = 2;
    /** Level 3: 加载引用文件 */
    public static final int REFERENCES = 3;
}
```

### 加载策略

```
上下文预算评估
    │
    ├─ 预算充足 → 全部 FULL 加载
    │
    ├─ 预算紧张 → 高优先级 FULL，低优先级 FRONTMATTER
    │
    └─ 预算不足 → 仅 FRONTMATTER，需要时再 FULL
```

### ProgressiveSkillLoader

```java
import com.harness.skills.ProgressiveSkillLoader;
import com.harness.skills.SkillMetadata;
import java.nio.file.Path;

public class ProgressiveSkillLoader {
    public ProgressiveSkillLoader() {
        this(50);
    }

    /**
     * @param cacheSize 内存中缓存的技能最大数量
     */
    public ProgressiveSkillLoader(int cacheSize) {
        // ...
    }

    public List<SkillMetadata> discoverSkills(Path directory) {
        // 发现目录中的所有技能（Level 1 加载，仅读取 frontmatter）
    }

    public Skill loadFullContent(SkillMetadata metadata) {
        // 加载完整的技能内容（Level 2 加载）
    }

    public List<SkillMetadata> matchSkills(
        String text,
        List<SkillMetadata> skills,
        int maxMatches
    ) {
        // 根据用户输入文本匹配技能
    }

    public SkillWithReferences loadWithReferences(
        SkillMetadata metadata,
        // 可选的引用加载器
    ) {
        // 加载技能及其所有引用文件（Level 3 加载）
    }

    public String buildSkillSelectionPrompt(
        List<SkillMetadata> skills,
        String formatStyle
    ) {
        // 构建技能选择提示
    }

    public int estimateTokens(List<?> skills, int level) {
        // 估算技能列表的 token 数量
    }

    public void clearCache() {
        // 清除所有缓存技能
    }
}
```

### 使用示例

```java
import java.nio.file.Path;
import com.harness.skills.ProgressiveSkillLoader;
import com.harness.skills.ProgressiveSkillLoader.SkillMetadata;
import com.harness.skills.ProgressiveSkillLoader.LoadingLevel;
import com.harness.skills.Skill;

// 创建加载器
ProgressiveSkillLoader loader = new ProgressiveSkillLoader(50);

// Level 1: 发现所有技能的元数据
Path skillsDir = Path.of(".harness", "skills");
List<SkillMetadata> allSkills = loader.discoverSkills(skillsDir);

// 构建技能选择提示
String skillList = loader.buildSkillSelectionPrompt(allSkills, "list");
System.out.println("可用技能:\n" + skillList);

// 根据用户输入匹配技能
String userInput = "审查代码中的安全漏洞";
List<SkillMetadata> matched = loader.matchSkills(userInput, allSkills, 3);

// Level 2: 加载完整内容
for (SkillMetadata skillMeta : matched) {
    Skill skill = loader.loadFullContent(skillMeta);
    System.out.println("[" + LoadingLevel.FULL_CONTENT + "] " + skill.name() + ": " + skill.content().substring(0, Math.min(100, skill.content().length())) + "...");
}

// Level 3: 加载技能及其引用文件
for (SkillMetadata skillMeta : matched) {
    var result = loader.loadWithReferences(skillMeta);
    System.out.println("[" + LoadingLevel.REFERENCES + "] " + result.skill().name() + " 有 " + result.references().size() + " 个引用文件");
}

// 估算 token 使用
int tokens = loader.estimateTokens(matched, LoadingLevel.FULL_CONTENT);
System.out.println("估计 token 使用: " + tokens);

// 清除缓存
loader.clearCache();
```

### 各级别的内容格式

**Level 1: FRONTMATTER 级别**（最小上下文占用，仅元数据）：

```
Available skills:
- code-review: Review code for issues (tools: read, grep, glob)
- security-audit: Security audit for vulnerabilities (tools: read, bash)
```

**Level 2: FULL_CONTENT 级别**（完整技能内容）：

```
## Skill: code-review

You are a code reviewer. Your task is to:
1. Read the code files
2. Identify bugs, security issues, performance problems
3. Provide actionable suggestions
...
```

**Level 3: REFERENCES 级别**（包含引用文件）：

```
Skill: code-review
Content: [完整技能内容]

--- References ---
file1.py:
def example_function():
    ...

file2.md:
# Example documentation
...
```

## SkillInjector（技能注入）

SkillInjector 将技能指令注入系统提示，让 LLM 感知可用技能。

```java
import com.harness.skills.SkillInjector;
import com.harness.skills.InjectionConfig;
import com.harness.skills.SkillRegistry;

public class SkillInjector {
    /**
     * @param registry 技能注册表
     * @param config   注入配置（可选）
     */
    public SkillInjector(SkillRegistry registry, InjectionConfig config) {
        // ...
    }

    public String injectSkills(
        String systemPrompt,
        String userInput,
        Map<String, Object> context
    ) {
        // 将技能注入系统提示
        // 返回注入技能后的系统提示
    }

    public Predicate<String> getToolFilter() {
        // 获取工具过滤函数，返回 true 表示工具被允许
    }

    public InjectionPreview getInjectionPreview(
        String systemPrompt,
        String userInput
    ) {
        // 获取注入预览信息
    }
}

public record InjectionConfig(
    int maxSkillsPerPrompt,          // 每个提示最大技能数（默认 5）
    int maxSkillLength,              // 每个技能最大长度（默认 2000）
    String injectMethod,             // append, prepend, section
    String skillSeparator            // 技能分隔符
) {
    public static InjectionConfig defaults() {
        return new InjectionConfig(5, 2000, "append", "\n\n---\n\n");
    }
}
```

## Skill 基类

```java
import com.harness.skills.SkillMetadata;

public record Skill(
    String name,                        // 技能名称
    SkillMetadata metadata,             // 技能描述
    String content,                     // 技能完整内容（Markdown）
    SkillTrigger triggers,              // 触发条件
    SkillTools tools,                   // 工具配置
    List<SkillParameter> parameters,    // 参数列表
    String version,                     // 版本号
    String author,                      // 作者
    Map<String, Object> metadata,       // 元数据
    Path sourcePath                     // 源文件路径
) {
    public Skill {
        this.version = version != null ? version : "1.0.0";
        this.author = author != null ? author : "";
    }
}
```

## 技能与工具的关系

技能可以限制可用工具范围，防止 Agent 执行不必要的操作：

```markdown
---
name: read-only-analysis
description: Analyze code without making changes
tools:
  allowed: [read, grep, glob]
  restricted: [write, edit, bash]
  default_permission: deny
---

You are a code analyst. You may only read files, never modify them.
```

```markdown
---
name: full-development
description: Full development with all tools
tools:
  allowed: [read, write, edit, glob, grep, bash]
  default_permission: allow
---

You are a developer. You can read, write, and execute code.
```

## 技能目录结构

推荐的项目技能目录结构：

```
.harness/
├── skills/
│   ├── code-review.md
│   ├── debugging.md
│   ├── testing.md
│   └── security/
│       ├── audit.md
│       └── compliance.md
├── memory/
│   ├── MEMORY.md              # 记忆索引
│   └── feedback_testing.md    # 反馈记忆
└── vectors/                   # 向量索引
```

## 与其他系统的集成

### 与 AgentHarness 集成

AgentHarness 内置了技能系统，在运行时自动注入匹配的技能：

```java
import com.harness.integration.AgentHarness;
import java.nio.file.Path;

// AgentHarness 自动初始化技能系统
AgentHarness agent = AgentHarness.builder()
    .apiKey("...")
    .build();

// 加载自定义技能目录
agent.loadSkillsFromDir(Path.of(".harness", "skills"));

// 查看匹配的技能
String userInput = "将 README.md 转换为 Word 文档";
List<Skill> matching = agent.getMatchingSkills(userInput);
System.out.println("匹配的技能: " + matching.stream().map(Skill::name).toList());

// 运行时自动注入匹配的技能
LoopResult result = agent.run(userInput).join();
```

#### 技能注入流程

```
用户输入 → get_matching_skills() → 匹配技能
    ↓
inject_skills() → 增强的 system prompt
    ↓
LLM 调用（包含技能指令）
```

#### 手动控制技能激活

```java
// 强制激活特定技能（即使不匹配 triggers）
agent.activateSkill("code-review");

// 停用技能
agent.deactivateSkill("code-review");
```

### 与记忆系统集成

- 技能内容被 VectorMemoryStore 索引，支持语义搜索
- 技能执行经验可保存为 MEMORY.md 记忆
- SystemPromptBuilder 将技能指令注入系统提示

### 与触发器集成

- Cron 触发器可指定使用特定技能
- Webhook 触发器可根据事件类型选择技能

### 与 MCP 集成

- MCP 工具可作为技能的可用工具
- 技能的 `tools` 字段可包含 MCP 工具名

```java
// 使用 MCP 工具的技能
agent.addMcpServer("github", "mcp-github");

// 技能文件中引用 MCP 工具
"""
---
name: github-ops
description: GitHub operations
tools:
  allowed: [read, grep, mcp_github]
  default_permission: allow
---
"""
```

## 下一步

- [02-agent-loop.md](./03-agent-loop.md) - 了解 Agent Loop
- [04-memory-system.md](./05-memory-system.md) - 了解记忆系统
- [06-trigger-system.md](./17-trigger-system.md) - 了解触发器系统
