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

```python
from harness.skills.progressive import SkillMetadata
from pathlib import Path

@dataclass
class SkillMetadata:
    name: str                    # 技能名称（必需）
    description: str             # 技能描述（必需）
    path: Path                   # 技能文件路径
    triggers: dict[str, list[str]] = field(default_factory=dict)  # 触发条件
    version: str = "1.0.0"       # 版本号
    
    # 内部缓存字段
    _skill: Skill | None = field(default=None, repr=False)  # 缓存的完整技能对象
    _loaded: bool = field(default=False, repr=False)        # 是否已加载完整内容
    
    def to_list_item(self) -> str:
        """格式化为技能列表项"""
        return f"- {self.name}: {self.description}"
    
    def matches(self, text: str) -> bool:
        """检查文本是否匹配此技能的触发条件"""
        # 实现细节：检查关键词和正则表达式匹配
        ...
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

```python
from harness.skills.registry import SkillRegistry
from pathlib import Path

class SkillRegistry:
    def __init__(self):
        """初始化技能注册表"""

    def add_skill_dir(self, directory: Path) -> None:
        """添加技能目录并自动加载所有技能"""

    def register(self, skill: Skill) -> None:
        """注册技能（同名技能按版本号覆盖）"""

    def unregister(self, name: str) -> bool:
        """注销技能，返回是否成功"""

    def get(self, name: str) -> Skill | None:
        """获取技能"""

    def list_skills(self) -> list[Skill]:
        """列出所有注册技能"""

    def find_matching_skills(self, user_input: str) -> list[Skill]:
        """根据用户输入查找匹配的技能"""

    def activate(self, skill_name: str) -> bool:
        """激活技能，返回是否成功"""

    def deactivate(self, skill_name: str) -> bool:
        """停用技能，返回是否成功"""

    def get_active_skills(self) -> list[Skill]:
        """获取所有激活的技能"""

    def clear_active(self) -> None:
        """清除所有激活的技能"""

    def is_tool_allowed(self, tool_name: str) -> bool:
        """检查工具是否被所有激活技能允许"""

    def reload(self) -> None:
        """重新加载所有技能目录"""

    def __len__(self) -> int:
        """返回注册技能数量"""

    def __contains__(self, name: str) -> bool:
        """检查技能是否已注册"""

    def __iter__(self):
        """迭代所有技能"""
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

```python
from harness.skills.progressive import LoadingLevel

class LoadingLevel:
    """Skill loading levels."""
    FRONTMATTER = 1  # Level 1: 仅加载元数据
    FULL_CONTENT = 2  # Level 2: 加载完整内容
    REFERENCES = 3    # Level 3: 加载引用文件
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

```python
from harness.skills.progressive import ProgressiveSkillLoader, SkillMetadata
from pathlib import Path

class ProgressiveSkillLoader:
    def __init__(self, cache_size: int = 50):
        """
        Args:
            cache_size: 内存中缓存的技能最大数量
        """

    def discover_skills(self, directory: Path) -> list[SkillMetadata]:
        """发现目录中的所有技能（Level 1 加载，仅读取 frontmatter）"""

    def load_full_content(self, metadata: SkillMetadata) -> Skill:
        """加载完整的技能内容（Level 2 加载）"""

    def match_skills(
        self,
        text: str,
        skills: list[SkillMetadata],
        max_matches: int = 3,
    ) -> list[SkillMetadata]:
        """根据用户输入文本匹配技能"""

    def load_with_references(
        self,
        metadata: SkillMetadata,
        reference_loader: callable | None = None,
    ) -> tuple[Skill, list[str]]:
        """加载技能及其所有引用文件（Level 3 加载）"""

    def build_skill_selection_prompt(
        self,
        skills: list[SkillMetadata],
        format_style: str = "list",
    ) -> str:
        """构建技能选择提示"""

    def estimate_tokens(self, skills: list[SkillMetadata | Skill], level: int = 1) -> int:
        """估算技能列表的 token 数量"""

    def clear_cache(self) -> None:
        """清除所有缓存技能"""
```

### 使用示例

```python
from pathlib import Path
from harness.skills.progressive import ProgressiveSkillLoader, SkillMetadata, LoadingLevel

# 创建加载器
loader = ProgressiveSkillLoader(cache_size=50)

# Level 1: 发现所有技能的元数据
skills_dir = Path(".harness/skills")
all_skills = loader.discover_skills(skills_dir)

# 构建技能选择提示
skill_list = loader.build_skill_selection_prompt(all_skills, format_style="list")
print(f"可用技能:\n{skill_list}")

# 根据用户输入匹配技能
user_input = "审查代码中的安全漏洞"
matched = loader.match_skills(user_input, all_skills, max_matches=3)

# Level 2: 加载完整内容
for skill_meta in matched:
    skill = loader.load_full_content(skill_meta)
    print(f"[{LoadingLevel.FULL_CONTENT}] {skill.name}: {skill.content[:100]}...")

# Level 3: 加载技能及其引用文件
for skill_meta in matched:
    skill, references = loader.load_with_references(skill_meta)
    print(f"[{LoadingLevel.REFERENCES}] {skill.name} 有 {len(references)} 个引用文件")

# 估算 token 使用
tokens = loader.estimate_tokens(matched, level=LoadingLevel.FULL_CONTENT)
print(f"估计 token 使用: {tokens}")

# 清除缓存
loader.clear_cache()
```

### AgentHarness 集成

`AgentHarness` 已内置渐进式技能加载，无需手动使用 `ProgressiveSkillLoader`：

```python
from harness import AgentHarness

agent = AgentHarness()

# 初始化时自动发现技能元数据 (Level 1)
# 从 ~/.harness/skills, ./.harness/skills 目录

# 查看已发现的技能（元数据，未加载完整内容）
for meta in agent.list_discovered_skills():
    print(f"- {meta.name}: {meta.description}")

# 按需加载技能完整内容 (Level 2)
agent.activate_skill("code-review")  # 触发 Level 2 加载

# run() 时自动加载匹配技能的完整内容
result = await agent.run("review this code")

# 查看已加载完整内容的技能
for skill in agent.list_skills():
    print(f"- {skill.name}: {len(skill.content)} chars")
```

**工作流程**：

1. **初始化**：`AgentHarness.__init__()` 调用 `_load_skill_metadata()` 发现所有技能元数据
2. **激活**：`activate_skill()` 触发 Level 2 加载，注册到 SkillRegistry
3. **运行**：`run()` 根据用户输入匹配技能，自动加载匹配技能的完整内容

### 技能去重

当多个技能目录中存在同名技能时，`_load_skill_metadata()` 会自动去重：

```python
# DEFAULT_SKILL_PATHS 扫描顺序（优先级从高到低）：
# 1. ~/.harness/skills      - 用户级（最高优先级）
# 2. ./.harness/skills      - 项目级

# 如果 ~/.harness/skills/convert/SKILL.md 和 ./.harness/skills/convert/SKILL.md 都存在，
# 只有第一个被加载（用户级优先），后续同名技能会被跳过
```

**去重逻辑**：

```python
# SDK 内部实现 (harness/sdk/harness.py)
for directory in DEFAULT_SKILL_PATHS:
    if directory.exists():
        skills = self._progressive_loader.discover_skills(directory)
        for meta in skills:
            if meta.name not in self._skill_metadata_by_name:
                self._skill_metadata.append(meta)
                self._skill_metadata_by_name[meta.name] = meta
            else:
                logger.info(f"Skipping duplicate skill: {meta.name} from {meta.path}")
```

**设计原则**：用户级技能 (`~/.harness/skills`) 优先级最高，确保用户可以覆盖项目级技能。

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

```python
from harness.skills.injector import SkillInjector, InjectionConfig
from harness.skills.registry import SkillRegistry

class SkillInjector:
    def __init__(self, registry: SkillRegistry, config: InjectionConfig | None = None):
        """
        Args:
            registry: 技能注册表
            config: 注入配置（可选）
        """

    def inject_skills(
        self,
        system_prompt: str,
        user_input: str,
        context: dict | None = None,
    ) -> str:
        """
        将技能注入系统提示

        Args:
            system_prompt: 原始系统提示
            user_input: 用户输入文本
            context: 可选上下文字典

        Returns:
            注入技能后的系统提示
        """

    def get_tool_filter(self) -> Callable[[str], bool]:
        """获取工具过滤函数，返回 True 表示工具被允许"""

    def get_injection_preview(
        self,
        system_prompt: str,
        user_input: str,
    ) -> dict:
        """获取注入预览信息"""

@dataclass
class InjectionConfig:
    max_skills_per_prompt: int = 5          # 每个提示最大技能数
    max_skill_length: int = 2000            # 每个技能最大长度
    inject_method: str = "append"           # append, prepend, section
    skill_separator: str = "\n\n---\n\n"    # 技能分隔符
```

### 注入格式

注入后的技能格式包含技能目录路径，让 LLM 知道脚本位置：

```markdown
## Skill: md-to-word

Convert Markdown to Word documents.

**Skill Directory**: `/home/user/.harness/skills/md-to-word`

### Available Tools
bash
```

**设计理念**：
- **运行时提供路径**：遵循业界标准，在运行时提供路径信息而非使用占位符替换
- **脚本定位**：LLM 可以使用 `bash` 工具执行技能目录中的脚本
- **相关提交**：`0a9e89f`

## Skill 基类

```python
from harness.skills.base import Skill, SkillTrigger, SkillTools, SkillParameter

class Skill:
    name: str                          # 技能名称
    description: str                   # 技能描述
    content: str                       # 技能完整内容（Markdown）
    triggers: SkillTrigger             # 触发条件
    tools: SkillTools                  # 工具配置
    parameters: list[SkillParameter]   # 参数列表
    version: str = "1.0.0"             # 版本号
    author: str = ""                   # 作者
    metadata: dict[str, Any]           # 元数据
    source_path: str | None            # 源文件路径
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

```python
from harness import AgentHarness

# AgentHarness 自动初始化技能系统
agent = AgentHarness(api_key="...")

# 加载自定义技能目录
from pathlib import Path
agent.load_skills_from_dir(Path("./.harness/skills"))

# 查看匹配的技能
user_input = "将 README.md 转换为 Word 文档"
matching = agent.get_matching_skills(user_input)
print(f"匹配的技能: {[s.name for s in matching]}")

# 运行时自动注入匹配的技能
result = await agent.run(user_input)
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

```python
# 强制激活特定技能（即使不匹配 triggers）
agent.activate_skill("code-review")

# 停用技能
agent.deactivate_skill("code-review")
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

```python
# 使用 MCP 工具的技能
agent.add_mcp_server("github", command="mcp-github")

# 技能文件中引用 MCP 工具
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

- [02-agent-loop.md](./02-agent-loop.md) - 了解 Agent Loop
- [04-memory-system.md](./04-memory-system.md) - 了解记忆系统
- [06-trigger-system.md](./06-trigger-system.md) - 了解触发器系统
