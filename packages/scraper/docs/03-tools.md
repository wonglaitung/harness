# 03 - 工具系统

## 工具概览

所有工具继承自 SDK 的 `Tool` 基类：

```python
from harness.tools.base import Tool, ToolContext
from harness.types import ToolResult
```

| 工具 | 名称 | 数据源 | 用途 |
|------|------|--------|------|
| FetchRSSTool | `fetch_rss` | RSS Feed | 抓取 RSS 文章 |
| FetchHNTool | `fetch_hn` | Hacker News API | 高分帖子 (>150) |
| FetchShowHNTool | `fetch_show_hn` | Hacker News API | 早期项目 (>50) |
| FetchGitHubTrendingTool | `fetch_github_trending` | GitHub Trending | 热门开源项目 |
| FetchURLTool | `fetch_url` | GitHub/Jina Reader | 深度抓取 README |
| SaveOnePagerTool | `save_one_pager` | 文件系统 | 保存 Markdown |

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
            return ToolResult_success(content=format_output(data))
        except Exception as e:
            return ToolResult_error(content=str(e))
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
    "limit": {"type": "integer", "description": "Max articles to fetch (default 10)"}
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
    limit = arguments.get("limit", 10)

    # 使用 feedparser 解析 RSS
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

    return ToolResult_success(content=format_articles(articles))
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

    return ToolResult_success(content=format_posts(posts))
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

    return ToolResult_success(content=format_posts(posts, "Show HN"))
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
    "limit": {"type": "integer", "description": "Max repos to fetch (default 10)"}
  },
  "required": []
}
```

### 输出格式

```json
{
  "content": "## GitHub Trending (Python, daily)\n\n### Repo 1\nName: ...\nURL: ...\nDescription: ...\nStars: ...\nLanguage: ...\n\n### Repo 2\n..."
}
```

### 实现要点

```python
GITHUB_TRENDING = "https://github.com/trending"

async def execute(self, arguments: dict, context: ToolContext) -> ToolResult:
    language = arguments.get("language", "python")
    since = arguments.get("since", "daily")
    limit = arguments.get("limit", 10)

    # 构建 URL
    url = f"{GITHUB_TRENDING}/{language}?since={since}"

    # 使用 aiohttp 抓取 HTML
    html = await fetch_html(url)

    # 解析 HTML
    repos = parse_trending_html(html, limit)

    return ToolResult_success(content=format_repos(repos))
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
        return ToolResult_success(content=f"## GitHub README\n\n{content}")

    # 其他 URL → Jina Reader
    jina_url = f"https://r.jina.ai/{url}"
    content = await fetch_text(jina_url)
    return ToolResult_success(content=f"## Article Content\n\n{content}")

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

保存情报一页纸到文件系统。

### 输入 Schema

```json
{
  "type": "object",
  "properties": {
    "title": {"type": "string", "description": "Project/tool name"},
    "content": {"type": "string", "description": "One-Pager content in Markdown"},
    "filename": {"type": "string", "description": "Output filename (optional)"}
  },
  "required": ["title", "content"]
}
```

### 输出格式

```json
{
  "content": "One-Pager saved: ~/.harness/scraper/2026-06-13/project-name.md"
}
```

### 实现要点

```python
OUTPUT_DIR = Path.home() / ".harness" / "scraper"

async def execute(self, arguments: dict, context: ToolContext) -> ToolResult:
    title = arguments["title"]
    content = arguments["content"]
    filename = arguments.get("filename", sanitize_filename(title))

    # 按日期分目录
    date_dir = OUTPUT_DIR / datetime.now().strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)

    # 写入文件
    file_path = date_dir / f"{filename}.md"
    file_path.write_text(content, encoding="utf-8")

    # 更新 MEMORY.md
    update_memory_md(title, filename)

    return ToolResult_success(
        content=f"One-Pager saved: {file_path}",
        metadata={"path": str(file_path)}
    )
```

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
    content="...",
    success=True,
)

# 失败
return ToolResult(
    content=f"Error: {str(e)}",
    success=False,
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

        return ToolResult(content=format_posts(posts))
```

```python
# tools/__init__.py
from .fetch_reddit import FetchRedditTool

__all__ = [
    "FetchRSSTool",
    "FetchHNTool",
    "FetchShowHNTool",
    "FetchGitHubTrendingTool",
    "FetchURLTool",
    "SaveOnePagerTool",
    "FetchRedditTool",  # 新增
]
```