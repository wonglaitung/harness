# AI 情报抽取系统实现计划

## Context

实现一个自动化情报抽取系统，用于追踪 AI 行业的新概念和新技术。系统核心逻辑是：
- **上游**：监控巨头博客、黑客社区、技术专家 (X/Twitter)
- **中游**：粗筛 → LLM 裁判 → 深度探针 (GitHub README)
- **下游**：生成结构化"盲区技术一页纸"写入文件系统

## 关键设计决策

基于深度评审，做出以下调整：

1. **砍掉 TF-IDF**：维护 30 天基线窗口复杂度高，用 LLM 裁判替代
2. **引入 LLM 裁判层**：用轻量模型 (Qwen 2.5 7B) 判断是否为新范式
3. **深度探针闭环**：从文章提取 GitHub URL → 抓取 README → 填充 One-Pager
4. **支持本地大模型**：配置 vLLM/Ollama 端点，降低 API 成本
5. **X (Twitter) 数据源**：通过 RSSHub 将 X List 转为 RSS

## 包结构

```
packages/scraper/
├── src/harness_scraper/
│   ├── __init__.py
│   ├── models.py                 # Pydantic 数据模型
│   ├── sources/                  # 数据源
│   │   ├── __init__.py
│   │   ├── base.py               # Source 抽象基类
│   │   ├── rss.py                # RSS/博客抓取 (含 RSSHub 的 X List)
│   │   ├── hacker_news.py        # HN API
│   │   └── reddit.py             # Reddit API (可选)
│   ├── filters/                  # 过滤规则
│   │   ├── __init__.py
│   │   ├── prefilter.py          # 粗筛：关键词、链接、代码块
│   │   └── llm_ranker.py         # LLM 裁判层
│   ├── explorer/                 # 深度探针
│   │   ├── __init__.py
│   │   ├── github.py             # GitHub README 抓取
│   │   └── jina_reader.py        # Jina Reader API (可选)
│   ├── output/                   # 输出格式化
│   │   ├── __init__.py
│   │   └── one_pager.py          # 盲区技术一页纸生成
│   ├── llm/                      # LLM 客户端
│   │   ├── __init__.py
│   │   └── client.py             # 统一 LLM 接口 (支持 vLLM/Ollama/OpenAI)
│   ├── scheduler.py              # 定时任务调度
│   └── config.py                 # 配置
├── docs/
│   └── plan.md
├── pyproject.toml
└── README.md
```

## 核心组件

### 1. 数据模型 (Pydantic)

```python
# models.py
from pydantic import BaseModel, Field
from datetime import datetime

class Article(BaseModel):
    """原始文章"""
    url: str
    title: str
    content: str
    source: str                    # 来源名称
    published_at: datetime
    score: int = 0                 # HN points / Reddit upvotes
    github_urls: list[str] = Field(default_factory=list)

class IntelCard(BaseModel):
    """情报卡片 - LLM 抽取的结构化输出"""
    concept_name: str = Field(description="新概念或新工具的官方名称")
    definition: str = Field(description="大白话解释其技术本质")
    pain_point: str = Field(description="它刚出现是为了解决什么痛点")
    old_paradigm: str = Field(description="旧做法是什么")
    new_paradigm: str = Field(description="新做法是什么")
    production_impact: str = Field(description="对应用层工作者的实际生产力影响")
    adoption_cost: str = Field(description="采用成本评估")
    github_url: str = Field(description="官方 GitHub 链接")
    hn_url: str = Field(default="", description="HN 讨论链接")
    published_at: datetime
```

### 2. 数据源 (Source)

```python
class Source(ABC):
    @abstractmethod
    async def fetch(self, since: datetime) -> list[Article]:
        """获取增量文章"""
        pass
```

**数据源配置**：

| 类型 | 来源 | 抓取频率 | 说明 |
|------|------|---------|------|
| RSS | Anthropic Research | 12h | 官方博客 |
| RSS | OpenAI Blog | 12h | 官方博客 |
| RSS | Hugging Face Blog | 12h | 开源社区 |
| RSS | X List (via RSSHub) | 6h | Swyx, Chip Huyen 等专家 |
| API | Hacker News (points > 150) | 6h | 包含 Show HN |
| API | Reddit r/LocalLLaMA | 12h | Top 24h |

### 3. 过滤器 (两阶段)

#### 3.1 粗筛 (Pre-filter)

```python
class PreFilter:
    """粗筛：快速过滤明显不相关的内容"""

    KEYWORDS = [
        "github.com", "gitlab.com",  # 包含代码链接
        "npm install", "pip install", "docker run",  # 安装命令
        "open source", "release", "announce",  # 发布关键词
    ]

    def should_process(self, article: Article) -> bool:
        # 动态高分策略：HN points > 300 直接放行
        if article.score >= 300:
            return True
        # 检查是否包含关键词或 GitHub 链接
        return any(kw in article.content.lower() for kw in self.KEYWORDS)
```

#### 3.2 LLM 裁判 (LLM Ranker)

```python
from pydantic import BaseModel, Field
import json

class Judgment(BaseModel):
    """LLM 判断结果 - 结构化输出"""
    is_new_paradigm: bool = Field(description="是否定义了新的软件工程范式、工具或标准")
    reason: str = Field(description="简短的理由判断")

class LLMRanker:
    """LLM 裁判层：判断是否为新范式"""

    SYSTEM_PROMPT = "你是一个前沿技术专家，负责筛选具有范式转变（Paradigm Shift）或创新性的 AI 开源项目与技术。"

    USER_PROMPT = """请评估以下技术文章是否代表了新工具、新范式或重大技术突破。

标题：{title}
摘要：{content}

请严格按 JSON 格式返回：
{{"is_new_paradigm": true/false, "reason": "简短理由"}}"""

    async def rank(self, article: Article) -> bool:
        prompt = self.USER_PROMPT.format(
            title=article.title,
            content=article.content[:1000]
        )

        # 强制结构化输出 (JSON Mode)
        response_text = await self.llm.generate(
            prompt=prompt,
            system=self.SYSTEM_PROMPT,
            json_mode=True
        )

        try:
            data = json.loads(response_text)
            return data.get("is_new_paradigm", False)
        except json.JSONDecodeError:
            # 降级容错逻辑
            return "YES" in response_text.upper() or "TRUE" in response_text.upper()
```

### 4. 深度探针 (Explorer)

**关键闭环**：从文章提取 GitHub URL → 抓取 README → 填充 One-Pager

```python
class GitHubExplorer:
    """GitHub README 抓取"""

    async def fetch_readme(self, github_url: str) -> str:
        """抓取 GitHub README.md 内容"""
        # 1. 解析 repo URL → https://raw.githubusercontent.com/{owner}/{repo}/main/README.md
        # 2. 尝试多种 README 文件名：README.md, README.rst, README.txt, readme.md
        # 3. 清理 Markdown 格式，保留核心内容
        pass

class JinaReaderExplorer:
    """Jina Reader API 抓取 (备选)"""

    async def fetch(self, url: str) -> str:
        """使用 Jina Reader API 抓取网页内容"""
        # GET https://r.jina.ai/{url}
        # 适用于非 GitHub 链接（如 Hugging Face、技术博客）
        pass
```

**README 文件名优先级**：
```
README.md > README.rst > README.txt > readme.md > docs/index.md
```

### 5. LLM 客户端

```python
class LLMConfig(BaseModel):
    """LLM 配置"""
    provider: str = "openai"                # vllm, ollama, openai, anthropic
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    temperature: float = 0.1

class LLMClient:
    """统一 LLM 接口，支持本地/第三方/云端"""

    def __init__(self, config: LLMConfig):
        self.config = config
        # OpenAI 兼容 API（vLLM、Ollama、第三方都支持）
        self.base_url = config.base_url
        self.headers = {"Authorization": f"Bearer {config.api_key}"} if config.api_key else {}

    async def generate(self, prompt: str) -> str:
        async with aiohttp.ClientSession() as session:
            response = await session.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": self.config.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self.config.temperature,
                    "max_tokens": 1000,
                }
            )
            return (await response.json())["choices"][0]["message"]["content"]
```

**支持的 LLM 提供者**：

| 提供者 | base_url | 成本 | 说明 |
|-------|----------|------|------|
| 本地 vLLM | `http://localhost:8000/v1` | 免费 | 需要 GPU 服务器 |
| 本地 Ollama | `http://localhost:11434/v1` | 免费 | CPU/GPU均可 |
| 硅基流动 | `https://api.siliconflow.cn/v1` | ~0.01元/千token | 推荐，便宜 |
| DeepSeek | `https://api.deepseek.com/v1` | ~0.01元/千token | 推荐 |
| 智谱 AI | `https://open.bigmodel.cn/api/paas/v4` | ~0.01元/千token | GLM 模型 |
| OpenAI | `https://api.openai.com/v1` | ~$0.15/百万token | gpt-4o-mini |
| Anthropic | 需要 Anthropic SDK | ~$3/百万token | claude-sonnet |

### 6. 输出 (One-Pager)

```python
class OnePagerGenerator:
    """盲区技术一页纸生成"""

    EXTRACT_PROMPT = """基于以下 GitHub README 内容，提取技术情报。

{readme_content}

要求：
1. 无论输入的 README 为何种语言，请一律使用中文进行结构化情报的填充
2. 请严格按以下 JSON 格式输出：
{{
    "concept_name": "名称",
    "definition": "技术定义（用大白话解释）",
    "pain_point": "解决的痛点",
    "old_paradigm": "旧做法",
    "new_paradigm": "新做法",
    "production_impact": "生产力影响",
    "adoption_cost": "采用成本评估"
}}"""

    async def generate(self, article: Article, readme: str) -> IntelCard:
        # LLM 结构化抽取 (JSON Mode)
        pass

    def to_markdown(self, card: IntelCard) -> str:
        """转换为 Markdown 格式"""
        pass
```

### 7. 增量排重机制

```python
class DedupStore:
    """增量排重 - 基于 SQLite"""

    def __init__(self, db_path: str = "~/.harness/scraper/seen.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_table()

    def is_seen(self, url: str) -> bool:
        """检查 URL 是否已处理"""
        cursor = self.conn.execute(
            "SELECT 1 FROM seen_urls WHERE url_hash = ?",
            (hashlib.md5(url.encode()).hexdigest(),)
        )
        return cursor.fetchone() is not None

    def mark_seen(self, url: str, concept_name: str):
        """标记 URL 已处理"""
        self.conn.execute(
            "INSERT OR IGNORE INTO seen_urls (url_hash, url, concept_name, seen_at) VALUES (?, ?, ?, ?)",
            (hashlib.md5(url.encode()).hexdigest(), url, concept_name, datetime.now().isoformat())
        )
        self.conn.commit()
```

## 配置文件

`~/.harness/scraper.yaml`:

```yaml
# LLM 配置 - 支持多种提供者
llm:
  # 选项 1：本地 vLLM/Ollama（推荐，成本最低）
  provider: "vllm"
  base_url: "http://localhost:8000/v1"
  model: "Qwen2.5-7B-Instruct"

  # 选项 2：第三方 OpenAI 兼容 API（如 DeepSeek、智谱、硅基流动等）
  # provider: "openai"
  # base_url: "https://api.siliconflow.cn/v1"
  # api_key: "sk-xxx"
  # model: "Qwen/Qwen2.5-7B-Instruct"

  # 选项 3：OpenAI 官方 API
  # provider: "openai"
  # base_url: "https://api.openai.com/v1"
  # api_key: "sk-xxx"
  # model: "gpt-4o-mini"

  # 选项 4：Anthropic Claude
  # provider: "anthropic"
  # api_key: "sk-ant-xxx"
  # model: "claude-sonnet-4-6"

  temperature: 0.1

# 数据源配置
sources:
  rss:
    - url: https://www.anthropic.com/research/rss
      name: Anthropic Research
    - url: https://openai.com/blog/rss
      name: OpenAI Blog
    - url: https://huggingface.co/blog/feed.xml
      name: Hugging Face Blog
    # X List via RSSHub
    - url: https://rsshub.app/twitter/list/your-list-id
      name: X AI Experts

  hacker_news:
    min_points: 150
    include_show_hn: true

  reddit:
    subreddits: [LocalLLaMA]
    timeframe: 24h

# 过滤配置
filter:
  prefilter_keywords:
    - "github.com"
    - "release"
    - "announce"
    - "open source"

# 输出配置
output:
  directory: ~/.harness/scraper
```

## 数据流

```
┌─────────────────┐     ┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   数据源        │────>│   粗筛      │────>│  LLM 裁判    │────>│  深度探针   │
│ RSS/HN/X/Reddit │     │ 关键词过滤  │     │ 判断新范式   │     │ GitHub README│
└─────────────────┘     └─────────────┘     └──────────────┘     └─────────────┘
                                                                          │
                                                                          ▼
┌─────────────────┐     ┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   文件系统      │<────│  One-Pager  │<────│  LLM 抽取    │<────│ README 内容 │
│ ~/.harness/     │     │  Markdown   │     │  结构化输出  │     │             │
└─────────────────┘     └─────────────┘     └──────────────┘     └─────────────┘
```

## 实现步骤

### Phase 1: 基础框架
- [ ] 创建 `packages/scraper/` 目录结构
- [ ] 实现 Pydantic 数据模型 (`models.py`)
- [ ] 实现配置加载 (`config.py`)
- [ ] 实现 LLM 客户端 (`llm/client.py`) - 支持 vLLM/Ollama/OpenAI 兼容 API

### Phase 2: 数据源
- [ ] 实现 `Source` 基类 (`sources/base.py`)
- [ ] 实现 `RSSSource` (`sources/rss.py`) - 含 RSSHub X List
- [ ] 实现 `HackerNewsSource` (`sources/hacker_news.py`)
- [ ] 测试数据抓取

### Phase 3: 过滤器 (两阶段)
- [ ] 实现 `PreFilter` 粗筛 (`filters/prefilter.py`) - 动态高分策略 (HN > 300)
- [ ] 实现 `LLMRanker` 裁判 (`filters/llm_ranker.py`) - 结构化输出 JSON
- [ ] 测试过滤流程

### Phase 4: 深度探针
- [ ] 实现 `GitHubExplorer` (`explorer/github.py`) - 多 README 文件名尝试
- [ ] 实现 `JinaReaderExplorer` 备选 (`explorer/jina_reader.py`) - 非 GitHub 链接
- [ ] 测试 README 抓取

### Phase 5: 输出
- [ ] 实现 `OnePagerGenerator` (`output/one_pager.py`) - 多语言支持，强制中文输出
- [ ] 实现文件系统写入 - 按日期分目录
- [ ] 实现增量排重机制 - 布隆过滤器或 SQLite 唯一键

### Phase 6: 调度
- [ ] 实现定时调度器 (`scheduler.py`) - 带并发信号量保护
- [ ] CLI 命令 (`harness-scraper run --once`)
- [ ] 端到端测试

## 依赖

```toml
[project]
dependencies = [
    "aiohttp>=3.8.0",
    "feedparser>=6.0.0",
    "pyyaml>=6.0",
    "pydantic>=2.0",
    "jinja2>=3.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
]
```

## 工程注意事项

### 1. LLM 并发控制

```python
# llm/client.py
class LLMClient:
    def __init__(self, config):
        self._session: aiohttp.ClientSession | None = None
        self._semaphore = asyncio.Semaphore(2)  # 限制并发，保护显存

    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self.headers)
        return self._session

    async def generate(self, prompt: str, json_mode: bool = False) -> str:
        session = await self.get_session()
        async with self._semaphore:  # 信号量保护
            # ... API 调用
```

### 2. GitHub Rate Limit 处理

```python
class GitHubExplorer:
    RATE_LIMIT_DELAY = 1.0  # 请求间隔

    async def fetch_readme(self, github_url: str) -> str:
        await asyncio.sleep(self.RATE_LIMIT_DELAY)  # 避免触发限流
        # ... 抓取逻辑
```

### 3. 错误处理与降级

- GitHub 抓取失败 → 尝试 Jina Reader API
- LLM JSON 解析失败 → 降级到关键词匹配
- 网络超时 → 记录日志，跳过该文章

## 验证方法

1. **单元测试**：每个 Source、Filter、Explorer 的独立测试
2. **集成测试**：运行 `harness-scraper run --once` 执行完整流程
3. **输出验证**：检查 `~/.harness/scraper/YYYY-MM-DD/` 生成的 Markdown 文件

## 示例输出

`~/.harness/scraper/2026-06-13/mcp.md`:

```markdown
# Model Context Protocol (MCP)

## 技术定义 (What)
MCP 是一个开放协议，用于标准化大模型与外部数据源/工具的通信方式。可以理解为"AI 生态的 USB 接口"。

## 行业痛点 (Why)
每个 AI 平台都需要单独对接各种数据源（文件、数据库、API），重复造轮子，无法互通。

## 旧范式 vs 新范式
- **旧做法**：OpenAI 单独对接 Google Drive，Anthropic 单独对接 Slack，各平台各自为战
- **新做法**：MCP 提供统一协议，任何 LLM 都可以通过 MCP 连接任何数据源

## 生产力影响 (How)
1. 应用层开发者只需实现一次 MCP server，即可被所有支持 MCP 的 AI 客户端使用
2. 采用成本低：有 Python/TypeScript SDK，几分钟即可上手

## 核心线索
- GitHub：https://github.com/modelcontextprotocol/servers
- HN 讨论：https://news.ycombinator.com/item?id=xxx
- 发布时间：2024-11-25
```
