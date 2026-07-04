# 02 - Agent 设计

## 概述

Scraper 提供两种 Agent 模式：

| Agent | 执行模式 | 适用场景 |
|-------|----------|----------|
| **IntelAgent** | 单次执行 | 简单任务，一次性提取 |
| **GoalAgent** | 目标驱动 | 复杂任务，自主迭代直到目标达成 |

## IntelAgent

单次执行的情报提取 Agent，适合简单任务。

### IntelAgent 结构

```python
class IntelAgent:
    """通用信息抓取 Agent，支持技能注入"""

    def __init__(
        self,
        config: ScraperConfig,
        tools: list[Tool] | None = None,
        skill: str | None = None,
        memory_path: str | Path | None = None,
    ):
        # 初始化 AgentHarness
        self._agent = AgentHarness(
            model=config.llm.model,
            api_key=config.llm.api_key,
            base_url=config.llm.base_url,
            provider="openai",
            tools=tools or DEFAULT_TOOLS,
            system_prompt=build_system_prompt(skill),
            memory_md_path=memory_path,
            max_iterations=15,
        )

    async def run(self, prompt: str) -> LoopResult:
        """运行 Agent"""
        return await self._agent.run(prompt)
```

### 系统提示词分层

```
┌─────────────────────────────────────────────────┐
│              BASE_SYSTEM_PROMPT                  │
│  - 通用角色定位                                   │
│  - 工具清单                                       │
│  - 通用工作流程                                   │
│  - 通用判断原则                                   │
└─────────────────────────────────────────────────┘
                      ↓ 拼接
┌─────────────────────────────────────────────────┐
│              Skill Content                       │
│  - 领域判断标准                                   │
│  - 已知实体列表                                   │
│  - 输出模板                                       │
│  - 领域工作流程                                   │
└─────────────────────────────────────────────────┘
                      ↓ 拼接
┌─────────────────────────────────────────────────┐
│              MEMORY.md                           │
│  - 已处理项目                                     │
│  - 避免重复                                       │
└─────────────────────────────────────────────────┘
                      ↓ 最终
┌─────────────────────────────────────────────────┐
│          Complete System Prompt                  │
│          (发送给 LLM)                             │
└─────────────────────────────────────────────────┘
```

### BASE_SYSTEM_PROMPT 内容

```python
BASE_SYSTEM_PROMPT = """# 信息提取代理

## 角色定位

你是一个专业的信息提取代理，负责从海量内容中识别高价值信息。

## 通用判断原则

1. **宁缺毋滥**：宁可漏掉也不要误报
2. **时效性**：关注首次出现时间
3. **可操作性**：读者能从情报中获得价值
"""
```

**注意**：工具清单、工作流程、判断标准都由 skill 文件定义，不在 base prompt 中硬编码。

## 技能加载

### load_skill 函数

使用 SDK 的 `Skill.from_file()` 解析技能文件（含 frontmatter）：

```python
from harness.skills.base import Skill

def load_skill(skill_name: str) -> Skill | None:
    """从 packages/scraper/skills/{skill_name}.md 加载技能"""
    repo_skill_path = REPO_SKILL_DIR / f"{skill_name}.md"
    if repo_skill_path.exists():
        return Skill.from_file(repo_skill_path)  # 解析 YAML frontmatter
    return None
```

**返回 `Skill` 对象**：

```python
skill = load_skill("ai-intelligence")
skill.name           # "ai-intelligence"
skill.description    # "AI 行业情报提取..."
skill.tools.allowed  # ["fetch_rss", "fetch_hn", ...]
skill.content        # 技能 Markdown 内容
```

### 技能注入流程

```python
def __init__(self, ..., skill: str | None = None):
    # 1. 加载技能
    if skill:
        self._skill = load_skill(skill)
        if not self._skill:
            raise ValueError(f"Skill not found: {skill}")

    # 2. 根据 skill.tools.allowed 自动选择工具
    if tools is None:
        if self._skill and self._skill.tools.allowed:
            tools = get_tools_by_names(self._skill.tools.allowed)
        else:
            tools = get_tools_by_names(["fetch_url"])  # 最小默认

    # 3. 拼接 system prompt
    system_prompt = BASE_SYSTEM_PROMPT
    if self._skill:
        system_prompt += f"\n\n---\n\n# 已加载技能：{self._skill.name}\n\n{self._skill.content}"
```

## 工具配置

### 工具自动选择（推荐）

skill 的 `tools.allowed` frontmatter 驱动工具选择：

```python
# 只需指定 skill，工具自动选择
agent = IntelAgent(config, skill="ai-intelligence")
# 自动加载: fetch_rss, fetch_hn, fetch_show_hn, fetch_github_trending, fetch_url, save_one_pager

agent = IntelAgent(config, skill="hk-stocks-alpha")
# 自动加载: fetch_hkex, fetch_financial_news, fetch_url, save_one_pager
```

**skill 文件示例**：

```markdown
---
name: ai-intelligence
description: AI 行业情报提取
tools:
  allowed:
    - fetch_rss
    - fetch_hn
    - fetch_show_hn
    - fetch_github_trending
    - fetch_url
    - save_one_pager
---

# AI 情报提取技能
...
```

### 自定义工具（可选）

显式传入 `tools` 参数覆盖自动选择：

```python
# 只用 RSS 和 URL 工具
agent = IntelAgent(
    config,
    skill="ai-intelligence",
    tools=[FetchRSSTool(), FetchURLTool()],
)
```

### 最小工具集

不传 skill 时，默认只有 `FetchURLTool`：

```python
agent = IntelAgent(config)
# 只有 fetch_url 工具可用
```

## 运行方法

### run()

```python
async def run(
    self,
    prompt: str,
    session_id: str | None = None,
    verbose: bool = False,
) -> LoopResult:
    """运行 Agent，prompt 必须指定任务"""
    result = await self._agent.run(
        prompt=prompt,
        session_id=session_id,
        verbose=verbose,
    )
    return result
```

## 会话管理

```python
def get_session(self, session_id: str) -> Session:
    """获取已有会话"""
    return self._agent.get_session(session_id)

def clear_session(self, session_id: str) -> None:
    """清除会话"""
    self._agent.clear_session(session_id)
```

## 使用示例

### 基本使用（工具自动选择）

```python
from harness_scraper import IntelAgent, load_config

# 加载配置
config = load_config()

# 创建 Agent（工具根据 skill.tools.allowed 自动选择）
agent = IntelAgent(config, skill="ai-intelligence")

# 运行
result = await agent.run("提取 AI 情报")
print(result.content)
```

### 不同技能

```python
# AI 情报（自动选择 6 个工具）
agent = IntelAgent(config, skill="ai-intelligence")

# 港股 Alpha（自动选择 4 个工具）
agent = IntelAgent(config, skill="hk-stocks-alpha")

# 无技能（通用模式，只有 fetch_url）
agent = IntelAgent(config)
```

### 多轮对话

```python
# 第一次运行
result1 = await agent.run("提取 AI 情报", session_id="session-1")

# 继续对话（使用相同 session_id）
result2 = await agent.run(
    "这次多关注前端类的项目",
    session_id="session-1"
)
```

## 设计决策

### 为什么 max_iterations=15？

| 原因 | 说明 |
|------|------|
| **完整流程** | RSS → HN → GitHub → URL → One-Pager 需要多步 |
| **成本控制** | 限制最大迭代次数，避免无限循环 |
| **任务复杂度** | 情报提取通常需要 8-12 步 |

### 为什么拼接 Skill 而非硬编码？

| 原因 | 说明 |
|------|------|
| **可扩展** | 新领域只需 Skill 文件 |
| **可维护** | 判断标准独立于代码 |
| **用户定制** | 用户可创建自己的 Skill |

### 为什么用 frontmatter 驱动工具选择？

| 原因 | 说明 |
|------|------|
| **声明式** | 工具清单在 skill 文件中声明，无需改代码 |
| **一致性** | skill 文件既是工具定义，也是工作流程 |
| **新 skill 简单** | 创建 skill 文件即可，无需注册工具 |

### 为什么使用 SDK 的 AgentHarness？

| 原因 | 说明 |
|------|------|
| **复用** | 不重复实现 Agent Loop |
| **稳定性** | SDK 经过测试验证 |
| **功能丰富** | Memory、Hooks、Skills 等 |

## GoalAgent（目标驱动执行）

GoalAgent 使用 `run_goal()` 自主执行，直到目标达成。这是 Loop Engineering 范式的应用。

### 与 IntelAgent 的区别

| 特性 | IntelAgent | GoalAgent |
|------|------------|-----------|
| 执行模式 | 单次执行 | 循环执行直到目标达成 |
| 方法 | `run(prompt)` | `run_goal(goal, ...)` |
| 验证 | 无自动验证 | 内置验证器 + 自定义验证 |
| 迭代次数 | 固定（max_iterations=15） | 可配置（默认 20） |
| 适用场景 | 简单任务 | 复杂信息提取 |

### 类设计

```python
from harness import AgentHarness, GoalStatus
from harness.loop import GoalConfig, GoalResult

class GoalAgent:
    """目标驱动的信息提取 Agent"""

    def __init__(
        self,
        config: ScraperConfig,
        skill: str | None = None,
        memory_path: str | Path | None = None,
    ):
        # 初始化 AgentHarness
        self._agent = AgentHarness(...)

    async def run_goal(
        self,
        goal: str,
        max_iterations: int = 20,
        timeout_seconds: float = 300.0,
        custom_verifier: Callable | None = None,
    ) -> GoalResult:
        """
        运行目标驱动执行。

        Args:
            goal: 目标描述
            max_iterations: 最大迭代次数
            timeout_seconds: 超时时间（秒）
            custom_verifier: 自定义验证函数

        Returns:
            GoalResult 包含 status、content、total_iterations
        """
        config = GoalConfig(
            description=goal,
            max_iterations=max_iterations,
        )
        return await self._agent.run_goal(
            config,
            timeout_seconds=timeout_seconds,
            custom_verifier=custom_verifier,
        )
```

### 使用示例

#### 基本使用

```python
from harness_scraper.goal_agent import GoalAgent
from harness_scraper.config import load_config

agent = GoalAgent(load_config(), skill="ai-intelligence")

result = await agent.run_goal(
    goal="提取 3 个 AI 行业新范式项目",
    max_iterations=20,
)

if result.status == GoalStatus.ACHIEVED:
    print(f"✅ 目标达成，共 {result.total_iterations} 轮迭代")
else:
    print(f"❌ 未达成: {result.status}")
```

#### 自定义验证

```python
from pathlib import Path

def verify_one_pagers(result):
    """验证是否生成了至少 3 个 One-Pager"""
    output_dir = Path("output")
    md_files = list(output_dir.glob("**/*.md"))
    # 排除 MEMORY.md
    one_pagers = [f for f in md_files if f.name != "MEMORY.md"]
    return len(one_pagers) >= 3

result = await agent.run_goal(
    goal="提取 AI 情报并保存 One-Pager",
    custom_verifier=verify_one_pagers,
)
```

### 执行流程

```
用户目标: "提取 3 个 AI 行业新范式项目"
    ↓
GoalAgent.run_goal()
    ↓
┌─────────────────────────────────────────────┐
│              Goal Loop                       │
│                                              │
│  ┌─────────┐    ┌─────────┐    ┌────────┐  │
│  │ 迭代 1  │ →  │ 验证    │ →  │ 未达成 │  │
│  │ 抓取 RSS│    │ 检查结果│    │ 继续   │  │
│  └─────────┘    └─────────┘    └────────┘  │
│       ↓                                       │
│  ┌─────────┐    ┌─────────┐    ┌────────┐  │
│  │ 迭代 2  │ →  │ 验证    │ →  │ 未达成 │  │
│  │ 抓取 HN │    │ 检查结果│    │ 继续   │  │
│  └─────────┘    └─────────┘    └────────┘  │
│       ↓                                       │
│  ┌─────────┐    ┌─────────┐    ┌────────┐  │
│  │ 迭代 3  │ →  │ 验证    │ →  │ 达成!  │  │
│  │ 保存    │    │ 3 个文件│    │ 退出   │  │
│  └─────────┘    └─────────┘    └────────┘  │
└─────────────────────────────────────────────┘
    ↓
返回 GoalResult(status=ACHIEVED, total_iterations=3)
```

### 默认目标

根据技能自动生成默认目标：

| 技能 | 默认目标 |
|------|----------|
| `ai-intelligence` | 提取 AI 行业情报：识别 3 个以上新范式项目 |
| `hk-stocks-alpha` | 提取港股市场信号：识别 3 个以上左侧交易机会 |

### 设计决策

#### 为什么使用 run_goal() 而非 run()？

| 场景 | IntelAgent (run) | GoalAgent (run_goal) |
|------|------------------|----------------------|
| 单次抓取 | ✅ 足够 | 过度设计 |
| 需要多次尝试 | ❌ 需手动重试 | ✅ 自动重试 |
| 质量验证 | ❌ 无自动验证 | ✅ 内置验证 |
| 成本控制 | ✅ 固定迭代 | ⚠️ 需设上限 |

#### GoalAgent 适用场景

- **信息质量要求高**：需要验证输出质量
- **任务复杂**：可能需要多次调整策略
- **自主性要求**：Agent 自主决定何时完成

## 下一步

- [01-overview.md](./01-overview.md) - 了解 Scraper 整体架构
- [03-tools.md](./03-tools.md) - 了解工具系统
- [04-skills.md](./04-skills.md) - 了解技能系统