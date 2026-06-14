# SkillSpector

## 技术定义 (What)
首个专门扫描 AI Agent 技能安全漏洞的工具，检测 64 种漏洞模式，包括提示注入、数据泄露、权限提升、供应链攻击等，提供 0-100 风险评分。

## 行业痛点 (Why)
研究显示 26.1% 的 Agent 技能包含漏洞，5.2% 存在恶意意图，但开发者缺乏工具评估技能安全性，导致安全隐患。

## 旧范式 vs 新范式
- **旧做法**：手动审查技能代码，依赖开发者经验判断安全性，无标准化检测流程，容易遗漏隐蔽漏洞。
- **新做法**：自动化静态分析 + LLM 语义评估，支持 16 大类 64 种漏洞模式，实时查询 OSV.dev CVE 数据库，生成 SARIF/JSON/Markdown 报告。

## 生产力影响 (How)
DevOps 团队可在 CI/CD 流程中集成 SkillSpector，自动扫描第三方技能，阻止高风险技能进入生产环境，降低安全风险。

## 采用成本
开源免费，Python 3.12+，支持 Docker 部署，静态分析无需 API Key，LLM 语义分析需配置 OpenAI/Anthropic API。

## 核心线索
- GitHub：https://github.com/NVIDIA/SkillSpector
- 来源：https://github.com/NVIDIA/SkillSpector
- 发布时间：2026-06-14
