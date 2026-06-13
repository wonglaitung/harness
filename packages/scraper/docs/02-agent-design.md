# 02 - IntelAgent 设计

## 类设计

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

## 工具清单

| 工具 | 用途 |
|-----|------|
| fetch_rss | 抓取 RSS 文章 |
| fetch_hn | 抓取 HN 高分帖子 |
| fetch_show_hn | 抓取 Show HN 早期项目 |
| fetch_github_trending | 抓取 GitHub Trending |
| fetch_url | 深度抓取 URL 内容 |
| save_one_pager | 保存情报一页纸 |

## 通用工作流程

1. 广撒网：选择合适的数据源
2. 精准筛选：根据技能文件判断高价值内容
3. 深度挖掘：fetch_url 获取详细信息
4. 结构化输出：save_one_pager 保存

## 通用判断原则

- 宁缺毋滥：宁可漏掉也不要误报
- 时效性：关注首次出现时间
- 可操作性：读者能从情报中获得价值
"""
```

## 技能加载

### load_skill 函数

```python
def load_skill(skill_name: str) -> str | None:
    """从 ~/.harness/skills/{skill_name}.md 加载技能"""
    skill_path = SKILL_DIR / f"{skill_name}.md"
    if skill_path.exists():
        return skill_path.read_text(encoding="utf-8")
    return None
```

### 技能注入流程

```python
def __init__(self, ..., skill: str | None = None):
    system_prompt = BASE_SYSTEM_PROMPT

    if skill:
        skill_content = load_skill(skill)
        if skill_content:
            system_prompt += f"\n\n---\n\n# 已加载技能：{skill}\n\n{skill_content}"
            logger.info(f"Loaded skill: {skill}")
        else:
            logger.warning(f"Skill not found: {skill}")
```

## 默认工具

```python
DEFAULT_TOOLS = [
    FetchRSSTool(),
    FetchHNTool(),
    FetchShowHNTool(),
    FetchGitHubTrendingTool(),
    FetchURLTool(),
    SaveOnePagerTool(),
]
```

## 运行方法

### run()

```python
async def run(
    self,
    prompt: str = "运行信息提取...",
    session_id: str | None = None,
    verbose: bool = False,
) -> LoopResult:
    """运行 Agent"""
    result = await self._agent.run(
        prompt=prompt,
        session_id=session_id,
        verbose=verbose,
    )
    return result
```

### run_with_sources()

```python
async def run_with_sources(
    self,
    rss_feeds: list[str] | None = None,
    hn_min_points: int = 150,
    show_hn_min_points: int = 50,
    github_language: str = "python",
    verbose: bool = False,
) -> LoopResult:
    """指定数据源运行"""
    prompt = build_prompt_from_sources(...)
    return await self.run(prompt, verbose=verbose)
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

### 基本使用

```python
from harness_scraper import IntelAgent, load_config

# 加载配置
config = load_config()

# 创建 Agent（默认 AI 技能）
agent = IntelAgent(config, skill="ai-intelligence")

# 运行
result = await agent.run("提取 AI 情报")
print(result.content)
```

### 自定义技能

```python
# 股票分析
agent = IntelAgent(config, skill="stock-analysis")
result = await agent.run("提取股票投资信号")

# 无技能（通用模式）
agent = IntelAgent(config)
result = await agent.run("提取热门技术话题")
```

### 自定义工具

```python
# 只用 RSS 和 URL 工具
agent = IntelAgent(
    config,
    tools=[FetchRSSTool(), FetchURLTool(), SaveOnePagerTool()],
    skill="ai-intelligence",
)
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

### 为什么使用 SDK 的 AgentHarness？

| 原因 | 说明 |
|------|------|
| **复用** | 不重复实现 Agent Loop |
| **稳定性** | SDK 经过测试验证 |
| **功能丰富** | Memory、Hooks、Skills 等 |