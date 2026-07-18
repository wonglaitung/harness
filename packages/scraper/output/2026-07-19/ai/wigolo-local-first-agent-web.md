# wigolo — 本地优先Agent Web智能层新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首次定义"Agent Web Surface"概念——Agent的统一Web智能层，将搜索/抓取/爬行/提取/缓存/相似发现/研究/自主收集整合为一个本地优先的持久化表面 |
| 采用广度 | ☆☆☆/5 | 支持 Claude Code, Cursor, Codex, Gemini CLI, VS Code, Windsurf, Zed, Antigravity, LangChain, CrewAI, LlamaIndex, Vercel AI SDK, n8n 等主流Agent框架和编辑器 |
| 时间新鲜 | ☆☆☆☆☆/5 | 公测阶段，2025年7月GitHub Trending |
| 社区热度 | ☆☆☆/5 | GitHub 192 stars/day (TypeScript trending), HN未单独发帖但MCP生态内高关注度 |
| **总体判断** | ✅ 新范式 | **本地优先Agent Web基础设施新范式** |

## 技术定义 (What)

wigolo 是一个本地优先的Agent Web智能层，为AI Agent提供统一的Web操作表面——搜索、抓取、爬行、提取、缓存、相似发现、研究和自主收集循环。核心特点：零API密钥、零云依赖、零按量计费，所有数据存储在本地 `~/.wigolo/` 目录下。

## 行业痛点 (Why)

当前AI Agent的Web能力碎片化严重：搜索依赖付费API（Tavily/Exa），抓取需要独立工具，缓存没有统一层，每次查询都要重新付费。Agent在Web操作上被迫在多个工具间手动切换，且无法积累Web知识。

## 旧范式 vs 新范式

- **旧做法**：Agent分别调用搜索API（Tavily $0.01/query）、抓取工具（Firecrawl）、向量数据库，每个工具独立付费、独立配置，查询结果无法持久化复用
- **新做法**：wigolo作为Agent的统一Web表面，一次MCP调用即可并行多引擎搜索，结果自动缓存可离线复用，每个结果携带byte-exact provenance和explainable score，零API密钥即可运行

## 生产力影响 (How)

1. **零成本Web操作**：搜索/抓取/缓存/相似发现完全本地运行，无按量计费
2. **证据级输出**：每个结果携带verbatim excerpt、citation_id、source_span（byte精确位置）、evidence_score（语义+词汇+引擎共识三维评分）
3. **诚实输出**：过期缓存、失败抓取、降级后端、截断都被显式标记，不会伪装为成功数据
4. **持久化Web记忆**：所有页面自动缓存，支持关键词/语义混合检索，支持变更检测（diff+watch）
5. **自主研究循环**：`research`工具可分解问题→并行子查询→抓取源→合成引用报告；`agent`工具支持计划→搜索→抓取→提取→合成的自主收集循环

## 采用成本

- **时间**：5分钟安装（`npx wigolo init --agents=claude-code`）
- **金钱**：核心功能完全免费，可选配免费Gemini Key提升research质量
- **磁盘**：~1.5GB（含浏览器引擎+本地模型）
- **学习曲线**：低——MCP协议即插即用，CLI/shell/REST/SDK多种接入方式

## 采用案例

- **Claude Code + wigolo**：Agent可直接搜索Web、抓取页面、缓存结果，无需额外API
- **自托管Agent + wigolo REST**：n8n/LangChain工作流通过REST端点获取Web能力
- **变更监控**：`watch+diff`工具监控URL变更，自动推送webhook

## 风险/局限

- 仍处于公测阶段，API可能变化
- 无API Key时research功能体验降级（返回原始简报而非合成答案）
- 本地模型质量依赖设备性能
- 1.5GB初始下载对轻量环境有门槛

## 核心线索

- GitHub：https://github.com/KnockOutEZ/wigolo
- 首发来源：GitHub TypeScript Trending
- 发布时间：2025年（公测中）
- 当前状态：公测中 / 活跃开发