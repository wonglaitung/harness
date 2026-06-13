# 05 - CLI 使用指南

## 基本命令

### 运行情报抽取

```bash
# AI 情报抽取（默认）
harness-scraper

# 指定技能
harness-scraper --skill stock-analysis
harness-scraper --skill my-custom-skill

# 详细输出
harness-scraper -v
harness-scraper --verbose

# 自定义提示词
harness-scraper agent "只关注前端框架类项目"
```

### 配置管理

```bash
# 创建默认配置文件
harness-scraper config

# 查看当前配置
harness-scraper config --show
```

### 技能管理

```bash
# 列出可用技能
harness-scraper skills
```

## 命令详解

### agent 命令

运行情报抽取 Agent。

```bash
harness-scraper agent [OPTIONS] [PROMPT]
```

**选项**：

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--skill` | 技能名称 | `ai-intelligence` |
| `-v, --verbose` | 详细输出 | `False` |
| `PROMPT` | 自定义提示词 | 默认提示词 |

**示例**：

```bash
# 默认运行
harness-scraper agent

# 股票分析
harness-scraper agent --skill stock-analysis

# 自定义提示词
harness-scraper agent "这次关注 Rust 生态的新项目"

# 详细模式
harness-scraper agent -v
```

### config 命令

管理配置文件。

```bash
harness-scraper config [OPTIONS]
```

**选项**：

| 选项 | 说明 |
|------|------|
| `--show` | 显示当前配置 |

**示例**：

```bash
# 创建配置文件
harness-scraper config
# 输出: Created config file: ~/.harness/scraper.yaml

# 查看配置
harness-scraper config --show
# 输出:
# LLM: openai @ https://api.openai.com/v1
# Model: gpt-4o-mini
# Output: ~/.harness/scraper
```

### skills 命令

列出可用技能。

```bash
harness-scraper skills
```

**输出**：

```
Available skills in ~/.harness/skills:

  --skill ai-intelligence
  --skill stock-analysis

Usage:
  harness-scraper --skill stock-analysis
```

## 输出说明

### 运行输出

```
21:03:14 [INFO] harness_scraper.agent: Loaded skill: ai-intelligence
21:03:14 [INFO] harness_scraper.agent: Running IntelAgent with prompt: ...
21:03:15 [INFO] harness_scraper.tools.fetch_rss: Fetched 10 articles from ...
21:03:20 [INFO] harness_scraper.tools.fetch_hn: Fetched 15 posts with score >= 150
21:03:25 [INFO] harness_scraper.tools.save_one_pager: Saved: ~/.harness/scraper/2026-06-13/project.md

=== Agent Result ===
[Agent 输出内容]
```

### 生成文件

```
~/.harness/scraper/
├── 2026-06-13/
│   ├── project1.md
│   ├── project2.md
│   └── ...
├── 2026-06-14/
│   └── ...
└── MEMORY.md
```

## 环境变量

Scraper 支持通过环境变量覆盖配置：

```bash
# LLM 配置
export HARNESS_LLM_PROVIDER=openai
export HARNESS_LLM_BASE_URL=https://api.openai.com/v1
export HARNESS_LLM_API_KEY=sk-xxx
export HARNESS_LLM_MODEL=gpt-4o-mini
export HARNESS_LLM_TEMPERATURE=0.1
export HARNESS_LLM_MAX_TOKENS=2000

# 运行
harness-scraper
```

## 配置文件

### 配置文件位置

```
~/.harness/scraper.yaml
```

### 配置文件示例

```yaml
# Harness Scraper Configuration

# LLM Configuration
llm:
  provider: "openai"
  base_url: "https://api.openai.com/v1"
  api_key: ""  # Or set via HARNESS_LLM_API_KEY env var
  model: "gpt-4o-mini"
  temperature: 0.1
  max_tokens: 2000

  # Alternative: DeepSeek
  # provider: "openai"
  # base_url: "https://api.deepseek.com/v1"
  # api_key: "sk-xxx"
  # model: "deepseek-chat"

  # Alternative: Local vLLM
  # provider: "openai"
  # base_url: "http://localhost:8000/v1"
  # model: "Qwen2.5-7B-Instruct"

# Data Sources (for reference, skill may override)
sources:
  rss:
    - url: "https://openai.com/blog/rss.xml"
      name: "OpenAI Blog"
    - url: "https://huggingface.co/blog/feed.xml"
      name: "Hugging Face Blog"

  hacker_news:
    min_points: 150

  github_trending:
    languages: ["python", "typescript"]
    since: "daily"

# Output
output:
  directory: "~/.harness/scraper"
```

## 使用场景

### 日常 AI 情报追踪

```bash
# 每天运行一次
harness-scraper

# 查看生成的 One-Pagers
ls ~/.harness/scraper/$(date +%Y-%m-%d)/
```

### 股票市场监控

```bash
# 运行股票分析
harness-scraper --skill stock-analysis

# 查看分析结果
cat ~/.harness/scraper/$(date +%Y-%m-%d)/*.md
```

### 自定义领域

```bash
# 创建自定义技能
cat > ~/.harness/skills/crypto-analysis.md << 'EOF'
# Crypto Intelligence

Extract crypto/blockchain intelligence.

## Judgment Criteria
...
EOF

# 运行
harness-scraper --skill crypto-analysis
```

## 常见问题

### Q: 为什么没有生成 One-Pager？

**可能原因**：

1. **没有找到高价值内容**：Agent 根据技能判断标准过滤了所有内容
2. **LLM 配置错误**：检查 API Key、Base URL
3. **网络问题**：检查是否能访问数据源

**解决方法**：

```bash
# 使用 verbose 模式查看详细日志
harness-scraper -v
```

### Q: 如何添加新的 RSS 源？

**方法 1：修改配置文件**

```yaml
sources:
  rss:
    - url: "https://new-rss-source.com/feed.xml"
      name: "New Source"
```

**方法 2：使用自定义提示词**

```bash
harness-scraper agent "使用 fetch_rss 抓取 https://new-source.com/feed.xml"
```

### Q: 如何使用本地模型？

```yaml
llm:
  provider: "openai"
  base_url: "http://localhost:8000/v1"  # vLLM 或 Ollama
  model: "Qwen2.5-7B-Instruct"
  api_key: ""  # 本地模型不需要
```

### Q: 如何避免重复抓取？

1. **MEMORY.md**：Agent 自动参考记忆文件
2. **技能中的已知实体列表**：在技能中列出成熟项目

```markdown
## Known Mature Projects

vLLM, LangChain, Ollama, ...
```

## 进阶用法

### Python API

```python
import asyncio
from harness_scraper import IntelAgent, load_config

async def main():
    # 加载配置
    config = load_config()

    # 创建 Agent
    agent = IntelAgent(
        config,
        skill="ai-intelligence",
        memory_path="~/.harness/scraper/MEMORY.md",
    )

    # 运行
    result = await agent.run("提取 AI 情报", verbose=True)
    print(result.content)

asyncio.run(main())
```

### 定时运行

#### 方式 1：GitHub Actions CI（推荐）

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
| `EMAIL_PASSWORD` | 邮箱密码/授权码 |
| `SMTP_SERVER` | SMTP 服务器 (如 `smtp.163.com`) |
| `RECIPIENT_EMAIL` | 收件邮箱 |
| `LLM_API_KEY` | LLM API Key |
| `LLM_BASE_URL` | LLM API URL |
| `LLM_MODEL` | 模型名称 |

**手动触发**：

1. 进入 GitHub Actions 页面
2. 选择 "每日情报推送" workflow
3. 点击 "Run workflow"
4. 可选择运行特定技能或全部

#### 方式 2：本地 cron

```bash
# 使用 cron 定时运行
crontab -e

# 每天早上 9 点运行
0 9 * * * cd /path/to/harness/packages/scraper && uv run python scripts/run_scraper.py --skill ai-intelligence
0 9 * * * cd /path/to/harness/packages/scraper && uv run python scripts/run_scraper.py --skill hk-stocks-alpha
```

#### 方式 3：手动运行脚本

```bash
# 运行 AI 情报抽取
cd packages/scraper
uv run python scripts/run_scraper.py --skill ai-intelligence --timeout 180

# 运行港股监控
uv run python scripts/run_scraper.py --skill hk-stocks-alpha

# 发送邮件（可选）
uv run python scripts/send_intelligence_email.py           # 发送
uv run python scripts/send_intelligence_email.py --dry-run # 预览
```

### 输出目录结构

```
~/.harness/scraper/
├── 2026-06-13/
│   ├── ai/              # AI 情报 (domain="ai")
│   │   ├── mcp.md
│   │   └── autoresearch.md
│   └── stocks/          # 股票分析 (domain="stocks")
│       ├── 00700.md
│       └── macro.md
├── 2026-06-14/
│   └── ...
└── MEMORY.md            # 已处理项目记录
```

### 邮件通知

CI 工作流会发送两封邮件：

1. **AI 情报日报** - 包含 `ai/` 目录下的 One-Pagers
2. **港股异动日报** - 包含 `stocks/` 目录下的 One-Pagers

邮件使用 HTML 格式，支持 Markdown 渲染（表格、列表、链接）。