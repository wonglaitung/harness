# Copperhead — Agent-Native PCB 设计新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首次将"Cursor for X"模式迁移到硬件设计，引入 8 阶段 Gate-Check 流水线 + Agent-Native Hardware Design 概念 |
| 采用广度 | ☆☆☆☆/5 | Show HN #1 248 points，开源 Apache-2.0，已有实际硬件案例（Open Telegraph） |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026-09-12 Show HN 首发，刚发布 |
| 社区热度 | ☆☆☆☆☆/5 | Show HN 248 points，Product Hunt Featured |
| **总体判断** | ✅ | **新范式：Agent 驱动的硬件设计自动化** |

## 技术定义 (What)

Copperhead 是一个开源 AI Agent，专门用于设计、文档化和验证印刷电路板 (PCB)。用户用自然语言描述需求（brief.md），Agent 自动完成 8 个阶段：规格书→架构→BOM 清单→原理图→布局→Gerber 输出→固件→开发计划。每个阶段都有 Gate-Check，不通过则停止。

## 行业痛点 (Why)

硬件设计中，原理图、BOM、功耗预算、文档之间的一致性是噩梦级问题。一旦不一致，在打样阶段才会发现，一次 Re-spin 成本 5000-50000 美元 + 6-8 周延迟。

## 旧范式 vs 新范式
- **旧做法**：硬件工程师手工维护 KiCad 原理图、BOM、文档，版本漂移靠人工检查
- **新做法**：AI Agent 端到端管理 8 阶段流水线，每阶段 Gate-Check，ERC/DRC 自动通过

## 生产力影响 (How)
- 从 Brief 到 Gerber 文件全自动生成
- 编辑是"外科手术式"的（KiCad s-expression 级别修改，diff 小而可审查）
- 拒绝修改任何未经验证的变更提案

## 采用成本
- CLI 免费开源（Apache-2.0），本地运行
- 需要 Node 20+、KiCad、ANTHROPIC_API_KEY
- Cloud 版本 $49/用户/月

## 采用案例
- **Open Telegraph**：ESP32-S3 Morse 键盘，全程通过 Copperhead 设计并已实际生产

## 风险/局限
- 当前仅支持 KiCad（企业版支持 Altium）
- 硬件验证最终仍需物理测试
- 复杂 RF/高速设计可能超出当前能力

## 核心线索
- GitHub：https://github.com/animesh-chouhan/open-telegraph（案例仓库）
- 官网：https://copperhead.sh/
- 首发来源：Show HN 2026-09-12
- 当前状态：活跃开发中