# Harness Scraper

AI 情报抽取系统 - 自动化抓取和分析 AI 行业趋势、港股市场异动。

## 功能

### AI 情报抽取
- **数据源**: RSS 博客、Hacker News、GitHub Trending
- **智能过滤**: 粗筛 + LLM 裁判层
- **深度探针**: GitHub README 抓取、Jina Reader 备选
- **输出**: One-Pager Markdown 文件

### 港股 Alpha 监控
- **数据源**: AkShare (东方财富)、财联社快讯、Yahoo Finance
- **异动监控**: 高成交量、大幅涨跌个股
- **宏观追踪**: 美国国债收益率
- **输出**: 股票分析报告

## 快速开始

```bash
# 安装
cd packages/scraper
uv sync

# 创建配置文件
uv run harness-scraper config
# 编辑 ~/.harness/scraper.yaml 添加 API Key

# AI 情报抽取 (默认)
uv run harness-scraper --skill ai-intelligence

# 港股 Alpha 监控
uv run harness-scraper --skill hk-stocks-alpha
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

## 技能系统

使用技能文件定义领域特定的判断标准和工作流程：

| 技能 | 用途 | 数据源 |
|------|------|--------|
| `ai-intelligence` | AI 情报抽取 | RSS、HN、GitHub |
| `hk-stocks-alpha` | 港股异动监控 | AkShare、财联社 |

```bash
# AI 情报抽取
uv run harness-scraper --skill ai-intelligence

# 港股 Alpha 监控
uv run harness-scraper --skill hk-stocks-alpha

# 自定义技能
uv run harness-scraper --skill my-custom
```

## 工具

### AI 情报工具

| 工具 | 名称 | 用途 |
|------|------|------|
| FetchRSSTool | `fetch_rss` | 抓取 RSS 文章 |
| FetchHNTool | `fetch_hn` | HN 高分帖子 (>150) |
| FetchShowHNTool | `fetch_show_hn` | Show HN 早期项目 (>50) |
| FetchGitHubTrendingTool | `fetch_github_trending` | GitHub Trending |
| FetchURLTool | `fetch_url` | 深度抓取 README |

### 金融工具

| 工具 | 名称 | 数据源 | 用途 |
|------|------|--------|------|
| FetchHKEXTool | `fetch_hkex` | AkShare | 港股实时行情、异动监控 |
| FetchFinancialNewsTool | `fetch_financial_news` | AkShare + yfinance | 财经快讯、国债收益率 |

### 输出工具

| 工具 | 名称 | 用途 |
|------|------|------|
| SaveOnePagerTool | `save_one_pager` | 保存 Markdown One-Pager |

## 输出示例

### AI 情报

`~/.harness/scraper/2026-06-13/ai/mcp.md`:

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

### 股票分析

`~/.harness/scraper/2026-06-13/stocks/00700.md`:

```markdown
# 腾讯控股 (00700.HK) - 回购公告

## 事件概述 (What)
腾讯宣布回购 100 亿港元股票，回购期限 2026-07-01 至 2026-12-31。

## 市场影响 (Why)
回购通常提振市场信心，表明管理层认为股价被低估。

## 数据支撑
- 股价变化: +5.2%
- 成交额: 125M 港元
- 回购规模: 100 亿港元

## 风险提示
- 回购执行进度可能不及预期
- 市场情绪受宏观影响

## 核心线索
- 来源: 东方财富
- 时间: 2026-06-13 14:30
```

## 目录结构

```
~/.harness/scraper/
├── 2026-06-13/
│   ├── ai/              # AI 情报
│   │   ├── mcp.md
│   │   └── autoresearch.md
│   └── stocks/          # 股票分析
│       ├── 00700.md
│       └── macro.md
├── 2026-06-14/
└── MEMORY.md            # 已处理项目记录
```

## 架构

```
数据源 → Agent (LLM) → 工具调用 → One-Pager
  RSS                      fetch_rss        Markdown 文件
  HN                       fetch_hn         (ai/ 或 stocks/)
  GitHub                   fetch_github_trending
  AkShare                  fetch_hkex
  财联社                   fetch_financial_news
```

**核心设计**：使用 Harness SDK 的 AgentHarness，通过技能文件定义领域知识，让 LLM 自主决策工具调用和数据筛选。

## 详细文档

- [概述](docs/01-overview.md) - 架构设计
- [工具系统](docs/03-tools.md) - 所有工具详解
- [技能系统](docs/04-skills.md) - 技能文件格式和示例
- [CLI 使用](docs/05-cli.md) - 命令行和 CI/自动化
- [配置说明](docs/06-configuration.md) - 完整配置选项

## CI 自动化

### GitHub Actions 每日推送

项目内置 GitHub Actions 工作流，自动每日运行并发送邮件：

```yaml
# .github/workflows/daily-intelligence.yml
on:
  schedule:
    - cron: '0 22 * * *'  # 每天 06:00 HKT
  workflow_dispatch:       # 手动触发
```

**配置 GitHub Secrets**：

| Secret | 说明 |
|--------|------|
| `EMAIL_SENDER` | 发件邮箱 |
| `EMAIL_PASSWORD` | 邮箱授权码 |
| `SMTP_SERVER` | SMTP 服务器 |
| `RECIPIENT_EMAIL` | 收件邮箱 |
| `LLM_API_KEY` | LLM API Key |
| `LLM_BASE_URL` | LLM API URL |
| `LLM_MODEL` | 模型名称 |

**邮件通知**：
- AI 情报日报（`ai/` 目录）
- 港股异动日报（`stocks/` 目录）

### 本地脚本

```bash
# 运行情报抽取（带超时）
cd packages/scraper
uv run python scripts/run_scraper.py --skill ai-intelligence --timeout 180
uv run python scripts/run_scraper.py --skill hk-stocks-alpha

# 发送邮件
uv run python scripts/send_intelligence_email.py
uv run python scripts/send_intelligence_email.py --dry-run  # 预览
```
