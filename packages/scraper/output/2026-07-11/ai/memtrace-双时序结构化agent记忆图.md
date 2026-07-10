# Memtrace — 双时序结构化Agent记忆图

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首个"双时序结构化知识图"：将代码AST解析为函数/类/调用边图谱，叠加时间维度实现版本回溯，零LLM调用构建 |
| 采用广度 | ☆☆☆/5 | MCP-native 25+工具；兼容Cursor/Claude Code/Codex/Hermes/VS Code/Windsurf；20+编程语言 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年Private Beta，首发<3个月 |
| 社区热度 | ☆☆☆/5 | GitHub trending 25 stars/day；基准测试全面领先Mem0/Graphiti/GitNexus |
| **总体判断** | ✅ | **新范式 — Agent记忆从"对话实体追踪"到"结构化代码时序图"** |

## 技术定义 (What)
Memtrace是一个面向AI编码Agent的结构化记忆系统。它用Rust+Tree-sitter将代码库解析为知识图谱（函数、类、调用边、继承关系），并叠加双时序维度（bi-temporal），使Agent能查询任意符号的完整版本历史和影响范围。核心创新：零LLM调用、1.5秒索引1500文件、MCP原生暴露25+工具。

## 行业痛点 (Why)
当前AI编码Agent面临三大记忆问题：
1. **盲区重构**：Agent修改函数后不知道14个下游测试会崩，因为看不到调用图
2. **会话失忆**：每次新会话重新读文件，无法继承上次的结构理解
3. **LLM记忆成本**：Mem0/Graphiti用LLM推理构建图谱，1500文件需1-2小时+$10-50 API费用

## 旧范式 vs 新范式
- **旧做法**：Mem0/Graphiti用LLM提取实体关系，对话级记忆，$10-50/代码库，31分钟索引
- **新做法**：Tree-sitter AST确定性解析，代码级结构图+双时序，$0成本，1.5秒索引

## 生产力影响 (How)
- **消除盲区重构**：Agent修改前自动查询blast radius，避免破坏性变更
- **跨会话记忆**：Agent舰队共享同一知识图谱，无需重复索引
- **时间旅行查询**：6种评分算法（影响/新颖/近因/方向/复合/概览）支持不同时间维度问题
- **跨仓库API拓扑**：自动映射HTTP调用图，检测服务间依赖

## 采用成本
- **时间**：90秒完成50k文件索引
- **金钱**：$0（零LLM调用，纯本地AST解析）
- **学习曲线**：MCP原生，Agent自动发现工具；CLI `npm install -g memtrace`
- **限制**：当前Private Beta，需申请waitlist；专有EULA许可

## 采用案例
- **Cursor/Claude Code集成**：通过MCP自动获取代码结构上下文
- **代码审查**：PR代码审查F1达0.7268，比Cubic v2高19.6%
- **符号查询**：精确符号查询准确率96.6%，延迟0.07ms（比GitNexus快128倍）

## 风险/局限
- Private Beta阶段，尚未GA
- 专有EULA许可，非完全开源
- 仅面向代码智能，不支持对话实体记忆（与Mem0/Graphiti互补而非替代）
- RSS仅26MB，但大型monorepo索引性能待验证

## 核心线索
- GitHub：https://github.com/syncable-dev/memtrace-public
- 官网：https://memtrace.io
- 首发来源：GitHub Trending (TypeScript)
- 发布时间：2026年（Private Beta）
- 当前状态：Private Beta / 活跃开发