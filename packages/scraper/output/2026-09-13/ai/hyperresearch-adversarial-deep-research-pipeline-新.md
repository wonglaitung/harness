# Hyperresearch — Adversarial Deep Research Pipeline

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 16 步对抗性研究流水线：分解→宽度搜索→矛盾图谱→深度调查→三稿并行→4 路对抗评审→引文验证→修复。首次将学术研究流程完整编码为 Agent 可执行流水线 |
| 采用广度 | ☆☆/5 | 首发阶段，依赖 Claude Code |
| 时间新鲜 | ☆☆☆☆☆/5 | GitHub trending 712⭐/天（2026-09-13），Fresh |
| 社区热度 | ☆☆☆☆/5 | GitHub 712 stars/day，PyPI 可安装 |
| **总体判断** | ✅ | **新范式** |

## 技术定义 (What)

Hyperresearch 将 Claude Code 转变为深度研究 Agent，通过 16 步分层流水线将一个 prompt 转化为经过对抗性审计、带完整溯源的研究报告。核心创新包括：4 路对抗批评并行、引文逐句验证、独立性审计（区分转载与独立来源）、8 种学术源统一搜索。

## 行业痛点 (Why)

现有的 AI 深度研究工具（如 OpenAI Deep Research、Gemini Deep Research）仍存在幻觉引用、无法区分转载与独立来源、无法处理付费论文全文等问题。传统做法依赖人工交叉验证。

## 旧范式 vs 新范式
- **旧做法**：AI 一次生成研究报告 → 人工检查引用 → 发现幻觉后重新生成
- **新做法**：16 步流水线自动完成：宽度搜索(100-250源) → 矛盾识别 → 4 路对抗批评 → 逐句引文验证 → 手术级修复 → 可读性审计

## 生产力影响 (How)
- 从"AI 生成+人工验证"到"AI 生成+AI 对抗验证"，将深度研究报告的可信度提升一个量级
- 250+来源/次，支持断点续传（crash recovery）
- 支持论文级（300-450 源，25K-80K 字）深度研究

## 采用成本
- 安装：pip install hyperresearch
- 需要：Claude Code 环境 + API token
- 时间：轻量 30-40 分钟，完整 1.5-2.5 小时，论文级 4-8 小时

## 采用案例
- 自称在 DeepResearch-Bench RACE 排行榜上领先（内部评估，第三方验证待完成）

## 风险/局限
- 依赖 Claude Code 生态（非独立应用）
- 内部 benchmark 自称领先，缺第三方独立验证
- Python 3.14 尚不支持

## 核心线索
- GitHub：https://github.com/jordan-gibbs/hyperresearch
- PyPI：hyperresearch
- 发布时间：2026-09 ~ 近期
- 当前状态：活跃开发中