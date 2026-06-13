# 04 - 技能系统

## 技能概述

技能（Skill）定义了领域知识：
- 判断标准：什么是高价值内容？
- 已知实体：已成熟的项目/公司，避免重复
- 输出模板：One-Pager 的格式要求
- 工作流程：领域特定的抓取策略

## 技能文件位置

技能文件按以下优先级加载：

1. **仓库内置技能** (`packages/scraper/skills/`) - CI/CD 和首次运行使用
2. **用户技能目录** (`~/.harness/skills/`) - 自定义技能

```
# 仓库内置（优先）
packages/scraper/skills/
├── ai-intelligence.md    # AI 情报抽取
├── hk-stocks-alpha.md    # 港股 Alpha 监控
└── ...

# 用户目录（备选）
~/.harness/skills/
├── ai-intelligence.md    # 用户自定义版本
├── stock-analysis.md     # 其他技能
└── custom.md             # 自定义技能
```

### 加载逻辑

```python
def load_skill(skill_name: str) -> str | None:
    # 1. 优先查找仓库内置技能（CI/CD 场景）
    repo_skill_path = REPO_SKILL_DIR / f"{skill_name}.md"
    if repo_skill_path.exists():
        return repo_skill_path.read_text()

    # 2. 查找用户技能目录
    skill_path = SKILL_DIR / f"{skill_name}.md"
    if skill_path.exists():
        return skill_path.read_text()

    return None
```

**设计原因**：
- CI/CD 环境需要稳定的内置技能
- 用户可以在 `~/.harness/skills/` 覆盖或自定义技能

## 技能文件格式

### 基本结构

```markdown
# 技能名称

简短描述技能的作用。

## 判断标准

### ✅ 应该标记为高价值

| 情况 | 示例 | 原因 |
|-----|------|------|
| ... | ... | ... |

### ❌ 应该过滤的内容

| 情况 | 示例 | 原因 |
|-----|------|------|
| ... | ... | ... |

## 已知实体

成熟项目/公司列表，避免重复。

## 工作流程

1. 使用 fetch_xxx 抓取数据
2. 根据 YYY 标准筛选
3. 使用 save_one_pager 保存

## 输出模板

One-Pager 的格式要求。
```

## 内置技能

### ai-intelligence.md

AI 行业情报抽取技能。

**判断标准**：

| 类型 | 描述 | 示例 |
|------|------|------|
| **Type A** | 新范式/行业黑话 | taste-skill, vibe-coding |
| **Type B** | 新模型架构/微调流派 | Hermes, Agent runtime |
| **Type C** | 新评测/脚手架工具 | MCP, Harness, GGUF |

**已知成熟项目**：

- 推理框架：vLLM, TGI, llama.cpp, Ollama
- 应用框架：LangChain, LlamaIndex, Haystack
- 模型：LLaMA, Mistral, Qwen, ChatGLM

**输出模板**：

```markdown
# [项目名称]

## 技术定义 (What)
...

## 行业痛点 (Why)
...

## 旧范式 vs 新范式
- **旧做法**：...
- **新做法**：...

## 生产力影响 (How)
...

## 采用成本
...

## 核心线索
- GitHub：...
- 来源：...
- 发布时间：...
```

### hk-stocks-alpha.md

港股 Alpha 事件捕获技能。

**用途**：监控港股异动、捕捉市场事件、生成投资分析报告。

**数据源**：

| 工具 | 数据源 | 用途 |
|------|--------|------|
| `fetch_hkex` | AkShare (东方财富) | 港股实时行情、异动监控 |
| `fetch_financial_news` | 财联社 + yfinance | 财经快讯、美国国债收益率 |

**判断标准**：

| 类型 | 描述 | 示例 |
|------|------|------|
| **Type A** | 公司事件 | 回购、减持、并购、业绩惊喜 |
| **Type B** | 行业/宏观 | 政策变化、监管动态、利率变动 |
| **Type C** | 技术/情绪 | 异常成交量、突破关键技术位 |

**噪音过滤**：

- 常规分红公告
- 小额回购（< 1 亿港元）
- 分析师评级（滞后指标）
- 常规产品更新

**工作流程**：

1. 使用 `fetch_hkex` 获取异动股票（volume_threshold=50M, pct_threshold=3%）
2. 使用 `fetch_financial_news` 获取财经快讯（keywords=["港股", "监管", "政策"]）
3. 使用 `fetch_financial_news source=macro` 获取美国国债收益率
4. 结合技术面和消息面，识别 Alpha 事件
5. 使用 `save_one_pager domain="stocks"` 保存分析报告

**输出模板**：

```markdown
# [公司/事件]

## 事件概述 (What)
简述发生了什么事件。

## 市场影响 (Why)
分析事件对股价/行业的潜在影响。

## 数据支撑
- 股价变化：+5.2%
- 成交额：125M 港元（较平日 +300%）
- 换手率：0.45%
- 时间窗口：2026-06-13

## 消息面
- 相关新闻：[链接]
- 宏观背景：美联储利率、美债收益率

## 风险提示
- 潜在风险 1
- 潜在风险 2

## 核心线索
- 来源：东方财富、财联社
- 时间：2026-06-13 14:30
- 相关标的：00700.HK, 03690.HK
```

**使用示例**：

```bash
# 创建技能文件
mkdir -p ~/.harness/skills
cat > ~/.harness/skills/hk-stocks-alpha.md << 'EOF'
# HK Stocks Alpha Event Capture

Monitor HK stock market for alpha events: major moves, corporate actions, policy changes.

## Data Sources

- `fetch_hkex`: HK stock real-time quotes via AkShare
- `fetch_financial_news`: Cailian news + US Treasury yields

## Judgment Criteria

### Type A: Company Events
- Buybacks > 100M HKD
- Insider trading disclosures
- M&A announcements
- Earnings surprises > 5%

### Type B: Sector/Macro
- Policy changes (regulatory, tax)
- Interest rate decisions
- Industry rotation signals

### Type C: Technical/Sentiment
- Volume spike > 3x average
- Price break key levels
- Unusual options activity

## Noise Filter

- Routine dividends
- Small buybacks (< 100M HKD)
- Analyst ratings (lagging indicator)

## Workflow

1. fetch_hkex (volume_threshold=50M, pct_threshold=3)
2. fetch_financial_news (keywords=["港股", "监管"])
3. fetch_financial_news (source="macro")
4. Synthesize findings
5. save_one_pager (domain="stocks")

## Output Template

# [Company/Event]

## Event Overview (What)
...

## Market Impact (Why)
...

## Data Support
- Price change: ...
- Volume: ...
- Time: ...

## News Context
- Related news: ...
- Macro backdrop: ...

## Risk Warning
...

## Key Clues
- Source: ...
- Time: ...
- Related tickers: ...
EOF

# 运行
harness-scraper --skill hk-stocks-alpha
```

### stock-analysis.md

股票市场分析技能。

**判断标准**：

| 类型 | 描述 |
|------|------|
| **Type A** | 基本面变化：财报惊喜、并购、新产品 |
| **Type B** | 行业/宏观趋势：监管变化、行业轮动 |
| **Type C** | 技术/情绪信号：异常成交量、情绪转变 |

**噪音过滤**：

- 常规财报（beat 1-2%）
- 分析师评级（滞后指标）
- 小幅产品更新

**输出模板**：

```markdown
# [公司/主题]

## 事件概述 (What)
...

## 市场影响 (Why)
...

## 数据支撑
- 股价变化：...
- 估值影响：...
- 时间窗口：...

## 风险提示
...

## 核心线索
- 来源：...
- 时间：...
- 相关标的：...
```

## 技能加载流程

```
IntelAgent.__init__(skill="ai-intelligence")
    │
    ↓
load_skill("ai-intelligence")
    │
    ↓
读取 ~/.harness/skills/ai-intelligence.md
    │
    ↓
拼接到 BASE_SYSTEM_PROMPT
    │
    ↓
传给 AgentHarness
```

## 创建自定义技能

### 步骤 1：创建文件

```bash
touch ~/.harness/skills/my-domain.md
```

### 步骤 2：编写内容

```markdown
# My Domain Intelligence

Extract intelligence from my domain.

## 判断标准

### ✅ 高价值内容

- 新产品发布
- 技术突破
- 市场变化

### ❌ 噪音

- 常规更新
- 营销内容
- 过时信息

## 工作流程

1. 使用 fetch_rss 抓取相关 RSS 源
2. 使用 fetch_hn 关注相关讨论
3. 根据 [判断标准] 筛选
4. 使用 save_one_pager 保存

## 输出模板

# [项目/事件]

## 概述
...

## 影响
...

## 行动建议
...
```

### 步骤 3：使用技能

```bash
harness-scraper --skill my-domain
```

## 技能最佳实践

### 判断标准要具体

❌ 差：

```markdown
## 判断标准

高价值内容：创新性、重要性、时效性
```

✅ 好：

```markdown
## 判断标准

### ✅ 高价值内容

| 情况 | 示例 | 原因 |
|-----|------|------|
| 新项目（<3个月） | autoresearch | 定义了新的自动化范式 |
| 新概念/黑话 | taste-skill | 社区新词，认知升级 |
```

### 已知实体列表要维护

定期更新已知实体列表，避免重复抓取：

```markdown
## 已知成熟项目

**推理框架**：vLLM, TGI, llama.cpp
**应用框架**：LangChain, LlamaIndex
**模型**：LLaMA, Mistral, Qwen
```

### 输出模板要结构化

使用固定的字段，便于阅读和比较：

```markdown
## 输出模板

# [项目名称]

## 技术定义 (What) - 用大白话解释
## 行业痛点 (Why) - 解决什么问题
## 旧范式 vs 新范式 - 对比
## 生产力影响 (How) - 实际价值
## 采用成本 - 时间、金钱、学习曲线
```

## 技能与 Agent 的协作

### Agent 如何使用技能

1. **理解任务**：Agent 收到"运行情报抽取"
2. **加载技能**：Skill 内容拼接到 System Prompt
3. **执行工具**：Agent 根据 Skill 中的工作流程调用工具
4. **判断内容**：Agent 根据 Skill 中的判断标准筛选
5. **生成输出**：Agent 按照 Skill 中的模板格式输出

### 技能不是硬编码

技能是**指导**而非**规则**：

- Agent 可以灵活调整策略
- 用户可以通过对话进一步指导
- 技能提供起点，Agent 提供智能

## 技能文件示例

完整的 ai-intelligence.md：

```markdown
# AI Intelligence Extraction Skill

Extract AI industry intelligence from web sources.

## Domain Focus

AI/ML industry: models, frameworks, tools, protocols, evaluation systems.

## Judgment Criteria

### Three Types of New Paradigms

**Type A: New Paradigms/Buzzwords**
- Community-formed new concept words
- Examples: taste-skill, vibe-coding, prompt-engineering

**Type B: New Model Architectures**
- New architectures, training methods, inference frameworks
- Examples: Hermes series, Agent runtime, MoE

**Type C: New Evaluation Tools**
- Automated evaluation frameworks, protocols, standards
- Examples: MCP, Harness, GGUF

### ✅ Should Mark as New Paradigm

| Situation | Example | Reason |
|-----------|---------|--------|
| New project (< 3 months) | karpathy/autoresearch | Just released, new paradigm |
| New concept/buzzword | taste-skill | New community term |
| New protocol/standard | MCP | New interoperability method |
| New tool category | browser-use | Opens new capability boundary |

### ❌ Should NOT Mark as New Paradigm

| Situation | Example | Reason |
|-----------|---------|--------|
| Mature project | vLLM, LangChain | Exists > 3 months, widely used |
| Pure tutorial | "How to use LangChain" | No new concept |
| Incremental update | "vLLM 0.5.0 released" | Version upgrade |
| Pure application | "AI email assistant" | Using existing tech |

## Known Mature Projects (Skip These)

**Inference Frameworks**: vLLM, TGI, llama.cpp, Ollama
**Application Frameworks**: LangChain, LlamaIndex, Haystack, Semantic Kernel
**Models**: LLaMA, Mistral, Qwen, ChatGLM
**Tools**: Transformers, PyTorch, TensorFlow
**Vector Databases**: Pinecone, Weaviate, Qdrant, Milvus

## Workflow

1. Use `fetch_rss` for official blogs
2. Use `fetch_hn` for high-score posts (min_points=150)
3. Use `fetch_show_hn` for early projects (min_points=50)
4. Use `fetch_github_trending` for Python/TypeScript trending
5. For promising items, use `fetch_url` to get README
6. Use `save_one_pager` to save intelligence

## One-Pager Template

# [Project Name]

## 技术定义 (What)
[Plain language explanation]

## 行业痛点 (Why)
[What problem does it solve]

## 旧范式 vs 新范式
- **旧做法**：[Old approach]
- **新做法**：[New approach]

## 生产力影响 (How)
[Actual value for developers]

## 采用成本
[Time, money, learning curve]

## 核心线索
- GitHub：[URL]
- 来源：[Source]
- 发布时间：[Date]

## Output Requirements

1. **Language**: Chinese for readability
2. **Concise**: Each field 2-3 sentences
3. **Actionable**: Provide GitHub link

## Notes

- Better to miss than over-report
- Focus on "first proposed time", not trending time
- Distinguish "popularity" from "innovation"
```