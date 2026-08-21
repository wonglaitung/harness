# Anthropic Cybersecurity Skills — 领域结构化技能库

## 技术定义 (What)
817 个生产级网络安全技能，按 agentskills.io 标准结构化，映射 6 大框架（MITRE ATT&CK v19.1、NIST CSF 2.0、MITRE ATLAS、D3FEND、NIST AI RMF、MITRE F3），覆盖 29 个安全领域，兼容 26+ AI 编码平台。本质是"领域知识即 Agent 能力"的规模化实践。

## 行业痛点 (Why)
AI Agent 做安全工作时的"知识鸿沟"：知道用哪个工具但不知道如何系统化调查。初级分析师熟悉 Volatility3、Sigma 规则、跨云取证流程——但 AI Agent 没有这些结构化知识。传统方法是每次在 prompt 里临时描述，不可复用、不可组合。

## 旧范式 vs 新范式
- **旧做法**：安全知识嵌在 prompt 中，每次交互临时描述；或依赖模型训练时记住的安全知识，无法迭代更新
- **新做法**：领域知识编译为标准化 Agent Skills（agentskills.io），以文件系统级别组织，Agent 按需加载。技能可版本控制、可组合、可跨平台复用。映射到行业框架实现合规对齐和覆盖度审计。

## 生产力影响 (How)
安全团队可一键让任何 AI Agent 获得资深分析师级的安全技能。技能即代码（Skills-as-Code），可进入 CI/CD、安全编排流程。框架映射让合规审计（NIST CSF 覆盖度）自动化。

## 采用成本
零成本：git clone 即可用，Apache 2.0 许可。学习曲线低：遵循 agentskills.io 标准，任何支持该标准的平台均可直接使用

## 核心线索
- GitHub：https://github.com/mukul975/Anthropic-Cybersecurity-Skills
- 来源：https://github.com/mukul975/Anthropic-Cybersecurity-Skills
- 发布时间：2026-08-22
