# Paperclip — Agent 公司编排新范式

## 新范式评分
| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | "Agent 是员工、系统是公司"的组织抽象 + 四支柱 + org chart（"能收心跳就被录用"） |
| 采用广度 | ☆☆☆/5 | 跨 provider 集成（OpenClaw/Claude/Codex/Cursor/Bash/HTTP） |
| 时间新鲜 | ☆☆☆☆/5 | 新发布，YC W26 背景，MIT 开源 |
| 社区热度 | ☆☆☆☆☆/5 | GitHub 今日 +2608 stars，trending 榜首 |
| **总体判断** | ✅ | **新范式** |

## 技术定义 (What)
Paperclip 是"管理 AI Agent 的 App"，把多 Agent 团队编排成公司结构：org chart（角色/权限/边界）、goal alignment（每个任务追溯公司使命）、heartbeats（心跳调度）、budget（月度预算节流）、ticket system（全程审计）。四支柱 = 任务管理器 + 组织架构 + 员工培训 + Agentic OS。

## 行业痛点 (Why)
多 Agent 并行时，开发者无法追踪进度、重启丢状态、手动拼上下文、失控循环烧 token。缺少面向"Agent 组织"的治理与协调基础设施。

## 旧范式 vs 新范式
- **旧做法**：手动开多个 Agent 终端，文件夹堆配置，重复造协调轮子，无预算治理
- **新做法**：以"公司"抽象统一编排，org chart + 心跳 + 预算 + 审计，运营公司而非维护脚本

## 生产力影响 (How)
统一 dashboard 管理任意 provider 的 Agent，原子任务认领+预算强制杜绝双工与失控开销，持久化会话，手机远程治理——为自主 AI 组织规模化提供底座。

## 采用成本
中等：自部署 Node.js+React，需理解 org chart/heartbeat/budget 模型；但无 vendor lock-in。

## 采用案例
- 自主 AI 组织/公司运营
- 协调 20+ Claude Code 终端的团队场景
- 24/7 自主运行的客服/社媒/报告等循环任务

## 风险/局限
- 需自托管基础设施，运维成本
- 概念较新，org chart 治理模型的实际效果待验证
- 多 Agent 协调本身的可靠性仍是行业难点

## 核心线索
- GitHub：https://github.com/paperclipai/paperclip
- 首发来源：GitHub trending（今日 +2608 stars）
- 发布时间：2026-09
- 当前状态：活跃试验中