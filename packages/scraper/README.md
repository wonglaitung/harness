# Harness Scraper

AI 情报抽取系统 - 自动化抓取和分析 AI 行业趋势。

## 功能

- **数据源**: RSS 博客、Hacker News、Reddit、X (via RSSHub)
- **智能过滤**: 粗筛 + LLM 裁判层
- **深度探针**: GitHub README 抓取、Jina Reader 备选
- **输出**: One-Pager Markdown 文件

## 快速开始

```bash
# 安装
cd packages/scraper
uv sync

# 创建配置文件
uv run harness-scraper config
# 编辑 ~/.harness/scraper.yaml 添加 API Key

# 运行一次
uv run harness-scraper run --once

# 持续运行 (每 12 小时)
uv run harness-scraper run
```

## 配置

配置文件: `~/.harness/scraper.yaml`

```yaml
llm:
  provider: "openai"
  base_url: "https://api.openai.com/v1"
  api_key: ""  # 或设置 HARNESS_LLM_API_KEY 环境变量
  model: "gpt-4o-mini"

sources:
  rss:
    - url: "https://www.anthropic.com/research/rss"
      name: "Anthropic Research"
  hacker_news:
    min_points: 150
```

## 支持的 LLM

| 提供者 | base_url | 说明 |
|-------|----------|------|
| 本地 vLLM | `http://localhost:8000/v1` | 免费 |
| 硅基流动 | `https://api.siliconflow.cn/v1` | ~0.01元/千token |
| DeepSeek | `https://api.deepseek.com/v1` | ~0.01元/千token |
| OpenAI | `https://api.openai.com/v1` | gpt-4o-mini |

## 输出示例

`~/.harness/scraper/2026-06-13/mcp.md`:

```markdown
# Model Context Protocol

## 技术定义 (What)
MCP 是一个开放协议，用于标准化大模型与外部数据源的通信方式。

## 行业痛点 (Why)
每个 AI 平台都需要单独对接各种数据源，重复造轮子。

## 旧范式 vs 新范式
- **旧做法**: 各平台各自为战
- **新做法**: MCP 提供统一协议

## 核心线索
- GitHub: https://github.com/modelcontextprotocol/servers
```

## 架构

```
数据源 → 粗筛 → LLM裁判 → 深度探针 → One-Pager
 RSS      关键词   判断新范式  GitHub README   Markdown文件
  HN      高分跳过             Jina Reader
```

## 详细文档

- [实现计划](docs/plan.md)
