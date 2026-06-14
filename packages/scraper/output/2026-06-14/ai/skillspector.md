# SkillSpector

## 技术定义 (What)
NVIDIA 推出的 AI Agent 技能安全扫描器，能在安装 agent 技能前检测漏洞、恶意模式和安全风险。研究表明 26.1% 的技能包含漏洞，5.2% 存在恶意意图。

## 行业痛点 (Why)
AI Agent 技能（Claude Code、Codex CLI、Gemini CLI 等）以隐式信任方式执行，缺乏安全审查。现有安全工具无法检测提示注入、数据泄露、权限提升等 Agent 特有的攻击向量。

## 旧范式 vs 新范式
- **旧做法**：手动审查技能代码，或直接信任安装，缺乏自动化安全检测。CVE 数据库不覆盖 Agent 特有的漏洞模式。
- **新做法**：静态分析 + LLM 语义评估的两阶段扫描，覆盖 16 大类 64 种漏洞模式（提示注入、数据泄露、权限提升、供应链攻击、过度代理等），支持实时 CVE 查询（OSV.dev），生成 SARIF 报告集成 CI/CD。

## 生产力影响 (How)
开发者可在安装技能前快速评估风险，CI/CD 流水线自动拦截高风险技能。支持 JSON/Markdown/SARIF 输出，与现有安全工作流无缝集成。

## 采用成本
Python 3.12+，支持 Docker 部署无需本地 Python。基础静态分析无需 API Key，LLM 语义分析需 OpenAI/Anthropic API。学习成本低，5 分钟上手。

## 核心线索
- GitHub：https://github.com/NVIDIA/SkillSpector
- 来源：https://github.com/NVIDIA/SkillSpector
- 发布时间：2026-06-14
