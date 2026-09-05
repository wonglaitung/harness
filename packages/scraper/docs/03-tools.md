# 03 - 工具系统

## 工具概览

所有工具继承自 SDK 的 `Tool` 基类：

```python
from harness.tools.base import Tool, ToolContext
from harness.types import ToolResult
```

### AI 情报工具

| 工具 | 名称 | 数据源 | 用途 |
|------|------|--------|------|
| FetchRSSTool | `fetch_rss` | RSS Feed | 抓取 RSS 文章 |
| FetchHNTool | `fetch_hn` | Hacker News API | 高分帖子 (>150) |
| FetchShowHNTool | `fetch_show_hn` | Hacker News API | 早期项目 (>50) |
| FetchGitHubTrendingTool | `fetch_github_trending` | GitHub Trending | 热门开源项目 |
| FetchURLTool | `fetch_url` | GitHub/Jina Reader | 深度抓取 README |

### 金融/股票工具

| 工具 | 名称 | 数据源 | 用途 |
|------|------|--------|------|
| FetchHKEXTool | `fetch_hkex` | AkShare (东方财富) | 港股实时行情、异动监控 |
| FetchFinancialNewsTool | `fetch_financial_news` | AkShare + yfinance | 财经快讯、美国国债收益率 |
| ReadHistoryReportTool | `read_history_report` | 文件系统 | 读取历史 One-Pager 报告 |

### 输出工具

| 工具 | 名称 | 数据源 | 用途 |
|------|------|--------|------|
| SaveOnePagerTool | `save_one_pager` | 文件系统 | 保存 Markdown One-Pager |
| UpdateMemoryTool | `update_memory` | 文件系统 | 记录已处理项目到 MEMORY.md（含 30 天自动归档） |

## 工具注册表

### ALL_TOOLS

工具名称到工具类的映射：

```python
from harness_scraper.tools import ALL_TOOLS, get_tools_by_names

# 查看所有可用工具
print(ALL_TOOLS.keys())
# ['fetch_rss', 'fetch_hn', 'fetch_show_hn', 'fetch_github_trending',
#  'fetch_url', 'save_one_pager', 'update_memory', 'fetch_hkex',
#  'fetch_financial_news', 'read_history_report']
```

### get_tools_by_names()

根据工具名称列表获取工具实例：

```python
from harness_scraper.tools import get_tools_by_names

# 获取指定工具
tools = get_tools_by_names(["fetch_rss", "fetch_hn", "save_one_pager"])
# [FetchRSSTool(), FetchHNTool(), SaveOnePagerTool()]

# 错误处理：工具不存在时抛出 ValueError
tools = get_tools_by_names(["unknown_tool"])
# ValueError: Unknown tools: ['unknown_tool']. Available: [...]
```

**用途**：skill 的 `tools.allowed` frontmatter 驱动工具选择：

```python
# IntelAgent 内部实现
if self._skill and self._skill.tools.allowed:
    tools = get_tools_by_names(self._skill.tools.allowed)
```

## 工具设计模式

### 基本结构

```python
class MyTool(Tool):
    @property
    def name(self) -> str:
        return "my_tool"

    @property
    def description(self) -> str:
        return "Tool description for LLM"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch"},
                "limit": {"type": "integer", "description": "Max items"},
            },
            "required": ["url"],
        }

    async def execute(self, arguments: dict, context: ToolContext) -> ToolResult:
        # 执行逻辑
        url = arguments["url"]
        limit = arguments.get("limit", 10)

        try:
            data = await fetch_data(url, limit)
            return ToolResult(tool_call_id="", success=True, content=format_output(data))
        except Exception as e:
            return ToolResult(tool_call_id="", success=False, content="", error=str(e))
```

### 输入验证

```python
def validate_arguments(self, arguments: dict) -> tuple[bool, str | None]:
    """可选：自定义参数验证"""
    if "url" not in arguments:
        return False, "url is required"
    return True, None
```

## FetchRSSTool

### 用途

抓取 RSS Feed 中的文章列表。

### 输入 Schema

```json
{
  "type": "object",
  "properties": {
    "url": {"type": "string", "description": "RSS feed URL"},
    "limit": {"type": "integer", "description": "Max articles to fetch (default 30)"}
  },
  "required": ["url"]
}
```

### 输出格式

```json
{
  "content": "## RSS Feed: Feed Name\n\n### Article 1\nTitle: ...\nURL: ...\nPublished: ...\nSummary: ...\n\n### Article 2\n..."
}
```

### 实现要点

```python
import feedparser

async def execute(self, arguments: dict, context: ToolContext) -> ToolResult:
    url = arguments["url"]
    limit = arguments.get("limit", 30)

    # 使用 aiohttp 抓取，再用 feedparser 解析（示意，实际实现为异步）：
    # async with aiohttp.ClientSession() as session:
    #     async with session.get(url) as resp:
    #         content = await resp.text()
    # feed = feedparser.parse(content)
    feed = feedparser.parse(url)

    # 格式化输出
    articles = []
    for entry in feed.entries[:limit]:
        articles.append({
            "title": entry.title,
            "url": entry.link,
            "published": entry.published if "published" in entry else "",
            "summary": entry.summary[:500] if "summary" in entry else "",
        })

    return ToolResult(tool_call_id="", success=True, content=format_articles(articles))
```

## FetchHNTool

### 用途

抓取 Hacker News 高分帖子。

### 输入 Schema

```json
{
  "type": "object",
  "properties": {
    "min_points": {"type": "integer", "description": "Minimum points (default 150)"},
    "limit": {"type": "integer", "description": "Max posts to fetch (default 20)"}
  },
  "required": []
}
```

### 输出格式

```json
{
  "content": "## Hacker News (>=150 points)\n\n### Post 1\nTitle: ...\nURL: ...\nPoints: ...\nComments: ...\n\n### Post 2\n..."
}
```

### 实现要点

```python
HN_API = "https://hacker-news.firebaseio.com/v0"

async def execute(self, arguments: dict, context: ToolContext) -> ToolResult:
    min_points = arguments.get("min_points", 150)
    limit = arguments.get("limit", 20)

    # 获取 top stories
    top_ids = await fetch_json(f"{HN_API}/topstories.json")

    # 过滤高分帖子
    posts = []
    for id in top_ids[:100]:
        post = await fetch_json(f"{HN_API}/item/{id}.json")
        if post.get("score", 0) >= min_points:
            posts.append(post)
        if len(posts) >= limit:
            break

    return ToolResult(tool_call_id="", success=True, content=format_posts(posts))
```

## FetchShowHNTool

### 用途

抓取 Show HN 早期项目（阈值较低，捕获早期信号）。

### 输入 Schema

```json
{
  "type": "object",
  "properties": {
    "min_points": {"type": "integer", "description": "Minimum points (default 50)"},
    "limit": {"type": "integer", "description": "Max posts to fetch (default 15)"}
  },
  "required": []
}
```

### 实现要点

```python
async def execute(self, arguments: dict, context: ToolContext) -> ToolResult:
    min_points = arguments.get("min_points", 50)  # 更低的阈值
    limit = arguments.get("limit", 15)

    # 搜索 Show HN 帙子
    show_hn_ids = await fetch_json(f"{HN_API}/showstories.json")

    # 过滤
    posts = []
    for id in show_hn_ids[:50]:
        post = await fetch_json(f"{HN_API}/item/{id}.json")
        if post.get("score", 0) >= min_points:
            posts.append(post)
        if len(posts) >= limit:
            break

    return ToolResult(tool_call_id="", success=True, content=format_posts(posts, "Show HN"))
```

## FetchGitHubTrendingTool

### 用途

抓取 GitHub Trending 热门项目。

### 输入 Schema

```json
{
  "type": "object",
  "properties": {
    "language": {"type": "string", "description": "Language filter (default python)"},
    "since": {"type": "string", "description": "Time range: daily/weekly/monthly (default daily)"},
    "filter_ai": {"type": "boolean", "description": "Only return AI-related repos (default true)"},
    "limit": {"type": "integer", "description": "Max repos to fetch (default 15)"}
  },
  "required": []
}
```

### 输出格式

```json
{
  "content": "## GitHub Trending (Python, daily)\n\n### Repo 1\nName: ...\nURL: ...\nDescription: ...\nStars today: ...\nLanguage: ...\n\n### Repo 2\n..."
}
```

### 实现要点

```python
GITHUB_TRENDING = "https://github.com/trending"

async def execute(self, arguments: dict, context: ToolContext) -> ToolResult:
    language = arguments.get("language", "python")
    since = arguments.get("since", "daily")
    filter_ai = arguments.get("filter_ai", True)
    limit = arguments.get("limit", 15)

    # 构建 URL
    url = f"{GITHUB_TRENDING}/{language}?since={since}"

    # 使用 aiohttp 抓取 HTML
    html = await fetch_html(url)

    # 解析 HTML（默认只保留 AI 相关仓库）
    repos = self._parse_trending_html(html, filter_ai)

    return ToolResult(tool_call_id="", success=True, content=format_repos(repos))
```

## FetchURLTool

### 用途

深度抓取 URL 内容（GitHub README、技术文章）。

### 输入 Schema

```json
{
  "type": "object",
  "properties": {
    "url": {"type": "string", "description": "URL to fetch"}
  },
  "required": ["url"]
}
```

### 输出格式

```json
{
  "content": "## Content from URL\n\n[Full README or article content]"
}
```

### 实现要点

```python
async def execute(self, arguments: dict, context: ToolContext) -> ToolResult:
    url = arguments["url"]

    # GitHub URL → README
    if "github.com" in url:
        readme_url = convert_to_raw_readme_url(url)
        content = await fetch_text(readme_url)
        return ToolResult(tool_call_id="", success=True, content=f"## GitHub README\n\n{content}")

    # 其他 URL → Jina Reader
    jina_url = f"https://r.jina.ai/{url}"
    content = await fetch_text(jina_url)
    return ToolResult(tool_call_id="", success=True, content=f"## Article Content\n\n{content}")

def convert_to_raw_readme_url(github_url: str) -> str:
    """github.com/owner/repo → raw.githubusercontent.com/owner/repo/main/README.md"""
    # 解析 URL
    parts = github_url.replace("github.com/", "").split("/")
    owner, repo = parts[0], parts[1]

    # 尝试多个 README 文件名
    return f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md"
```

## SaveOnePagerTool

### 用途

保存情报一页纸到文件系统，支持按领域分类存储。**自动更新 MEMORY.md 记录已处理项目**。

**双模式支持**：
- **Simple mode**：直接保存 title + content（适用于股票分析、自定义报告）
- **Structured mode**：使用 AI 情报字段生成标准 One-Pager

**自动记忆管理**：
- 保存后自动记录到 MEMORY.md（`SaveOnePagerTool._update_memory`）
- 注意：超过 30 天的条目**自动归档**由 `UpdateMemoryTool` 负责；只有在该工具被加入 skill 的 `tools.allowed` 时才会触发（默认技能未包含 `update_memory`，因此默认流程下不会自动归档，仅追加记录）

### 输入 Schema

```json
{
  "type": "object",
  "properties": {
    "title": {"type": "string", "description": "标题 (Simple mode)"},
    "content": {"type": "string", "description": "Markdown 内容 (Simple mode)"},
    "filename": {"type": "string", "description": "文件名 (可选)"},
    "concept_name": {"type": "string", "description": "概念名称 (Structured mode)"},
    "definition": {"type": "string", "description": "技术定义"},
    "pain_point": {"type": "string", "description": "行业痛点"},
    "old_paradigm": {"type": "string", "description": "旧做法"},
    "new_paradigm": {"type": "string", "description": "新做法"},
    "production_impact": {"type": "string", "description": "生产力影响"},
    "adoption_cost": {"type": "string", "description": "采用成本"},
    "github_url": {"type": "string", "description": "GitHub 链接"},
    "source_url": {"type": "string", "description": "来源链接"},
    "domain": {"type": "string", "enum": ["ai", "stocks"], "description": "领域: 'ai' 或 'stocks' (港股必须用 stocks)"}
  },
  "required": []
}
```

**重要**：`domain` 参数决定输出目录：
- `domain="ai"` → `packages/scraper/output/YYYY-MM-DD/ai/`（AI 情报）
- `domain="stocks"` → `packages/scraper/output/YYYY-MM-DD/stocks/`（港股分析）

### 输出格式

```json
{
  "content": "One-Pager saved to: packages/scraper/output/2026-06-13/stocks/00700.md\n\nPreview:\n# 腾讯控股..."
}
```

### 使用示例

#### Simple mode（股票分析）

```python
# 直接保存自定义内容
{
  "title": "腾讯控股 - 回购公告分析",
  "content": "# 腾讯控股 (00700.HK)\n\n## 事件概述\n回购 100 亿港元...",
  "domain": "stocks"
}
```

#### Structured mode（AI 情报）

```python
# 使用标准字段生成 One-Pager
{
  "concept_name": "Model Context Protocol",
  "definition": "标准化 LLM 与外部数据源通信的开放协议",
  "pain_point": "各平台重复对接数据源",
  "old_paradigm": "各平台各自为战",
  "new_paradigm": "MCP 提供统一协议",
  "github_url": "https://github.com/modelcontextprotocol/servers",
  "domain": "ai"
}
```

### 实现要点

```python
# 输出目录：packages/scraper/output/
OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / "output"
MEMORY_PATH = OUTPUT_DIR / "MEMORY.md"

async def execute(self, arguments: dict, context: ToolContext) -> ToolResult:
    domain = arguments.get("domain", "ai")

    # 判断模式
    if "title" in arguments and "content" in arguments:
        # Simple mode: 直接保存
        return await self._execute_simple(arguments, domain)
    elif "concept_name" in arguments:
        # Structured mode: 生成 AI 情报格式
        return await self._execute_structured(arguments, domain)

async def _execute_simple(self, arguments: dict, domain: str) -> ToolResult:
    title = arguments["title"]
    content = arguments["content"]
    filename = arguments.get("filename", sanitize_filename(title))
    source_url = arguments.get("source_url", "")

    # 按日期 + 领域分目录
    date_dir = OUTPUT_DIR / datetime.now().strftime("%Y-%m-%d") / domain
    date_dir.mkdir(parents=True, exist_ok=True)

    file_path = date_dir / f"{filename}.md"
    file_path.write_text(content, encoding="utf-8")

    # 自动更新 MEMORY.md
    self._update_memory(title, domain, source_url)

    return ToolResult(tool_call_id="", success=True, content=f"One-Pager saved to: {file_path}")

def _update_memory(self, name: str, domain: str, source_url: str) -> None:
    """自动更新 MEMORY.md，记录已处理项目"""
    # 加载或创建 MEMORY.md
    # 添加条目到当天的记录
    # 自动归档超过 30 天的条目
    pass
```

### 目录结构

```
packages/scraper/output/
├── MEMORY.md                    # 已处理项目记录（最近 30 天）
├── archive/
│   ├── MEMORY-2026-05.md        # 月度归档
│   └── MEMORY-2026-04.md
├── 2026-06-13/
│   ├── ai/                      # AI 情报
│   │   ├── mcp.md
│   │   └── autoresearch.md
│   └── stocks/                  # 股票分析
│       ├── 00700.md
│       └── macro.md
├── 2026-06-14/
│   └── ...
```

**自动归档机制**：
- `SaveOnePagerTool` 每次保存时都会把项目追加记录到 MEMORY.md
- 超过 30 天的条目归档到 `archive/MEMORY-YYYY-MM.md` 由 `UpdateMemoryTool` 完成（见下文）；默认技能未启用该工具，因此默认流程只追加、不归档
- 保持 MEMORY.md 文件大小可控，便于快速加载

## UpdateMemoryTool

### 用途

将已处理的项目/文章记录到 `MEMORY.md`，避免后续运行重复提取。可选调用，需显式加入 skill 的 `tools.allowed`。

### 输入 Schema

```json
{
  "type": "object",
  "properties": {
    "items": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {"type": "string", "description": "项目/条目名称"},
          "category": {"type": "string", "description": "分类 (如 '新范式/工具', '港股分析')"},
          "source_url": {"type": "string", "description": "发现来源 URL"}
        },
        "required": ["name"]
      },
      "description": "要记录的已处理条目列表"
    },
    "date": {"type": "string", "description": "条目日期 (默认今天, 格式 YYYY-MM-DD)"}
  },
  "required": ["items"]
}
```

### 输出格式

```markdown
Recorded 2 items to MEMORY.md:
- agent-skills-anthropic
- headroom
```

### 实现要点

```python
async def execute(self, arguments: dict, context: ToolContext) -> ToolResult:
    items = arguments.get("items", [])
    date_str = arguments.get("date", datetime.now().strftime("%Y-%m-%d"))

    if not items:
        return ToolResult(
            tool_call_id="",
            success=False,
            content="",
            error="No items provided to record",
        )

    # 加载或创建 MEMORY.md，追加新条目
    content = self._add_items(existing, items, date_str)

    # 自动归档超过 30 天的条目到 archive/MEMORY-YYYY-MM.md
    content = self._archive_old_entries(content)

    return ToolResult(
        tool_call_id="",
        success=True,
        content=f"Recorded {len(items)} items to MEMORY.md:\n" + "\n".join(f"- {item['name']}" for item in items),
    )
```

**注意**：`_archive_old_entries` 按 `RETENTION_DAYS = 30` 将旧日期分区归档到 `output/archive/MEMORY-YYYY-MM.md`。若技能未将 `update_memory` 列入 `tools.allowed`，该归档不会在默认流程中触发。

## FetchHKEXTool

### 用途

抓取港股实时行情数据，监控异动个股（高成交量、大幅涨跌）。使用 AkShare 稳定 API（东方财富数据源）。

### 输入 Schema

```json
{
  "type": "object",
  "properties": {
    "volume_threshold": {"type": "integer", "description": "最低成交额 (港元，默认 50000000 = 50M)"},
    "pct_threshold": {"type": "number", "description": "最低涨跌幅 % (默认 3.0)"},
    "limit": {"type": "integer", "description": "返回数量上限 (默认 20)"},
    "focus_codes": {"type": "array", "items": {"type": "string"}, "description": "关注特定股票代码"}
  },
  "required": []
}
```

### 输出格式

```markdown
## 港股异动监控

### 📈 腾讯控股 (00700.HK)
- 最新价: 380.50 港元
- 涨跌幅: **+5.23%**
- 成交额: 125.3 百万港元
- 换手率: 0.45%
- 股吧: https://guba.eastmoney.com/list,hk00700.html

### 📉 美团-W (03690.HK)
- 最新价: 120.80 港元
- 涨跌幅: **-4.12%**
- 成交额: 89.2 百万港元
- 换手率: 0.32%
- 股吧: https://guba.eastmoney.com/list,hk03690.html

**共 5 只个股发生显著异动，请结合宏观消息面分析。**
```

### 实现要点

```python
import akshare as ak

async def execute(self, arguments: dict, context: ToolContext) -> ToolResult:
    volume_threshold = arguments.get("volume_threshold", 50_000_000)
    pct_threshold = arguments.get("pct_threshold", 3.0)
    limit = arguments.get("limit", 20)
    focus_codes = arguments.get("focus_codes", [])

    # 在线程池中运行同步的 AkShare API
    loop = asyncio.get_running_loop()
    df = await loop.run_in_executor(None, ak.stock_hk_spot_em)

    # 过滤：成交额 > threshold 且涨跌幅 > pct_threshold
    df = df[df['成交额'] >= volume_threshold]
    df = df[df['涨跌幅'].abs() >= pct_threshold]

    # 按成交额排序
    df = df.sort_values('成交额', ascending=False).head(limit)

    return ToolResult(tool_call_id="", success=True, content=format_stocks(df))
```

### 数据源说明

| 数据源 | API | 稳定性 | 维护方 |
|-------|-----|--------|-------|
| 东方财富 | `ak.stock_hk_spot_em()` | 高 | 开源社区 |
| 港交所官网 | 网页抓取 | 低（反爬） | 已弃用 |

**推荐使用 AkShare**：社区维护，API 稳定，无需处理反爬。

## ReadHistoryReportTool

### 用途

读取历史 One-Pager 报告，用于趋势分析和历史信号关联。

**使用场景**：
- 当前数据引用过去事件（如"连续流入 3 天"、"验证早期信号"）
- 对比历史趋势
- 建立跟踪基线

### 输入 Schema

```json
{
  "type": "object",
  "properties": {
    "days": {
      "type": "integer",
      "description": "搜索过去 N 天的报告（默认 7，最大 30）"
    },
    "keywords": {
      "type": "array",
      "items": {"type": "string"},
      "description": "关键词过滤（股票名称、事件类型）。为空则返回日期范围内所有报告。"
    },
    "domain": {
      "type": "string",
      "enum": ["stocks", "ai"],
      "description": "报告领域（默认 stocks）"
    }
  },
  "required": []
}
```

### 输出格式

#### 找到报告时

```markdown
Found 3 historical report(s):

---
**Date**: 2026-06-14
**File**: 00700-腾讯控股
**Path**: packages/scraper/output/2026-06-14/stocks/00700-腾讯控股.md

**Content**:
# 腾讯控股 (00700.HK)

## 事件概述
...
```

#### 无匹配报告时

```markdown
未找到匹配的历史报告。
搜索条件：days=7, keywords=['腾讯']
已搜索目录：2026-06-08 至 2026-06-15

建议：将当前信息作为首次记录，建立跟踪基线。
```

### 使用示例

```python
# 查询过去 7 天关于腾讯的报告
{
  "days": 7,
  "keywords": ["腾讯", "00700"],
  "domain": "stocks"
}

# 查询过去 30 天所有港股报告
{
  "days": 30,
  "domain": "stocks"
}
```

### 实现要点

```python
from pathlib import Path
from datetime import datetime, timedelta

class ReadHistoryReportTool(Tool):
    @property
    def name(self) -> str:
        return "read_history_report"

    async def execute(self, arguments: dict, context: ToolContext) -> ToolResult:
        days = min(arguments.get("days", 7), 30)  # 最多 30 天
        keywords = arguments.get("keywords", [])
        domain = arguments.get("domain", "stocks")

        today = datetime.now().date()
        reports = []

        for i in range(days):
            date = today - timedelta(days=i)
            date_dir = OUTPUT_DIR / date.strftime("%Y-%m-%d") / domain

            if not date_dir.exists():
                continue

            for md_file in sorted(date_dir.glob("*.md")):
                # 关键词过滤
                if keywords:
                    filename = md_file.stem
                    if not any(kw.lower() in filename.lower() for kw in keywords):
                        continue

                content = md_file.read_text(encoding="utf-8")
                reports.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "filename": md_file.stem,
                    "content": content,
                })

        return ToolResult(tool_call_id="", success=True, content=format_reports(reports))
```

### 目录结构

```
packages/scraper/output/
├── MEMORY.md                    # 已处理项目记录
├── 2026-06-15/
│   ├── ai/                      # AI 情报
│   │   └── mcp.md
│   └── stocks/                  # 股票分析
│       ├── 00700.md
│       └── macro.md
├── 2026-06-14/
│   └── stocks/
│       └── 00700.md
```

## FetchFinancialNewsTool

### 用途

抓取实时财经快讯（财联社、华尔街见闻）和美国宏观数据（国债收益率）。用于港股 Alpha 事件捕获。

### 输入 Schema

```json
{
  "type": "object",
  "properties": {
    "source": {"type": "string", "enum": ["cailian", "macro", "all"], "description": "数据源"},
    "keywords": {"type": "array", "items": {"type": "string"}, "description": "关键词过滤"},
    "limit": {"type": "integer", "description": "每源返回上限 (默认 30)"}
  },
  "required": []
}
```

### 输出格式

```markdown
## 金融快讯 (cailian)

### 港交所推科创板简化上市流程
- 来源: 东方财富-财联社
- 时间: 2026-06-13 14:30
- 链接: https://finance.eastmoney.com/xxx
- 内容: 港交所宣布将简化上市流程，预计三季度实施...

### 美国国债收益率监控
- 来源: US_Macro
- 级别: MACRO
- 时间: 2026-06-13
- 内容:
  10年期国债收益率 (^TNX): 4.25%
  2年期国债收益率 (^IRX): 4.50%
  收益率曲线: 倒挂
```

### 实现要点

```python
import akshare as ak
import yfinance as yf

async def execute(self, arguments: dict, context: ToolContext) -> ToolResult:
    source = arguments.get("source", "cailian")
    keywords = arguments.get("keywords", [])
    limit = arguments.get("limit", 30)

    loop = asyncio.get_running_loop()

    # 财联社快讯 (东方财富港股新闻)
    if source in ["cailian", "all"]:
        df = await loop.run_in_executor(None, lambda: ak.stock_news_em(symbol="港股"))
        news_items = filter_news(df, keywords, limit)

    # 美国国债收益率
    if source in ["macro", "all"]:
        tnx = yf.Ticker("^TNX")
        irx = yf.Ticker("^IRX")
        rates = {
            'tnx': tnx.history(period="1d")['Close'].iloc[-1],
            'irx': irx.history(period="1d")['Close'].iloc[-1],
        }

    return ToolResult(tool_call_id="", success=True, content=format_news(news_items, rates))
```

### 数据源说明

| 数据源 | API | 内容 | 稳定性 |
|-------|-----|------|--------|
| 东方财富港股新闻 | `ak.stock_news_em(symbol="港股")` | 港股相关新闻 | 高 |
| Yahoo Finance | `yf.Ticker("^TNX")` | 美国国债收益率 | 高 |

## 工具输出格式规范

### 标准格式

所有工具输出使用 Markdown 格式，便于 LLM 理解：

```markdown
## Header

### Item 1
Field 1: ...
Field 2: ...

### Item 2
...
```

### 为什么使用 Markdown？

| 原因 | 说明 |
|------|------|
| **LLM 理解** | Markdown 是 LLM 最熟悉的格式 |
| **结构清晰** | 标题、列表、字段清晰分离 |
| **易于解析** | Agent 可以快速理解内容 |

## 工具错误处理

### 标准错误返回

```python
from harness.types import ToolResult

# 成功
return ToolResult(
    tool_call_id="",
    success=True,
    content="...",
)

# 失败
return ToolResult(
    tool_call_id="",
    success=False,
    content="",
    error=f"Error: {str(e)}",
)
```

### 常见错误处理

```python
try:
    data = await fetch(url)
except aiohttp.ClientError as e:
    return ToolResult(content=f"Network error: {e}", success=False)
except TimeoutError:
    return ToolResult(content="Timeout: request took too long", success=False)
```

## 工具扩展指南

### 添加新工具

1. 继承 `Tool` 基类
2. 实现 `name`, `description`, `input_schema`
3. 实现 `execute()` 方法
4. 在 `tools/__init__.py` 导出

### 示例：添加 FetchRedditTool

```python
# tools/fetch_reddit.py
class FetchRedditTool(Tool):
    @property
    def name(self) -> str:
        return "fetch_reddit"

    @property
    def description(self) -> str:
        return "Fetch top posts from Reddit subreddit"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "subreddit": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["subreddit"],
        }

    async def execute(self, arguments: dict, context: ToolContext) -> ToolResult:
        subreddit = arguments["subreddit"]
        limit = arguments.get("limit", 10)

        # Reddit API 调用
        posts = await fetch_reddit_posts(subreddit, limit)

        return ToolResult(tool_call_id="", success=True, content=format_posts(posts))
```

```python
# tools/__init__.py
from .fetch_reddit import FetchRedditTool

__all__ = [
    # AI 情报工具
    "FetchRSSTool",
    "FetchHNTool",
    "FetchShowHNTool",
    "FetchGitHubTrendingTool",
    "FetchURLTool",
    # 金融/股票工具
    "FetchHKEXTool",
    "FetchFinancialNewsTool",
    # 输出工具
    "SaveOnePagerTool",
    # 自定义工具
    "FetchRedditTool",  # 新增
]
```

## 依赖说明

### 金融工具依赖

港股和财经工具需要以下依赖：

```bash
# 安装金融数据依赖
pip install akshare>=1.12.0 yfinance>=0.2.0 pandas>=2.0.0
```

| 包 | 用途 | 数据源 |
|---|------|--------|
| `akshare` | 港股行情、财经新闻 | 东方财富 |
| `yfinance` | 美国国债收益率 | Yahoo Finance |
| `pandas` | 数据处理 | - |

**注意**：AkShare 使用东方财富数据源，由开源社区维护，API 稳定性高。

## 下一步

- [01-overview.md](./01-overview.md) - 了解 Scraper 整体架构
- [02-agent-design.md](./02-agent-design.md) - 了解 Agent 设计
- [04-skills.md](./04-skills.md) - 了解技能系统