# Claude Tag

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首个"多人协作Agent"产品范式——一个Agent在频道中与多人交互，共享上下文，主动行动 |
| 采用广度 | ☆☆☆/5 | Anthropic内部65%产品代码由Claude Tag生成，Enterprise/Team客户可用 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年6月23日发布 |
| 社区热度 | ☆☆☆/5 | HN 219分，Anthropic官方重磅发布 |
| **总体判断** | ✅ | **新范式——多人协作Agent** |

## 技术定义 (What)
Claude Tag是一种将AI Agent嵌入团队协作工具（首发Slack）的新范式。一个Claude实例作为频道成员存在，所有团队成员通过@Claude标记来委派任务，Claude在频道中积累上下文、主动提醒、异步执行，像一个真正的队友。

## 行业痛点 (Why)
当前AI助手是"单人对单Agent"模式——每个人独立与AI对话，上下文不共享，协作断裂。团队工作中，AI无法看到全局、无法跨人协作、无法主动跟进。

## 旧范式 vs 新范式
- **旧做法**：单人Chat模式，每人独立与AI对话，上下文隔离，Agent是被动的
- **新做法**：多人@Agent模式，一个Agent在频道中与所有人协作，共享记忆，主动行动，异步执行

## 生产力影响 (How)
- 团队级AI协作：多人可接力同一个Agent的任务
- 上下文积累：Agent从频道历史中学习，无需重复解释
- 主动行动：Agent可主动提醒、跟进未完成任务
- 异步执行：设置任务后Agent自主工作数小时/天
- Anthropic内部数据：65%产品代码由Claude Tag生成

## 采用成本
- Claude Enterprise/Team订阅
- Slack工作区配置
- 管理员设置权限和工具访问
- 学习成本极低——只需@Claude即可

## 采用案例
- Anthropic产品团队：65%代码由Claude Tag生成
- 工程团队：追踪产品指标和数据
- 支持团队：处理支持工单
- 调试：帮助找到复杂Bug根因

## 风险/局限
- 目前仅支持Slack平台
- 仅Enterprise/Team客户可用
- Agent身份按频道隔离，跨频道记忆需授权
- Token消耗可能较高（多人持续交互）

## 核心线索
- 首发来源：https://www.anthropic.com/news/introducing-claude-tag
- 发布时间：2026-06-23
- 当前状态：Beta（Enterprise/Team）
- 底层模型：Opus 4.8