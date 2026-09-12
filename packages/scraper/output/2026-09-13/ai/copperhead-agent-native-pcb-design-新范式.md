# Copperhead — Agent-Native PCB Design

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首次将完整 PCB 设计流程（规格→架构→BOM→原理图→布局→Gerber→固件→开发计划）编码为 8 阶段 Agent 流水线，每阶段有 Gate 门禁 |
| 采用广度 | ☆☆/5 | 首发阶段，基于 KiCad 生态，已产出真实硬件（Open Telegraph） |
| 时间新鲜 | ☆☆☆☆☆/5 | Show HN 249 pts（2026-09 初），GitHub 活跃开发中 |
| 社区热度 | ☆☆☆☆/5 | Show HN 249 points，Hacker News 首页 |
| **总体判断** | ✅ | **新范式** |

## 技术定义 (What)

Copperhead 是一个 AI Agent，通过 8 个阶段流水线设计、验证和记录印刷电路板（PCB）。每个阶段对应一个 Agent run：
1. **spec** — 产品规格文档
2. **architecture** — 子系统架构
3. **parts** — 物料清单（BOM，从数据表验证零件号）
4. **schematic** — KiCad 原理图（ERC 清洁）
5. **layout** — PCB 布局（DRC 清洁）
6. **outputs** — Gerber/钻孔/STEP 文件
7. **firmware** — 固件代码 + pinout
8. **dev plan** — 生产测试计划

每阶段必须把工件写入磁盘才能进入下一阶段，Gate 不通过则停止。

## 行业痛点 (Why)

PCB 设计中存在「漂移」问题：一个硬件设计决策分散在原理图、BOM、功耗预算和多份文档中，当它们失同步时不会报警。不一致性往往在 bring-up 阶段才被发现，一次重新打样花费 5,000-50,000 美元和 6-8 周时间。

## 旧范式 vs 新范式

- **旧做法**：人类工程师手动维护设计，文档与原理图常常脱节，评审靠人工检查一致性
- **新做法**：Agent 驱动全流程，每个阶段都是验证门禁，设计变更自动传播到所有文档，ERC/DRC 由 KiCad 原生验证

## 生产力影响 (How)

- 消除文档与硬件的漂移问题
- 每次变更可见 git diff，支持团队审查
-「不会凭空捏造不在数据表中的零件号」—— 设计约束被编码为 Gate

## 采用成本

CLI 免费开源，Cloud 版 $49/用户/月，支持私有仓库和 Web 查看器

## 采用案例

- **Open Telegraph**：ESP32-S3 口袋莫尔斯电键，从 brief 到成品全流程使用 Copperhead 构建，完整案例公开

## 风险/局限

- 当前仅支持 KiCad（Altium 支持在路线图中）
- 依赖 LLM API（Claude/GPT-5），需要 API Key
- PCB 设计是安全关键领域，Agent 仍需人工审查

## 核心线索

- GitHub：https://github.com/animesh-chouhan/open-telegraph
- 官网：https://copperhead.sh/
- 首发来源：Show HN（2026-09）
- 发布时间：2026-09 初
- 当前状态：活跃开发中