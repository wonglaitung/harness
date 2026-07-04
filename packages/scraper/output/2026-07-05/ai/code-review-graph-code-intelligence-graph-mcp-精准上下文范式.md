# code-review-graph

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首个将代码结构知识图谱与MCP协议结合的工具，引入"Blast Radius"精准上下文概念，解决AI编码工具的Token浪费问题 |
| 采用广度 | ☆☆☆☆/5 | 自动集成12+主流AI编码平台（Codex、Claude Code、Cursor、Windsurf、Gemini CLI、Copilot等），MCP协议标准化 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年6-7月新发布，GitHub Trending |
| 社区热度 | ☆☆☆/5 | GitHub Trending Python，单日34星，多语言README覆盖 |
| **总体判断** | ✅ | **新范式 — 从"全量上下文"到"精准上下文"的AI编码工具架构升级** |

## 技术定义 (What)
code-review-graph 是一个本地优先的代码智能图谱工具，使用 Tree-sitter 将代码库解析为 AST 知识图谱（函数、类、导入、调用关系、继承、测试覆盖），通过 MCP 协议为 AI 编码助手提供精准上下文。当文件变更时，自动计算"Blast Radius"（影响范围），只返回受影响的文件子集，而非让AI读取整个项目。

## 行业痛点 (Why)
当前AI编码工具（Claude Code、Cursor、Copilot等）在代码审查和大仓库操作时，会重新读取大量无关代码，造成Token浪费和响应延迟。实测显示：传统方式消耗38x-528x的Token，而精准上下文可将Token消耗降至原来的1/50到1/500。

## 旧范式 vs 新范式
- **旧做法**：AI编码工具读取整个项目或大段代码作为上下文，Token消耗巨大，响应慢，且常遗漏关键依赖关系
- **新做法**：通过代码知识图谱 + MCP协议，AI只读取变更文件的"Blast Radius"范围内的代码，Token消耗降低93x，2秒内增量更新

## 生产力影响 (How)
1. **Token成本大幅降低**：从208,821个源码Token降至~2,495个图谱响应Token（93x缩减）
2. **审查质量提升**：AI不再遗漏跨模块的依赖关系和受影响的测试
3. **Monorepo可用性突破**：27,700+文件的大型仓库，只需读取~15个关键文件
4. **增量更新极快**：2,900文件项目增量索引<2秒

## 采用成本
- 免费（MIT协议），`pip install code-review-graph` 即可
- 10秒内构建500文件项目的知识图谱
- 零配置自动检测已安装的AI编码工具并写入MCP配置
- 支持30+编程语言的Tree-sitter解析

## 采用案例
- **Claude Code用户**：通过MCP自动获取精准审查上下文
- **Cursor用户**：安装后自动配置，审查时只读取相关文件
- **Codex用户**：通过MCP + Hooks实现自动增量更新
- **大型Monorepo**：从需要读取全量代码变为只读15个关键文件

## 风险/局限
- 初始构建需解析整个项目，超大仓库可能需要更长时间
- Tree-sitter对部分语言的支持深度不一
- 增量更新依赖文件保存Hook或Watch模式
- 目前社区规模较小，需持续验证稳定性

## 核心线索
- GitHub：https://github.com/tirth8205/code-review-graph
- 首发来源：GitHub Trending Python
- 发布时间：2026年6-7月
- 当前状态：活跃开发中