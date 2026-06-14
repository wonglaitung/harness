# SkillSpector

## 技术定义 (What)
NVIDIA 发布的 AI Agent 技能安全扫描器，可在安装前检测技能包中的漏洞、恶意模式和安全风险。支持 64 种漏洞模式检测，覆盖提示注入、数据泄露、权限提升、供应链攻击等 16 个类别。

## 行业痛点 (Why)
AI Agent 技能（如 Claude Code、Codex CLI 的 Skills）目前以隐式信任方式执行，研究表明 26.1% 的技能包含漏洞，5.2% 具有恶意意图，但缺乏统一的安全审查工具。

## 旧范式 vs 新范式
- **旧做法**：直接安装使用社区技能包，依赖开发者自觉或人工审查，无自动化安全检测手段。
- **新做法**：在安装前自动扫描技能包，使用静态分析 + LLM 语义评估两阶段检测，生成 0-100 风险评分和详细报告，支持 CI/CD 集成。

## 生产力影响 (How)
将 Agent 技能安全审查从"盲目信任"升级为"可量化评估"，降低供应链攻击风险，为生产环境 Agent 部署提供安全保障。

## 采用成本
Python 3.12+，支持 Docker 部署，免费开源。LLM 分析需 API Key（OpenAI/Anthropic/NVIDIA），纯静态分析可免费使用。

## 核心线索
- GitHub：https://github.com/NVIDIA/SkillSpector
- 来源：https://github.com/NVIDIA/SkillSpector
- 发布时间：2026-06-14
