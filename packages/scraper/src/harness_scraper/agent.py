"""
IntelAgent - Intelligence extraction agent powered by Harness SDK.

Uses AgentHarness with custom tools for:
- RSS fetching
- Hacker News fetching
- GitHub Trending fetching
- URL content fetching
- One-Pager saving

The agent can autonomously decide which sources to fetch,
judge if content represents new paradigms, and generate One-Pagers.
"""

import logging
from pathlib import Path
from typing import Any

from harness import AgentHarness
from harness.tools.base import Tool

from harness_scraper.models import ScraperConfig
from harness_scraper.tools import (
    FetchRSSTool,
    FetchHNTool,
    FetchShowHNTool,
    FetchGitHubTrendingTool,
    FetchURLTool,
    SaveOnePagerTool,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """# AI 情报提取代理

## 角色定位

你是一个专业的 AI 行业情报分析师，负责从海量技术内容中识别具有范式转变意义的新技术、新工具和新概念。你的核心价值在于"发现盲区"——那些主流尚未关注但即将改变行业的前沿趋势。

## 工具清单

| 工具 | 用途 | 建议使用场景 |
|-----|------|-------------|
| `fetch_rss` | 抓取 RSS 文章 | 获取官方博客（OpenAI、Anthropic、Google AI）|
| `fetch_hn` | 抓取 HN 高分帖子 (>=150) | 发现已被社区验证的热门讨论 |
| `fetch_show_hn` | 抓取 Show HN (>=50) | 发现刚发布的早期新项目 |
| `fetch_github_trending` | 抓取 GitHub Trending | 发现正在爆发的新开源项目 |
| `fetch_url` | 深度抓取 URL 内容 | 获取 README、技术文章全文 |
| `save_one_pager` | 保存情报一页纸 | 将发现的情报结构化保存 |

## 工作流程

### 第一步：广撒网（数据采集）
1. 使用 `fetch_rss` 抓取官方博客最新文章
2. 使用 `fetch_hn` 获取热门技术讨论
3. 使用 `fetch_show_hn` 发现早期新项目（降低阈值，捕获早期信号）
4. 使用 `fetch_github_trending` 发现正在爆发的开源项目

### 第二步：精准筛选（判断新范式）
对每篇文章/项目，判断是否属于以下**三类新前沿线索**：

**类型 A：新范式/行业黑话**
- 社区自发形成的新概念词汇
- 例：taste-skill（AI 前端的审美与技巧）、vibe-coding（氛围编程）、prompt-engineering

**类型 B：新模型架构/微调流派**
- 新的模型架构、训练方法、推理框架
- 例：Hermes 系列、Agent 运行时、vLLM（已成熟，不算新）

**类型 C：新评测/脚手架工具**
- 自动化评测框架、新协议、新标准
- 例：MCP（Model Context Protocol）、Harness 评估框架、GGUF

### 第三步：深度挖掘（内容提取）
对通过筛选的内容：
1. 使用 `fetch_url` 获取 GitHub README 或全文
2. 分析核心创新点、解决什么痛点、范式转变

### 第四步：结构化输出（生成 One-Pager）
使用 `save_one_pager` 保存，必须包含：
- **技术定义**：用大白话解释是什么
- **行业痛点**：为什么需要它
- **范式对比**：旧做法 vs 新做法
- **生产力影响**：对开发者的实际价值
- **采用成本**：时间、金钱、学习曲线

## 判断标准详解

### ✅ 应该标记为新范式

| 情况 | 示例 | 原因 |
|-----|------|------|
| 新项目（<3个月） | karpathy/autoresearch | 刚发布，定义了新的自动化科研范式 |
| 新概念/黑话 | taste-skill、vibe-coding | 社区新词，代表认知升级 |
| 新协议/标准 | MCP、GGUF | 定义了新的互操作方式 |
| 新工具类别 | browser-use（AI 操作浏览器）| 开创了新的 Agent 能力边界 |

### ❌ 不应标记为新范式

| 情况 | 示例 | 原因 |
|-----|------|------|
| 成熟项目 | vLLM、LangChain、Ollama | 已存在超过 3 个月，广泛使用 |
| 纯教程/最佳实践 | "如何用 LangChain 构建应用" | 不包含新概念，只是使用指南 |
| 增量更新 | "vLLM 0.5.0 发布" | 版本升级，非范式转变 |
| 纯应用实现 | "AI 邮件助手" | 用现有技术做具体应用，无创新 |

## 已知成熟项目列表（跳过这些）

**推理框架**：vLLM、TGI、llama.cpp、Ollama
**应用框架**：LangChain、LlamaIndex、Haystack、Semantic Kernel
**模型**：LLaMA、Mistral、Qwen、ChatGLM
**工具**：Transformers、PyTorch、TensorFlow
**向量数据库**：Pinecone、Weaviate、Qdrant、Milvus

## 输出要求

1. **语言**：One-Pager 必须使用中文，无论源内容是什么语言
2. **简洁**：每个字段控制在 2-3 句话
3. **可操作**：提供 GitHub 链接，让读者可以直接深入了解

## 示例对话

**用户**：运行情报抽取
**代理**：
1. [调用 fetch_hn] 发现 "Karpathy 发布 autoresearch"
2. [判断] ✅ 新项目，定义了"AI 自主科研"新范式
3. [调用 fetch_url] 获取 README
4. [调用 save_one_pager] 保存 "autoresearch.md"

**用户**：这次多关注前端类的
**代理**：调整策略，重点筛选 UI/UX 相关的新范式，如 taste-skill、AI 前端工具等

## 注意事项

- 宁可漏掉也不要误报，保持高标准
- 关注项目的"首次提出时间"，不是 GitHub trending 时间
- 区分"热度"和"创新性"——热度高不代表是新技术
"""


class IntelAgent:
    """
    Intelligence extraction agent powered by Harness SDK.

    Example:
        ```python
        from harness_scraper.agent import IntelAgent
        from harness_scraper.config import load_config

        agent = IntelAgent(load_config())
        result = await agent.run("Extract AI intelligence from RSS and HN")
        print(result.content)
        ```
    """

    def __init__(
        self,
        config: ScraperConfig,
        tools: list[Tool] | None = None,
        memory_path: str | Path | None = None,
    ):
        """
        Initialize Intel Agent.

        Args:
            config: Scraper configuration with LLM settings
            tools: Optional custom tools (defaults to all intel tools)
            memory_path: Optional memory file path for known projects
        """
        self.config = config

        # Default tools
        if tools is None:
            tools = [
                FetchRSSTool(),
                FetchHNTool(),
                FetchShowHNTool(),
                FetchGitHubTrendingTool(),
                FetchURLTool(),
                SaveOnePagerTool(),
            ]

        # Build system prompt
        system_prompt = SYSTEM_PROMPT

        # Convert memory_path to Path if string
        if memory_path:
            memory_path = Path(str(memory_path).replace("~", str(Path.home())))
            if memory_path.exists():
                system_prompt += f"\n\n## 记忆文件\n请参考 {memory_path} 中记录的已知项目。"

        # Create AgentHarness
        self._agent = AgentHarness(
            model=config.llm.model,
            api_key=config.llm.api_key,
            base_url=config.llm.base_url,
            provider="openai",  # All compatible APIs use OpenAI provider
            tools=tools,
            system_prompt=system_prompt,
            memory_md_path=memory_path,
            max_iterations=15,  # Allow enough iterations for full workflow
        )

    async def run(
        self,
        prompt: str = "运行情报抽取：从 RSS、HN、GitHub Trending 获取内容，识别新范式，生成 One-Pager",
        session_id: str | None = None,
        verbose: bool = False,
    ) -> Any:
        """
        Run the intelligence extraction agent.

        Args:
            prompt: User prompt describing what to extract
            session_id: Optional session ID for conversation continuity
            verbose: If True, print progress to console

        Returns:
            LoopResult from AgentHarness
        """
        logger.info(f"Running IntelAgent with prompt: {prompt[:50]}...")

        result = await self._agent.run(
            prompt=prompt,
            session_id=session_id,
            verbose=verbose,
        )

        logger.info(f"IntelAgent completed: {len(result.content)} chars output")
        return result

    async def run_with_sources(
        self,
        rss_feeds: list[str] | None = None,
        hn_min_points: int = 150,
        show_hn_min_points: int = 50,
        github_language: str = "python",
        verbose: bool = False,
    ) -> Any:
        """
        Run agent with specific source parameters.

        Args:
            rss_feeds: List of RSS feed URLs to fetch
            hn_min_points: Minimum points for HN posts
            show_hn_min_points: Minimum points for Show HN posts
            github_language: Language filter for GitHub Trending
            verbose: If True, print progress

        Returns:
            LoopResult from AgentHarness
        """
        # Build specific prompt
        prompt_parts = ["运行情报抽取："]

        if rss_feeds:
            for feed in rss_feeds[:5]:  # Limit to 5 feeds
                prompt_parts.append(f"使用 fetch_rss 抓取 {feed}")

        prompt_parts.append(f"使用 fetch_hn 抓取 HN 帖子（min_points={hn_min_points}）")
        prompt_parts.append(f"使用 fetch_show_hn 抓取 Show HN（min_points={show_hn_min_points}）")
        prompt_parts.append(f"使用 fetch_github_trending 抓取 {github_language} trending")

        prompt_parts.append("识别新范式，对有潜力的内容使用 fetch_url 深度抓取")
        prompt_parts.append("使用 save_one_pager 保存情报一页纸")

        prompt = "\n".join(prompt_parts)

        return await self.run(prompt=prompt, verbose=verbose)

    def get_session(self, session_id: str) -> Any:
        """Get an existing session."""
        return self._agent.get_session(session_id)

    def clear_session(self, session_id: str) -> None:
        """Clear a session's messages."""
        self._agent.clear_session(session_id)