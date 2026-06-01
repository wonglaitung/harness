# 05 - Skills System 技能系统

## 概述

Skills System 定义了代理的行为边界和能力约束，通过结构化的指令文件指导 LLM 如何执行特定任务。

## 设计理念

### 什么是 Skill？

Skill 是一个**结构化、模块化的能力单元**，包含：

- **触发条件**: 何时激活这个技能
- **工具权限**: 可使用的工具集合
- **行为指导**: 具体的执行步骤和规则
- **输出规范**: 预期的输出格式

### Skill vs Prompt 的区别

| 特性 | 传统 Prompt | Skill |
|------|-------------|-------|
| 结构 | 自由文本 | 结构化文件 |
| 持久性 | 单次使用 | 可持久存储 |
| 工具绑定 | 手动指定 | 自动绑定 |
| 可组合性 | 低 | 高（可组合多个 Skill） |
| 可学习性 | 无 | 支持自动生成 |

### Skill vs MCP 的区别

Skills 和 MCP (Model Context Protocol) 是完全不同的机制：

| 特性 | Skills | MCP |
|------|--------|-----|
| 目的 | 注入 prompt 指令 | 连接外部工具服务器 |
| 触发方式 | 关键词/正则匹配用户输入 | 不触发，工具始终可用 |
| 工作层级 | System Prompt | Tool Registry |
| 选择权 | 代码匹配决定 | LLM 自主决定 |

**Skills 工作流程**：

```
用户输入 → 关键词匹配 → 注入技能到 prompt → LLM 看到指令
"review code" → 匹配 "review" → 注入代码审查技能
```

**MCP 工作流程**：

```
配置服务器 → 工具注册到 Registry → LLM 自主选择使用
无需匹配，工具始终在工具列表中，LLM 自己决定用不用
```

**示例对比**：

```python
# Skills: 需要匹配触发
skill = Skill(
    name="code-review",
    triggers=SkillTrigger(keywords=["review"]),
    content="你是代码审查专家...",
)
# 只有用户输入包含 "review" 时才会注入

# MCP: 无需触发，工具始终可用
manager = MCPManager()
await manager.connect_server("filesystem")
# 现在 read_file, write_file 等工具始终可用
# LLM 根据用户请求自主决定调用哪个
```

**适用场景**：

- **Skills**: 需要注入特定行为指令、改变 LLM 的工作方式
- **MCP**: 扩展工具能力、连接外部服务

MCP 的设计更简洁 - 工具注册后，完全由 LLM 根据上下文决定是否调用，不需要代码层面的触发判断。

## Skill 文件格式

### 标准 Skill 格式

```markdown
---
name: code-review
description: Review code changes and provide structured feedback
version: 1.0.0
author: harness-team
triggers:
  keywords:
    - "review"
    - "check code"
    - "code review"
  patterns:
    - "review this"
    - "check my changes"
tools:
  allowed:
    - read
    - grep
    - glob
    - bash
  restricted:
    - write
    - edit
parameters:
  severity_levels:
    type: array
    default: ["critical", "high", "medium", "low"]
  include_suggestions:
    type: boolean
    default: true
---

# Code Review Skill

## Purpose
You are a code reviewer. Your task is to analyze code changes and provide structured, actionable feedback.

## Workflow

1. **Identify Scope**
   - Ask the user which files or changes to review
   - Use `glob` to find relevant files if needed

2. **Read Code**
   - Use `read` to examine each file
   - Focus on changed sections if possible

3. **Analyze**
   Check for:
   - **Bugs**: Logic errors, edge cases, null handling
   - **Security**: Input validation, SQL injection, XSS
   - **Performance**: N+1 queries, unnecessary loops
   - **Style**: Naming conventions, complexity
   - **Architecture**: Module boundaries, dependencies

4. **Provide Feedback**
   Format each issue as:

   ```
   **Severity**: [Critical|High|Medium|Low]
   **Category**: [Bug|Security|Performance|Style|Architecture]
   **File**: path/to/file
   **Line**: line_number
   **Issue**: Description of the problem
   **Suggestion**: How to fix it
   **Code Example**: (optional) Suggested fix snippet
   ```

## Rules

- Never modify code directly (review-only)
- Always provide severity and category
- Include line numbers when possible
- Be specific, not vague
- Prioritize critical issues first

## Examples

### Good Review Output
```json
[
  {
    "severity": "High",
    "category": "Security",
    "file": "src/api/auth.py",
    "line": 45,
    "issue": "Password is logged in debug mode",
    "suggestion": "Remove password from log or disable debug mode"
  }
]
```

### Bad Review Output (avoid)
```
The code looks bad. You should fix it.
```
```

### 简化 Skill 格式

```markdown
---
name: summarize
description: Summarize text or content concisely
---

# Summarize Skill

Summarize the given content in 3-5 bullet points.
Focus on key information, ignore fluff.
Use clear, simple language.
```

## 核心组件

### 5.1 Skill 类定义

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable
from pathlib import Path
import yaml
import re

@dataclass
class SkillTrigger:
    """技能触发器"""
    keywords: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)  # 触发工具调用

    def matches(self, text: str) -> bool:
        """检查是否匹配触发条件"""
        # 关键词匹配
        text_lower = text.lower()
        for keyword in self.keywords:
            if keyword.lower() in text_lower:
                return True

        # 正则模式匹配
        for pattern in self.patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        return False


@dataclass
class SkillTools:
    """技能工具配置"""
    allowed: List[str] = field(default_factory=list)
    restricted: List[str] = field(default_factory=list)
    default_permission: str = "allow"  # allow, deny, ask

    def is_allowed(self, tool_name: str) -> bool:
        """检查工具是否允许"""
        if tool_name in self.restricted:
            return False
        if not self.allowed:
            return self.default_permission == "allow"
        return tool_name in self.allowed


@dataclass
class SkillParameter:
    """技能参数"""
    name: str
    type: str
    default: Any = None
    description: str = ""
    required: bool = False


@dataclass
class Skill:
    """技能定义"""
    name: str
    description: str
    content: str
    triggers: SkillTrigger = field(default_factory=SkillTrigger)
    tools: SkillTools = field(default_factory=SkillTools)
    parameters: List[SkillParameter] = field(default_factory=list)
    version: str = "1.0.0"
    author: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_path: Optional[str] = None

    @classmethod
    def from_file(cls, path: Path) -> "Skill":
        """从文件加载技能"""
        content = path.read_text()

        # 解析 frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])
                body = parts[2].strip()
            else:
                frontmatter = {}
                body = content
        else:
            frontmatter = {}
            body = content

        # 解析触发器
        triggers_data = frontmatter.get("triggers", {})
        triggers = SkillTrigger(
            keywords=triggers_data.get("keywords", []),
            patterns=triggers_data.get("patterns", []),
            tools=triggers_data.get("tools", [])
        )

        # 解析工具配置
        tools_data = frontmatter.get("tools", {})
        tools = SkillTools(
            allowed=tools_data.get("allowed", []),
            restricted=tools_data.get("restricted", []),
            default_permission=tools_data.get("default_permission", "allow")
        )

        # 解析参数
        parameters = []
        params_data = frontmatter.get("parameters", {})
        for param_name, param_info in params_data.items():
            parameters.append(SkillParameter(
                name=param_name,
                type=param_info.get("type", "string"),
                default=param_info.get("default"),
                description=param_info.get("description", ""),
                required=param_info.get("required", False)
            ))

        return cls(
            name=frontmatter.get("name", path.stem),
            description=frontmatter.get("description", ""),
            content=body,
            triggers=triggers,
            tools=tools,
            parameters=parameters,
            version=frontmatter.get("version", "1.0.0"),
            author=frontmatter.get("author", ""),
            metadata=frontmatter.get("metadata", {}),
            source_path=str(path)
        )

    def to_file(self, path: Path):
        """保存技能到文件"""
        frontmatter = {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "triggers": {
                "keywords": self.triggers.keywords,
                "patterns": self.triggers.patterns,
                "tools": self.triggers.tools
            },
            "tools": {
                "allowed": self.tools.allowed,
                "restricted": self.tools.restricted
            },
            "metadata": self.metadata
        }

        content = f"---\n{yaml.dump(frontmatter, default_flow_style=False)}---\n\n{self.content}"
        path.write_text(content)

    def should_activate(self, user_input: str, context: dict = None) -> bool:
        """判断是否应该激活"""
        return self.triggers.matches(user_input)
```

### 5.2 Skill Registry

```python
class SkillRegistry:
    """技能注册表"""

    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._active_skills: List[str] = []
        self._skill_dirs: List[Path] = []

    def add_skill_dir(self, directory: Path):
        """添加技能目录"""
        self._skill_dirs.append(directory)
        self._load_from_dir(directory)

    def _load_from_dir(self, directory: Path):
        """从目录加载所有技能"""
        if not directory.exists():
            return

        for skill_file in directory.glob("*.md"):
            skill = Skill.from_file(skill_file)
            self.register(skill)

    def register(self, skill: Skill):
        """注册技能"""
        if skill.name in self._skills:
            # 版本检查
            existing = self._skills[skill.name]
            if skill.version > existing.version:
                self._skills[skill.name] = skill
        else:
            self._skills[skill.name] = skill

    def unregister(self, name: str):
        """注销技能"""
        if name in self._skills:
            del self._skills[name]

    def get(self, name: str) -> Optional[Skill]:
        """获取技能"""
        return self._skills.get(name)

    def list_skills(self) -> List[Skill]:
        """列出所有技能"""
        return list(self._skills.values())

    def find_matching_skills(self, user_input: str) -> List[Skill]:
        """查找匹配的技能"""
        matches = []
        for skill in self._skills.values():
            if skill.should_activate(user_input):
                matches.append(skill)
        return matches

    def activate(self, skill_name: str):
        """激活技能"""
        if skill_name in self._skills:
            self._active_skills.append(skill_name)

    def deactivate(self, skill_name: str):
        """关闭技能"""
        if skill_name in self._active_skills:
            self._active_skills.remove(skill_name)

    def get_active_skills(self) -> List[Skill]:
        """获取活跃技能"""
        return [self._skills[name] for name in self._active_skills if name in self._skills]

    def get_allowed_tools(self, tool_name: str) -> bool:
        """检查工具在当前活跃技能中是否允许"""
        for skill in self.get_active_skills():
            if not skill.tools.is_allowed(tool_name):
                return False
        return True

    def reload(self):
        """重新加载所有技能"""
        self._skills.clear()
        for directory in self._skill_dirs:
            self._load_from_dir(directory)
```

### 5.3 Skill Injector

```python
@dataclass
class InjectionConfig:
    """注入配置"""
    max_skills_per_prompt: int = 5
    max_skill_length: int = 2000
    inject_method: str = "append"  # append, prepend, interleaved
    skill_separator: str = "\n\n---\n\n"


class SkillInjector:
    """技能注入器"""

    def __init__(
        self,
        registry: SkillRegistry,
        config: InjectionConfig = None
    ):
        self.registry = registry
        self.config = config or InjectionConfig()

    def inject_skills(
        self,
        system_prompt: str,
        user_input: str,
        context: dict = None
    ) -> str:
        """将技能注入系统提示"""

        # 找到匹配的技能
        matching_skills = self.registry.find_matching_skills(user_input)

        # 加上已经激活的技能
        active_skills = self.registry.get_active_skills()

        # 合并，去重
        all_skills = list(set(matching_skills + active_skills))

        # 限制数量
        all_skills = all_skills[:self.config.max_skills_per_prompt]

        if not all_skills:
            return system_prompt

        # 构建技能提示
        skill_prompts = []
        for skill in all_skills:
            skill_prompt = self._format_skill(skill)
            # 截断过长的技能
            if len(skill_prompt) > self.config.max_skill_length:
                skill_prompt = skill_prompt[:self.config.max_skill_length] + "\n...[truncated]"
            skill_prompts.append(skill_prompt)

        combined_skills = self.config.skill_separator.join(skill_prompts)

        # 根据注入方法组合
        if self.config.inject_method == "append":
            return system_prompt + self.config.skill_separator + combined_skills
        elif self.config.inject_method == "prepend":
            return combined_skills + self.config.skill_separator + system_prompt
        elif self.config.inject_method == "section":
            return f"{system_prompt}\n\n# Active Skills\n\n{combined_skills}"
        else:
            return system_prompt + self.config.skill_separator + combined_skills

    def _format_skill(self, skill: Skill) -> str:
        """格式化单个技能"""
        return f"""## Skill: {skill.name}

{skill.content}

### Available Tools
{', '.join(skill.tools.allowed) if skill.tools.allowed else 'All tools'}
"""

    def get_tool_filter(self) -> Callable[[str], bool]:
        """获取工具过滤器"""
        return lambda tool_name: self.registry.get_allowed_tools(tool_name)
```

### 5.4 Skill Loader

```python
## 技能文件存放位置

### 默认搜索路径

Harness 会自动从以下目录加载 Skill 文件（按优先级排序）：

```
优先级（高→低）
    │
    ├── 1. ./.agent/skills/          # 项目级技能（最高优先级，随项目提交）
    │
    ├── 2. ./skills/                 # 项目级技能（备选位置）
    │
    ├── 3. ~/.harness/skills/        # 用户级技能（个人技能库）
    │
    └── 4. ~/.harness/shared-skills/ # 共享技能（团队共享）
```

### 目录结构示例

```
my-project/
├── .agent/
│   ├── skills/
│   │   ├── code-review.md        # 项目专用代码审查技能
│   │   ├── deploy.md             # 项目部署技能
│   │   └── api-test.md           # API 测试技能
│   └── AGENTS.md                 # 项目上下文说明
│
├── skills/                       # 备选位置
│   └── custom-workflow.md
│
└── ...

~/.harness/
├── skills/                       # 用户个人技能库
│   ├── summarize.md
│   ├── translate.md
│   └── my-helpers/
│       └── data-format.md
│
└── shared-skills/                # 团队共享技能
    └── team-conventions.md
```

### 项目配置文件

在项目根目录创建 `.agent/config.yaml` 进行项目级配置：

```yaml
# .agent/config.yaml
skills:
  directories:
    - ./.agent/skills
    - ./skills
  auto_load: true

mcp:
  config: ./.agent/mcp.json        # MCP 配置文件路径

memory:
  type: file
  path: ./.agent/memory
```

### 使用示例

```python
from harness import AgentHarness

# 方式1：自动加载（推荐）
# 自动加载 .agent/skills/, skills/, ~/.harness/skills/ 中的技能
agent = AgentHarness()

# 方式2：指定配置文件
agent = AgentHarness.from_config("./.agent/config.yaml")

# 方式3：手动加载特定技能
agent = AgentHarness()
agent.load_skill("./.agent/skills/code-review.md")

# 方式4：添加额外技能目录
agent.skills.add_skill_dir(Path("./custom-skills"))
```

### 与 Claude Code 兼容

Harness 的 `.agent/` 目录设计兼容 Claude Code 的项目结构：

```
.agent/
├── AGENTS.md       # Claude Code 项目上下文
├── skills/         # Harness 技能文件
├── mcp.json        # MCP 配置（兼容 Claude Code 格式）
├── config.yaml     # Harness 配置
└── memory/         # 记忆文件
```

    def load_from_path(self, path: str):
        """从指定路径加载"""
        p = Path(path).expanduser()

        if p.is_file() and p.suffix == ".md":
            skill = Skill.from_file(p)
            self.registry.register(skill)
            self.loaded_paths.append(p)
        elif p.is_dir():
            self.registry.add_skill_dir(p)
            self.loaded_paths.append(p)

    def load_from_url(self, url: str):
        """从 URL 加载技能"""
        import aiohttp

        async def _load():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    content = await response.text()

            # 临时文件
            temp_path = Path("/tmp") / Path(url).name
            temp_path.write_text(content)

            skill = Skill.from_file(temp_path)
            self.registry.register(skill)

        # 异步加载
        asyncio.create_task(_load())

    def discover_skills(self, directory: Path) -> List[Path]:
        """发现目录中的所有技能文件"""
        skill_files = []

        # 搜索 .md 文件
        for md_file in directory.rglob("*.md"):
            # 检查是否有 skill frontmatter
            content = md_file.read_text()
            if content.startswith("---") and "name:" in content.split("---")[1]:
                skill_files.append(md_file)

        return skill_files
```

### 5.5 Skill Generator (自学习)

```python
@dataclass
class PatternObservation:
    """模式观察"""
    user_inputs: List[str]
    tool_sequences: List[List[ToolCall]]
    outcomes: List[str]
    frequency: int


class SkillGenerator:
    """技能生成器（从重复模式自动生成技能）"""

    def __init__(
        self,
        llm_client: LLMClient,
        registry: SkillRegistry,
        observation_window: int = 100
    ):
        self.llm = llm_client
        self.registry = registry
        self.observation_window = observation_window
        self.patterns: Dict[str, PatternObservation] = {}

    def observe(self, session: Session):
        """观察会话中的模式"""
        # 提取用户输入和工具序列
        user_inputs = []
        tool_sequences = []
        current_tools = []

        for msg in session.messages:
            if msg.role == "user":
                if current_tools:
                    tool_sequences.append(current_tools)
                    current_tools = []
                user_inputs.append(msg.content)
            elif msg.role == "assistant" and msg.tool_calls:
                current_tools.extend(msg.tool_calls)

        if len(user_inputs) >= 2 and len(tool_sequences) >= 2:
            # 检查是否有重复模式
            self._analyze_pattern(user_inputs, tool_sequences)

    def _analyze_pattern(
        self,
        inputs: List[str],
        tool_seqs: List[List[ToolCall]]
    ):
        """分析是否有可学习的模式"""

        # 简单模式检测：相似输入 + 相似工具序列
        # 提取关键词
        keywords = self._extract_common_keywords(inputs)

        # 检查工具序列相似性
        common_tools = self._extract_common_tools(tool_seqs)

        if keywords and common_tools:
            pattern_key = f"{keywords}_{common_tools}"
            if pattern_key in self.patterns:
                self.patterns[pattern_key].frequency += 1
            else:
                self.patterns[pattern_key] = PatternObservation(
                    user_inputs=inputs,
                    tool_sequences=tool_seqs,
                    outcomes=[],
                    frequency=1
                )

    def _extract_common_keywords(self, inputs: List[str]) -> List[str]:
        """提取共同关键词"""
        from collections import Counter

        all_words = []
        for input_text in inputs:
            words = input_text.lower().split()
            all_words.extend(words)

        # 高频词
        counter = Counter(all_words)
        return [w for w, c in counter.most_common(5) if c >= 2]

    def _extract_common_tools(self, tool_seqs: List[List[ToolCall]]) -> List[str]:
        """提取共同工具"""
        tool_counts = Counter()
        for seq in tool_seqs:
            for call in seq:
                tool_counts[call.name] += 1

        return [t for t, c in tool_counts.most_common(5) if c >= 2]

    async def generate_skill(self, pattern_key: str) -> Optional[Skill]:
        """从模式生成技能"""

        if self.patterns[pattern_key].frequency < 3:
            # 频率太低，不值得生成技能
            return None

        pattern = self.patterns[pattern_key]

        # 使用 LLM 生成技能描述
        prompt = f"""Generate a skill definition from this observed pattern:

User inputs (similar):
{pattern.user_inputs[:3]}

Tool sequences used:
{[tc.name for tc in pattern.tool_sequences[0]]}

Create a skill YAML frontmatter and content that captures this pattern.
Format as:

---
name: [skill name]
description: [brief description]
triggers:
  keywords: [list of trigger keywords]
tools:
  allowed: [tools used in pattern]
---

[Skill content/instructions]

Output only the skill markdown file content."""

        response = await self.llm.call(
            Context(
                system_prompt="You generate skill definitions from patterns.",
                messages=[Message(role="user", content=prompt)],
                tools=[]
            )
        )

        # 解析生成的技能
        try:
            skill_content = response.message.content

            # 保存到文件
            skill_name = f"auto_{pattern_key.replace('_', '-')}"
            skill_path = Path("~/.harness/skills").expanduser() / f"{skill_name}.md"
            skill_path.parent.mkdir(parents=True, exist_ok=True)
            skill_path.write_text(skill_content)

            # 加载到注册表
            skill = Skill.from_file(skill_path)
            self.registry.register(skill)

            return skill
        except Exception as e:
            print(f"Error generating skill: {e}")
            return None

    async def check_and_generate(self, session: Session):
        """检查模式并生成技能"""
        self.observe(session)

        # 检查是否有高频模式
        for pattern_key, pattern in self.patterns.items():
            if pattern.frequency >= 3:
                skill = await self.generate_skill(pattern_key)
                if skill:
                    # 清除已处理的模式
                    del self.patterns[pattern_key]
                    return skill

        return None
```

## 预置技能库

### 基础技能

```
skills/
├── general/
│   ├── think.md          # 思考和规划
│   ├── summarize.md      # 摘要内容
│   ├── explain.md        # 解释概念
│   └── translate.md      # 翻译
│
├── coding/
│   ├── code-review.md    # 代码审查
│   ├── debug.md          # 调试分析
│   ├── refactor.md       # 重构建议
│   ├── test-gen.md       # 测试生成
│   └── doc-gen.md        # 文档生成
│
├── research/
│   ├── web-search.md     # 网络搜索
│   ├── analyze.md        # 数据分析
│   └── report.md         # 报告生成
│
└── workflow/
│   ├── plan.md           # 任务规划
│   ├── execute.md        # 执行流程
│   ├── review.md         # 结果审查
│   └── iterate.md        # 迭代改进
```

### 内置技能示例

#### think.md

```markdown
---
name: think
description: Think through a problem step by step before acting
triggers:
  keywords:
    - "think"
    - "plan"
    - "analyze"
    - "consider"
tools:
  allowed: []
---

# Think Skill

Before taking any action, think through the problem:

1. **Understand the Request**
   - What is the user asking?
   - What context is available?
   - What constraints exist?

2. **Identify Key Steps**
   - Break down the task into steps
   - Order steps logically
   - Identify dependencies

3. **Consider Alternatives**
   - What are different approaches?
   - What are trade-offs?
   - Which approach is best?

4. **Plan Execution**
   - What tools are needed?
   - What information to gather?
   - What order to execute?

Output your thinking in a structured format before proceeding.
```

#### code-review.md

```markdown
---
name: code-review
description: Review code for bugs, security, and quality issues
triggers:
  keywords:
    - "review"
    - "check code"
    - "analyze code"
  patterns:
    - "review this (file|code)"
    - "check (my|the) (changes|code)"
tools:
  allowed:
    - read
    - grep
    - glob
  restricted:
    - write
    - edit
    - bash
---

# Code Review Skill

## Purpose
Analyze code and provide actionable feedback on quality, security, and correctness.

## Review Categories

### 1. Bugs & Logic Errors
- Incorrect logic
- Edge case handling
- Null/undefined checks
- Race conditions

### 2. Security
- Input validation
- SQL injection
- XSS vulnerabilities
- Authentication/authorization
- Data exposure

### 3. Performance
- N+1 queries
- Unnecessary loops
- Memory leaks
- Blocking operations

### 4. Style & Maintainability
- Naming conventions
- Code complexity
- Documentation
- Duplicate code

### 5. Architecture
- Module boundaries
- Dependency issues
- API design
- Test coverage

## Output Format

For each issue found:

```
**Severity**: Critical|High|Medium|Low
**Category**: Bug|Security|Performance|Style|Architecture
**File**: path/to/file:line_number
**Issue**: [clear description]
**Suggestion**: [how to fix]
**Example**:
  [code snippet if helpful]
```

## Rules

1. Review only - never modify code
2. Always include severity and category
3. Include line numbers when possible
4. Be specific and actionable
5. Prioritize critical issues
```

#### debug.md

```markdown
---
name: debug
description: Debug and diagnose issues in code
triggers:
  keywords:
    - "debug"
    - "fix"
    - "error"
    - "bug"
    - "issue"
  patterns:
    - "(fix|debug) (this|the) (error|bug|issue)"
    - "(why|what) is (wrong|broken|failing)"
tools:
  allowed:
    - read
    - grep
    - glob
    - bash
---

# Debug Skill

## Debugging Workflow

1. **Gather Information**
   - What is the error message?
   - What was expected vs actual behavior?
   - When does it occur?

2. **Locate the Problem**
   - Search for error text in files
   - Find relevant code sections
   - Check recent changes

3. **Analyze**
   - Read the problematic code
   - Trace execution flow
   - Identify root cause

4. **Propose Fix**
   - Explain what's wrong
   - Suggest specific changes
   - Show corrected code

5. **Verify**
   - Check for similar issues elsewhere
   - Consider edge cases
   - Verify fix doesn't break other things

## Output Format

```
## Diagnosis

**Error**: [error message or behavior]
**Location**: file:line
**Root Cause**: [explanation]

## Proposed Fix

**File**: path/to/file
**Change**: [description]
**Code**:
  [corrected code snippet]

## Prevention

[Suggestions to prevent similar issues]
```
```

## Skill 组合

```python
class SkillComposer:
    """技能组合器"""

    def compose(
        self,
        skills: List[Skill],
        composition_type: str = "sequential"
    ) -> Skill:
        """组合多个技能"""

        if composition_type == "sequential":
            # 顺序执行
            combined_content = "# Combined Skill: Sequential Execution\n\n"
            combined_content += "Execute the following skills in order:\n\n"

            for i, skill in enumerate(skills, 1):
                combined_content += f"## Step {i}: {skill.name}\n\n{skill.content}\n\n"

            # 合并工具
            all_allowed = []
            all_restricted = []
            for skill in skills:
                all_allowed.extend(skill.tools.allowed)
                all_restricted.extend(skill.tools.restricted)

            return Skill(
                name=f"combined_{skills[0].name}_sequence",
                description=f"Sequential execution: {', '.join(s.name for s in skills)}",
                content=combined_content,
                tools=SkillTools(
                    allowed=list(set(all_allowed)),
                    restricted=list(set(all_restricted))
                )
            )

        elif composition_type == "parallel":
            # 并行执行
            combined_content = "# Combined Skill: Parallel Analysis\n\n"
            combined_content += "Apply the following perspectives simultaneously:\n\n"

            for skill in skills:
                combined_content += f"## {skill.name}\n\n{skill.content}\n\n"

            return Skill(
                name=f"combined_{skills[0].name}_parallel",
                description=f"Parallel analysis: {', '.join(s.name for s in skills)}",
                content=combined_content
            )

        return None
```

## 测试

```python
@pytest.fixture
def skill_registry():
    registry = SkillRegistry()
    registry.add_skill_dir(Path("tests/fixtures/skills"))
    return registry

def test_skill_loading(skill_registry):
    skill = skill_registry.get("code-review")
    assert skill is not None
    assert skill.name == "code-review"

def test_skill_trigger(skill_registry):
    matches = skill_registry.find_matching_skills("review this code")
    assert len(matches) > 0
    assert any(s.name == "code-review" for s in matches)

def test_skill_tool_filter(skill_registry):
    skill_registry.activate("code-review")

    assert skill_registry.get_allowed_tools("read")
    assert not skill_registry.get_allowed_tools("write")

def test_skill_injection(skill_registry):
    injector = SkillInjector(skill_registry)

    prompt = "You are an AI assistant."
    user_input = "review this code"

    result = injector.inject_skills(prompt, user_input)

    assert "code-review" in result
    assert len(result) > len(prompt)
```

---

## Skill 冲突解决

多个 Skill 同时激活可能导致指令冲突。实现优先级 + 互斥 + 融合策略。

```python
@dataclass
class SkillPriority:
    """技能优先级"""
    skill_name: str
    priority: int = 0           # 数值越高优先级越高
    exclusive: bool = False     # 是否互斥（激活时禁用其他）
    conflicts_with: List[str] = field(default_factory=list)


class SkillConflictResolver:
    """技能冲突解决器"""

    def __init__(self, registry: SkillRegistry):
        self.registry = registry
        self.priorities: Dict[str, SkillPriority] = {}

    def set_priority(self, priority: SkillPriority):
        """设置技能优先级"""
        self.priorities[priority.skill_name] = priority

    def resolve(self, matched_skills: List[Skill], user_input: str) -> List[Skill]:
        """解决冲突，返回最终激活的技能"""

        if not matched_skills:
            return []

        # 1. 检查互斥技能
        for skill in matched_skills:
            priority = self.priorities.get(skill.name)
            if priority and priority.exclusive:
                return [skill]

        # 2. 检查冲突对
        result = []
        for skill in matched_skills:
            priority = self.priorities.get(skill.name)

            if priority:
                has_conflict = any(
                    s.name in priority.conflicts_with
                    for s in result
                )
                if has_conflict:
                    continue

            result.append(skill)

        # 3. 按优先级排序，保留前 N 个
        result.sort(
            key=lambda s: self.priorities.get(s.name, SkillPriority(s.name)).priority,
            reverse=True
        )

        return result[:2]  # 最多激活 2 个

    def merge_prompts(self, system_prompt: str, skills: List[Skill]) -> str:
        """融合多个技能的提示"""
        if not skills:
            return system_prompt

        if len(skills) == 1:
            return f"{system_prompt}\n\n# Active Skill: {skills[0].name}\n\n{skills[0].content}"

        skill_sections = []
        for i, skill in enumerate(skills, 1):
            skill_sections.append(f"## Skill {i}: {skill.name}\n\n{skill.content}")

        return f"{system_prompt}\n\n# Active Skills\n\n" + "\n\n".join(skill_sections)


# 使用示例
resolver = SkillConflictResolver(registry)

resolver.set_priority(SkillPriority(
    skill_name="code-review",
    priority=10,
    conflicts_with=["debug"]
))

resolver.set_priority(SkillPriority(
    skill_name="think",
    priority=100,
    exclusive=True
))

matched = registry.find_matching_skills("review and debug this code")
final_skills = resolver.resolve(matched, user_input)
```

---

## Skill 自学习的人机协作机制

自动生成的 Skill 质量不可控，可能污染 System Prompt 或引入安全漏洞。自学习 Skill 必须进入 Draft 状态，经过人工审核后才能激活。

```python
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from datetime import datetime

class SkillStatus(Enum):
    DRAFT = "draft"        # 草稿，等待审核
    PENDING = "pending"    # 待审核
    APPROVED = "approved"  # 已批准，可激活
    REJECTED = "rejected"  # 已拒绝


class SkillReviewManager:
    """技能审核管理器"""

    def __init__(
        self,
        draft_dir: str = "~/.harness/skills/drafts",
        approved_dir: str = "~/.harness/skills/approved"
    ):
        self.draft_dir = Path(draft_dir).expanduser()
        self.approved_dir = Path(approved_dir).expanduser()
        self.draft_dir.mkdir(parents=True, exist_ok=True)
        self.approved_dir.mkdir(parents=True, exist_ok=True)

    async def submit_for_review(self, skill: Skill) -> str:
        """提交技能审核"""
        draft_id = f"draft_{skill.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        draft_path = self.draft_dir / f"{draft_id}.md"
        skill.to_file(draft_path)

        return draft_id

    def list_pending(self) -> List["DraftSkill"]:
        """列出待审核的技能"""
        pending = []
        for draft_file in self.draft_dir.glob("*.md"):
            meta = self._load_meta(draft_file)
            if meta.get("status") == SkillStatus.PENDING.value:
                skill = Skill.from_file(draft_file)
                pending.append(DraftSkill(skill=skill, status=SkillStatus.PENDING))
        return pending

    async def approve(self, draft_id: str, reviewer: str = "user") -> bool:
        """批准技能"""
        draft_path = self.draft_dir / f"{draft_id}.md"
        if not draft_path.exists():
            return False

        skill = Skill.from_file(draft_path)
        approved_path = self.approved_dir / f"{skill.name}.md"
        skill.to_file(approved_path)

        draft_path.unlink()
        return True

    async def reject(self, draft_id: str, reason: str) -> bool:
        """拒绝技能"""
        draft_path = self.draft_dir / f"{draft_id}.md"
        if not draft_path.exists():
            return False

        meta = self._load_meta(draft_path)
        meta["status"] = SkillStatus.REJECTED.value
        meta["rejection_reason"] = reason
        self._save_meta(draft_path, meta)

        return True


# CLI 命令
# harness skill review --list          # 列出待审核
# harness skill approve <draft_id>      # 批准
# harness skill reject <draft_id> -r "不安全"
```

---

---

## 渐进式技能加载 ✅ 已实现

渐进式技能加载通过三级加载机制优化上下文使用，避免一次性加载所有技能内容消耗大量 token。

### 设计原理

```
Level 1: Frontmatter Only (~100 tokens)
    ├── 读取 YAML frontmatter：name, description
    └── 模型可见技能列表，选择激活

Level 2: Full Content (~1000-2000 tokens)
    ├── 加载完整 skill.md
    └── 仅在模型确定需要时加载

Level 3: Reference Files (按需)
    └── 加载技能引用的外部文件
```

### 使用方式

```python
from harness.skills import ProgressiveSkillLoader, LoadingLevel

# 创建加载器
loader = ProgressiveSkillLoader(skills_dir=Path(".agent/skills"))

# Level 1: 发现技能（仅 frontmatter）
skills = await loader.discover_skills()
for skill in skills:
    print(f"{skill.name}: {skill.description}")  # ~100 tokens

# Level 2: 加载完整内容
full_skill = await loader.load_full_content(skills[0])

# Level 3: 加载引用文件
skill_with_refs = await loader.load_with_references(skills[0])

# 匹配技能
matched = loader.match_skills("review this code", skills)
```

### SkillMetadata

```python
from harness.skills import SkillMetadata

@dataclass
class SkillMetadata:
    """轻量级技能元数据"""
    name: str
    description: str
    path: Path
    loaded: bool = False
    skill: Skill | None = None
    references: list[Path] = field(default_factory=list)
```

### LoadingLevel

```python
from harness.skills import LoadingLevel

class LoadingLevel:
    """三级加载常量"""
    FRONTMATTER = 1      # 仅 frontmatter (~100 tokens)
    FULL_CONTENT = 2     # 完整内容 (~1000-2000 tokens)
    REFERENCES = 3       # 包含引用文件
```

### 与 ContextBuilder 集成

```python
from harness.memory import ContextBuilder
from harness.skills import ProgressiveSkillLoader

loader = ProgressiveSkillLoader()

# 构建上下文时渐进加载
async def build_context(session, skills_dir):
    # Level 1: 所有技能的 frontmatter
    all_skills = await loader.discover_skills(skills_dir)
    available_list = [f"- {s.name}: {s.description}" for s in all_skills]
    
    system_prompt = f"# Available Skills\n" + "\n".join(available_list)
    
    # Level 2: 匹配激活的技能完整内容
    matched = loader.match_skills(session.user_input, all_skills)
    for skill_meta in matched:
        full_skill = await loader.load_full_content(skill_meta)
        system_prompt += f"\n\n## Skill: {full_skill.name}\n{full_skill.content}"
    
    return system_prompt
```

### 缓存机制

ProgressiveSkillLoader 内置 LRU 缓存，避免重复加载：

```python
loader = ProgressiveSkillLoader(cache_size=100)

# 第一次加载（从文件读取）
skill1 = await loader.load_full_content(metadata)

# 第二次加载（从缓存读取）
skill2 = await loader.load_full_content(metadata)
assert skill1 is skill2  # 同一对象
```