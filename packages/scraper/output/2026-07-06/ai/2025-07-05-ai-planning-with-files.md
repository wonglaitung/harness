# Planning-with-Files

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首次系统定义"持久化文件规划"概念：用磁盘Markdown文件(task_plan.md/findings.md/progress.md)替代上下文窗口维持Agent状态 |
| 采用广度 | ☆☆☆☆/5 | 5+社区fork扩展(devis/multi-manus-planning/plan-cascade等)，4+独立项目直接采用(ClaudeFinance/Copilot Agent等)，31K+技能注册表收录 |
| 时间新鲜 | ☆☆☆☆☆/5 | v3.2.0当前版本，24小时内爆发，持续活跃开发 |
| 社区热度 | ☆☆☆☆/5 | GitHub Trending Python #1当日，61+ stars/day，186个测试用例通过，SkillCheck验证 |
| **总体判断** | ✅ | **新范式 — Agent持久化规划标准** |

## 技术定义 (What)
一种让AI编码Agent通过磁盘上的Markdown文件（task_plan.md、findings.md、progress.md）维持规划状态的方法论和工具。Agent在每次工具调用时自动重新注入计划上下文，使得即使发生上下文丢失、/clear或崩溃，Agent仍能从磁盘恢复并继续执行。v3.0引入了自主模式和完成门控（completion gate），确保Agent不会在计划未完成时提前终止。

## 行业痛点 (Why)
AI编码Agent在长任务中面临三大问题：(1) 上下文窗口溢出导致遗忘早期规划；(2) /clear命令或崩溃后丢失所有进度；(3) 多Agent协作时无法共享任务状态。现有Agent依赖上下文窗口内记忆，无法跨会话持久化。

## 旧范式 vs 新范式
- **旧做法**：Agent将所有规划信息存储在上下文窗口中，一旦上下文溢出或会话重置，规划信息全部丢失。多Agent无法共享状态。
- **新做法**：将规划状态持久化到磁盘Markdown文件，Agent每次工具调用时自动从磁盘重新注入计划。支持完成门控（Agent在计划完成前不会被停止）、跨Agent共享状态、崩溃恢复。

## 生产力影响 (How)
- 长任务（>1小时）的完成率显著提升，基准测试96.7%通过率
- A/B盲测3/3胜出，证明持久化规划优于非持久化方案
- 支持60+种Agent（Claude Code、Codex、Cursor等）通过SKILL.md标准一键安装
- 多Agent团队可共享同一磁盘规划文件实现协作

## 采用成本
- 学习成本：极低。一条命令安装（npx skills add），零配置
- 迁移成本：无。现有项目无需修改，只需添加SKILL.md
- 运行成本：无额外API费用，仅使用磁盘存储

## 采用案例
- **devis (st01cs)**：面试优先工作流，先访谈再实现
- **multi-manus-planning (kmichels)**：多项目支持+Git同步
- **plan-cascade (Taoidle)**：多层级任务编排+并行执行+多Agent协作
- **ClarityFinance (cooragent)**：AI金融Agent框架，直接引用planning-with-files方法

## 风险/局限
- Markdown文件格式依赖Agent正确解析，格式错误可能导致状态丢失
- 完成门控可能阻止Agent在合理时机停止（需谨慎配置自主模式）
- 当前主要验证在Claude Code/Sonnet-4上，其他模型兼容性待验证
- 文件锁机制在多Agent并发写入场景下可能冲突

## 核心线索
- GitHub：https://github.com/OthmanAdi/planning-with-files
- 首发来源：GitHub Trending Python
- 发布时间：2025年6月（v1），当前v3.2.0
- 当前状态：活跃开发中
