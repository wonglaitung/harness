# Ouroboros

## 技术定义 (What)
Ouroboros 是一个 Agent OS（Agent 操作系统），将非确定性的 AI 编码转变为可重放、可观测、受策略约束的执行契约。核心创新：**Socratic Interview**（苏格拉底式访谈暴露隐藏假设）、**Immutable Seed Spec**（不可变规格说明书）、**3-Stage Evaluation Gate**（三级评估门控）。从模糊想法到验证通过的可工作代码库，无需反复 prompt。

## 行业痛点 (Why)
AI 编码失败常因输入不清晰：1) Vague prompts 导致 AI 猜测；2) 缺乏规格说明书，架构中途漂移；3) 手动 QA "看起来不错" 不是验证。大多数 AI 编码工具解决输出问题，但真正瓶颈是人类输入的清晰度。

## 旧范式 vs 新范式
- **旧做法**：直接 prompt："Build me a task CLI" → AI 猜测需求 → 输出代码 → 人工审查 → 发现问题 → 重新 prompt → 循环。需求模糊导致反复迭代，浪费时间和 token。
- **新做法**：Specification-first 工作流：`ooo interview` 苏格拉底式提问暴露隐藏假设 → `ooo seed` 生成不可变规格（模糊度评分降至 0.15）→ `ooo run` 执行（Double Diamond 分解）→ `ooo evaluate` 三级验证（Mechanical → Semantic → Consensus）。每次循环 Agent 学到更多。

## 生产力影响 (How)
将"反复 prompt"转变为"一次性成功"。减少因需求不清导致的返工。适用于复杂项目：从模糊想法到可工作代码库，全程可审计、可重放。支持 Claude Code、Codex CLI、Gemini、Copilot 等多种运行时。

## 采用成本
**时间成本**：一条命令安装（curl 脚本）。学习概念：Interview → Seed → Run → Evaluate。**金钱成本**：开源免费（MIT）。**依赖成本**：需要 Python 3.12+。支持多种 LLM 后端（Claude、OpenAI、Gemini、LiteLLM）。

## 核心线索
- GitHub：https://github.com/Q00/ouroboros
- 来源：https://github.com/trending/python
- 发布时间：2026-06-23
