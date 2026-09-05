# 06 - 配置说明

## 配置层级

Scraper 按以下优先级加载配置：

1. **环境变量**（最高优先级）
2. **配置文件** `~/.harness/scraper.yaml`
3. **默认值**（最低优先级）

## 配置文件

### 位置

```
~/.harness/scraper.yaml
```

### 创建配置文件

```bash
harness-scraper config
```

### 完整配置示例

```yaml
# Harness Scraper Configuration
# https://github.com/wonglaitung/harness/tree/main/packages/scraper

# LLM Configuration - Used by SDK Agent
llm:
  provider: "openai"
  base_url: "https://api.openai.com/v1"
  api_key: ""  # Or set via HARNESS_LLM_API_KEY env var
  model: "gpt-4o-mini"
  temperature: 0.1
  max_tokens: 8192

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
  directory: "packages/scraper/output"
```

## LLM 配置

### 配置项

| 项 | 类型 | 默认值 | 说明 |
|----|------|--------|------|
| `provider` | str | `openai` | 提供者类型 |
| `base_url` | str | OpenAI API URL | API 基础 URL |
| `api_key` | str | `None` | API Key |
| `model` | str | `gpt-4o-mini` | 模型名称 |
| `temperature` | float | `0.1` | 生成温度 |
| `max_tokens` | int | `8192` | 最大输出 token（8K，留 ~56K 给输入） |

**max_tokens 说明**：
- 默认 8192（8K）输出 token
- 对于 64K context 模型，留约 56K 给输入 context
- 情报抽取任务通常需要较长输出（One-Pager 生成）

### 支持的 LLM 提供者

所有 OpenAI 兼容的 API 都使用 `provider: openai`：

#### OpenAI 官方

```yaml
llm:
  provider: "openai"
  base_url: "https://api.openai.com/v1"
  api_key: "sk-xxx"
  model: "gpt-4o-mini"  # 或 gpt-4o, gpt-4-turbo
```

#### DeepSeek

```yaml
llm:
  provider: "openai"
  base_url: "https://api.deepseek.com/v1"
  api_key: "sk-xxx"
  model: "deepseek-chat"
```

#### 硅基流动 (SiliconFlow)

```yaml
llm:
  provider: "openai"
  base_url: "https://api.siliconflow.cn/v1"
  api_key: "sk-xxx"
  model: "Qwen/Qwen2.5-7B-Instruct"
```

#### 智谱 AI

```yaml
llm:
  provider: "openai"
  base_url: "https://open.bigmodel.cn/api/paas/v4"
  api_key: "xxx"
  model: "glm-4-flash"
```

#### 本地 vLLM

```yaml
llm:
  provider: "openai"
  base_url: "http://localhost:8000/v1"
  api_key: ""  # 本地模型不需要
  model: "Qwen2.5-7B-Instruct"
```

#### 本地 Ollama

```yaml
llm:
  provider: "openai"
  base_url: "http://localhost:11434/v1"
  api_key: ""
  model: "qwen2.5:7b"
```

### 模型选择建议

| 场景 | 推荐模型 | 原因 |
|------|---------|------|
| **成本敏感** | DeepSeek / 硅基流动 | ~0.01 元/千 token |
| **质量优先** | GPT-4o / Claude | 最佳推理能力 |
| **本地部署** | Qwen2.5-7B | 开源，性能好 |
| **快速测试** | gpt-4o-mini | 便宜，快速 |

## 数据源配置

### RSS 源

```yaml
sources:
  rss:
    - url: "https://openai.com/blog/rss.xml"
      name: "OpenAI Blog"
    - url: "https://huggingface.co/blog/feed.xml"
      name: "Hugging Face Blog"
    - url: "https://www.anthropic.com/research/rss"
      name: "Anthropic Research"
```

**推荐 RSS 源**：

| 源 | URL | 频率 |
|----|-----|------|
| OpenAI Blog | https://openai.com/blog/rss.xml | 每周 1-2 篇 |
| Anthropic | https://www.anthropic.com/research/rss | 每周 1-2 篇 |
| Hugging Face | https://huggingface.co/blog/feed.xml | 每周 2-3 篇 |
| Google AI | https://blog.google/technology/ai/rss/ | 每周 2-3 篇 |

### Hacker News

```yaml
sources:
  hacker_news:
    min_points: 150  # 最低分数阈值
```

**阈值建议**：

| 阈值 | 效果 |
|------|------|
| `100` | 更多内容，噪音增加 |
| `150` | 平衡质量和数量（推荐） |
| `200` | 高质量，可能漏掉早期项目 |

### GitHub Trending

```yaml
sources:
  github_trending:
    languages: ["python", "typescript"]
    since: "daily"
```

**语言建议**：

- AI 相关：`python`, `typescript`, `jupyter-notebook`
- 前端相关：`typescript`, `javascript`, `vue`
- 系统相关：`rust`, `go`, `c++`

**时间范围**：

| 值 | 说明 |
|----|------|
| `daily` | 今日热门 |
| `weekly` | 本周热门 |
| `monthly` | 本月热门 |

## 输出配置

```yaml
output:
  directory: ""  # 默认使用 packages/scraper/output/
```

**注意**：默认输出目录已改为 `packages/scraper/output/`（项目内），便于版本管理。如需自定义，可在配置文件中设置。

### 目录结构

```
packages/scraper/output/
├── MEMORY.md                    # 已处理项目记录（最近 30 天）
├── archive/
│   ├── MEMORY-2026-05.md        # 月度归档
│   └── MEMORY-2026-04.md
├── 2026-06-13/                  # 按日期分目录
│   ├── ai/                      # AI 情报 (domain="ai")
│   │   ├── mcp.md
│   │   └── autoresearch.md
│   └── stocks/                  # 股票分析 (domain="stocks")
│       ├── 00700.md
│       └── macro.md
├── 2026-06-14/
│   └── ...
```

### MEMORY.md 自动管理

- **自动记录**：每次保存 One-Pager 时自动更新 MEMORY.md
- **自动归档**：超过 30 天的条目移至 `archive/MEMORY-YYYY-MM.md`
- **避免重复**：SDK 加载 MEMORY.md 避免重复提取相同内容

### 领域分类

使用 `save_one_pager` 时可指定 `domain` 参数：

| domain | 子目录 | 用途 |
|--------|--------|------|
| `ai` | `ai/` | AI 情报一页纸 |
| `stocks` | `stocks/` | 股票分析报告 |
| 不指定 | 根目录 | 通用内容 |

## 依赖配置

### 金融数据依赖

使用港股和财经工具需要安装额外依赖：

```bash
# 在 scraper 目录安装
cd packages/scraper
uv sync

# 或手动安装
pip install akshare>=1.12.0 yfinance>=0.2.0 pandas>=2.0.0
```

| 包 | 版本 | 用途 | 数据源 |
|---|------|------|--------|
| `akshare` | >=1.12.0 | 港股行情、财经新闻 | 东方财富 |
| `yfinance` | >=0.2.0 | 美国国债收益率 | Yahoo Finance |
| `pandas` | >=2.0.0 | 数据处理 | - |

**数据源稳定性**：

| 数据源 | API | 稳定性 | 维护方 |
|-------|-----|--------|-------|
| 东方财富 | `ak.stock_hk_spot_em()` | 高 | 开源社区 |
| 东方财富港股新闻 | `ak.stock_news_em(symbol="港股")` | 高 | 开源社区 |
| Yahoo Finance | `yf.Ticker("^TNX")` | 高 | 开源社区 |

**推荐使用 AkShare**：社区维护，API 稳定，无需处理反爬虫。

## 环境变量

### 支持的环境变量

| 变量 | 对应配置项 |
|------|-----------|
| `HARNESS_LLM_PROVIDER` | `llm.provider` |
| `HARNESS_LLM_BASE_URL` | `llm.base_url` |
| `HARNESS_LLM_API_KEY` | `llm.api_key` |
| `HARNESS_LLM_MODEL` | `llm.model` |
| `HARNESS_LLM_TEMPERATURE` | `llm.temperature` |
| `HARNESS_LLM_MAX_TOKENS` | `llm.max_tokens` |

### 使用示例

```bash
# 设置环境变量
export HARNESS_LLM_API_KEY="sk-xxx"
export HARNESS_LLM_MODEL="gpt-4o"

# 运行（配置文件中的值会被覆盖）
harness-scraper
```

## 配置加载逻辑

```python
def load_config(config_path: Path | None = None) -> ScraperConfig:
    """加载配置，优先级：环境变量 > 配置文件 > 默认值"""

    # 1. 读取配置文件
    if config_path and config_path.exists():
        yaml_config = yaml.safe_load(config_path)
    else:
        yaml_config = {}

    # 2. 环境变量覆盖
    llm_config = LLMConfig(
        provider=os.getenv("HARNESS_LLM_PROVIDER", yaml_config.get("provider", "openai")),
        base_url=os.getenv("HARNESS_LLM_BASE_URL", yaml_config.get("base_url", "...")),
        api_key=os.getenv("HARNESS_LLM_API_KEY", yaml_config.get("api_key")),
        ...
    )

    return ScraperConfig(llm=llm_config, ...)
```

## 配置最佳实践

### 安全

```yaml
# ❌ 不要在配置文件中硬编码 API Key
llm:
  api_key: "sk-xxx"  # 不安全

# ✅ 使用环境变量
llm:
  api_key: ""  # 通过 HARNESS_LLM_API_KEY 设置
```

### 多环境

```bash
# 开发环境
export HARNESS_LLM_MODEL="gpt-4o-mini"

# 生产环境
export HARNESS_LLM_MODEL="gpt-4o"
```

### 成本控制

```yaml
llm:
  temperature: 0.1   # 低温度，减少随机性
  max_tokens: 8192   # 默认 8K 输出 token
  model: "gpt-4o-mini"  # 使用更便宜的模型
```

## 故障排查

### 查看当前配置

```bash
harness-scraper config --show
```

### 常见问题

| 问题 | 原因 | 解决方法 |
|------|------|---------|
| API Key 无效 | 未设置或格式错误 | 检查环境变量或配置文件 |
| 模型不存在 | 模型名称错误 | 查看提供者文档 |
| 连接超时 | 网络问题或 URL 错误 | 检查 base_url |
| 认证失败 | API Key 权限不足 | 检查 API Key 权限 |

## GitHub Actions 配置

### 必需的 GitHub Secrets

在 GitHub 仓库设置 → Secrets and variables → Actions 中配置：

| Secret | 说明 | 示例 |
|--------|------|------|
| `EMAIL_SENDER` | 发件邮箱 | `your@163.com` |
| `EMAIL_PASSWORD` | 邮箱授权码 | `xxxxxxxxxxxx` |
| `SMTP_SERVER` | SMTP 服务器 | `smtp.163.com` |
| `RECIPIENT_EMAIL` | 收件邮箱 | `target@gmail.com` |
| `LLM_API_KEY` | LLM API Key | `sk-xxx` |
| `LLM_BASE_URL` | LLM API URL | `https://api.openai.com/v1` |
| `LLM_MODEL` | 模型名称 | `gpt-4o-mini` |

### 邮箱配置说明

#### 163 邮箱

1. 登录 163 邮箱
2. 设置 → POP3/SMTP/IMAP → 开启 SMTP
3. 获取授权码（不是邮箱密码）
4. 配置：
   - `SMTP_SERVER`: `smtp.163.com`
   - `EMAIL_PASSWORD`: 授权码

#### QQ 邮箱

1. 登录 QQ 邮箱
2. 设置 → 账户 → POP3/SMTP 服务
3. 获取授权码
4. 配置：
   - `SMTP_SERVER`: `smtp.qq.com`
   - `EMAIL_PASSWORD`: 授权码

#### Gmail

1. 开启两步验证
2. 生成应用专用密码
3. 配置：
   - `SMTP_SERVER`: `smtp.gmail.com`
   - `EMAIL_PASSWORD`: 应用专用密码

### 工作流文件位置

```
.github/workflows/daily-intelligence.yml
```

### 工作流配置

```yaml
name: 每日情报推送

on:
  # 每天上午 6:00 香港时间 (UTC 22:00 前一天)
  schedule:
    - cron: '0 22 * * *'
  # 允许手动触发
  workflow_dispatch:
    inputs:
      send_email:
        description: '是否发送邮件'
        default: 'true'
      skill:
        description: '运行特定技能'
        default: 'all'
```

### 手动触发工作流

1. 进入 GitHub 仓库 → Actions
2. 选择 "每日情报推送" workflow
3. 点击 "Run workflow"
4. 选择参数：
   - `send_email`: 是否发送邮件
   - `skill`: `all` / `ai-intelligence` / `hk-stocks-alpha`

### 查看 CI 运行结果

```bash
# 本地查看生成的文件
ls packages/scraper/output/$(date +%Y-%m-%d)/ai/
ls packages/scraper/output/$(date +%Y-%m-%d)/stocks/
```

## 下一步

- [01-overview.md](./01-overview.md) - 了解 Scraper 整体架构
- [04-skills.md](./04-skills.md) - 了解技能系统
- [05-cli.md](./05-cli.md) - 了解 CLI 使用