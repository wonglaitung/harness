# Scientific Agent Skills — Agent Skills 标准的领域规模化

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ⭐⭐⭐⭐/5 | 不是发明 Agent Skills 标准本身，而是**证明该标准在大规模垂直领域的可行性**——163 个可复用技能 + 100+ 科学数据库 |
| 采用广度 | ⭐⭐⭐⭐⭐/5 | 190,000+ 科学家使用，兼容 Cursor/Claude Code/Codex/Antigravity/Pi |
| 时间新鲜 | ⭐⭐⭐⭐/5 | 持续迭代至 v2.65.0，从 Claude Scientific Skills 演进为开放标准兼容 |
| 社区热度 | ⭐⭐⭐⭐⭐/5 | GitHub 日增 1980 stars，多平台集成，配套桌面应用 K-Dense BYOK |
| **总体判断** | ✅ **新范式** | Agent Skills 标准的**旗舰级验证案例**，以领域深度证明标准可行性 |

## 技术定义 (What)

一个包含 **163 个即用科学技能** + **100+ 科学数据库**的开放仓库，遵循 [Agent Skills](https://agentskills.io/) 标准。它将任何 AI Agent 转变为覆盖生物/化学/医学/药物发现等领域的科学助手。每个 `SKILL.md` 文件包含 Agent 可自举的指令、Python 依赖和 API 使用方法，Agent 按需加载技能。

## 行业痛点 (Why)

科学领域的 AI 应用面临"知识碎片化"：数百个专业数据库（NCBI、PDB、PubChem...）各有自己的 API 和数据结构。科学家需要大量手工集成工作才能让 AI 访问这些资源。传统方案是逐一编写 Python 脚本调用每个数据库。

## 旧范式 vs 新范式

- **旧做法**：科学家手动搜索每个数据库 → 复制粘贴给 LLM → 手工整合结果 → 验证
- **新做法**：Agent 读取 `SKILL.md` 自举 → 理解数据库 schema → 自动编排多步科学工作流 → 返回分析报告

## 生产力影响 (How)

- **知识民主化**：非编程科学家通过自然语言驱动 AI 访问 100+ 专业数据库
- **工作流自动化**：从"序列比对 → 结构预测 → 分子对接 → 报告"全自动
- **可组合性**：技能可链式组合（如：基因组查询技能 + 统计技能 + 可视化技能）

## 采用成本

零成本开源。需 Agent 支持 Agent Skills 标准（Cursor/Claude Code/Codex 原生支持）。K-Dense BYOK 桌面应用提供开箱即用体验。

## 采用案例

- **K-Dense BYOK**：开源桌面 AI 协同科学家，本地运行
- **190,000+ 科学家**：在 Cursor/Claude Code 中直接使用这些技能进行科研
- **覆盖领域**：癌症基因组学、单细胞 RNA-seq、PK/PD 建模、分子动力学、药物发现等 15+ 领域

## 风险/局限

- 依赖 Agent Skills 标准的持续演进（但已是开放标准）
- 科学技能的质量需持续验证和更新
- 部分数据库需订阅/API key

## 核心线索

- GitHub：https://github.com/K-Dense-AI/scientific-agent-skills
- 标准：https://agentskills.io/
- 首发时间：从 Claude Scientific Skills 演进而来，持续迭代
- 当前状态：活跃开发中（v2.65.0）