# OpenSpec — Spec-Driven Development (SDD)

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首次系统化定义"Spec-Driven Development"概念，提出 artifact-guided 工作流（explore → propose → apply → archive） |
| 采用广度 | ☆☆/5 | 支持 25+ AI 编码工具（Claude Code、Codex、Cursor 等），但尚处早期采用阶段 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年6月首次公开发布 |
| 社区热度 | ☆☆☆/5 | GitHub Trending 首日 167 stars，npm 包已发布 |
| **总体判断** | ✅ | **新范式** |

## 技术定义 (What)
OpenSpec 是一种面向 AI 编码助手的规格驱动开发（Spec-Driven Development, SDD）框架。核心理念：在 AI 写代码之前，先让人类和 AI 对齐"要建什么"。每个功能变更都有独立的文件夹，包含 proposal.md（为什么做）、specs/（需求和场景）、design.md（技术方案）、tasks.md（实施清单），通过斜杠命令（/opsx:propose、/opsx:apply 等）驱动 AI 按规格执行。

## 行业痛点 (Why)
AI 编码助手（Claude Code、Codex 等）能力强大但不可预测——需求只存在于聊天历史中，导致模糊提示和不可控输出。缺乏结构化的规格层，AI 容易偏离意图、遗漏边界条件、产生不一致的实现。

## 旧范式 vs 新范式
- **旧做法**：在聊天中用自然语言描述需求，AI 即时生成代码，需求散落在对话历史中，无法追溯和审计
- **新做法**：先通过 /opsx:explore 探索方案，再用 /opsx:propose 生成结构化规格（proposal + specs + design + tasks），人类确认后 /opsx:apply 执行，/opsx:archive 归档。规格即文档，可追溯、可迭代

## 生产力影响 (How)
1. **减少返工**：先对齐再编码，避免 AI 产出与预期不符
2. **可追溯性**：每个变更都有完整的规格记录，团队协作时上下文不丢失
3. **迭代友好**：规格可随时修改，无刚性阶段门控
4. **工具无关**：支持 25+ AI 编码工具，不锁定特定 IDE 或模型

## 采用成本
- **时间**：初始化约 5 分钟（openspec init），每个功能需额外 2-5 分钟写规格
- **金钱**：开源免费（MIT 协议）
- **学习曲线**：低——斜杠命令直觉式，但需养成"先规格后编码"的习惯

## 采用案例
- **个人项目**：/opsx:explore → /opsx:propose 快速迭代
- **团队协作**：规格文件夹可提交到 Git，团队成员共享上下文
- **棕地项目**：支持在已有代码库中增量采用

## 风险/局限
- 规格层增加前期开销，简单任务可能过度工程化
- 依赖高质量 AI 模型（推荐 Codex 5.5 / Opus 4.7），低能力模型可能生成低质量规格
- 尚处早期，社区生态和最佳实践待成熟

## 核心线索
- GitHub：https://github.com/Fission-AI/OpenSpec
- npm：@fission-ai/openspec
- 首发来源：GitHub Trending (TypeScript)
- 发布时间：2026年6月
- 当前状态：活跃（早期快速迭代中）