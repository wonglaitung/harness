# Orca — Agent Development Environment (ADE) 新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首个"Agent 开发环境"概念，定义了 ADE (Agent Development Environment) 新类别 |
| 采用广度 | ☆☆☆☆/5 | 支持 Claude Code、Codex、Cursor、Gemini CLI 等 8+ 主流 Agent |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年中发布，GitHub 日增 703 stars |
| 社区热度 | ☆☆☆☆/5 | GitHub Trending TypeScript 第一，日下载量高 |
| **总体判断** | ✅ 新范式 | Agent 时代的 IDE，从单 Agent 走向并行 Agent 编排 |

## 技术定义 (What)

Orca 是首个 Agent Development Environment（ADE）——一个专为 AI 编码 Agent 设计的桌面 + 移动端工作环境。它让开发者同时运行多个编码 Agent（Claude Code、Codex、OpenCode 等），每个 Agent 在独立的 git worktree 中工作，所有活动在一个界面中统一追踪和比较。核心创新是"并行 worktree 编排"：一个 prompt 可以扇出给 5 个 Agent 同时执行，比较结果后合并最优方案。

## 行业痛点 (Why)

当前 AI 编码 Agent 的使用模式是"一人一 Agent 一终端"：
1. **Agent 间无法并行**：跑完一个才能跑下一个，等待时间长
2. **上下文无法共享**：每个 Agent 从零开始，不知道其他 Agent 做了什么
3. **结果无法比较**：多个方案的 diff 需要手动切窗口对比
4. **移动端断联**：离开电脑后无法监控 Agent 进度

## 旧范式 vs 新范式

- **旧做法**：开多个终端窗口，每个跑一个 Agent，手动切窗口查看结果，手动 merge 代码
- **新做法**：一个 Orca 界面并行运行多个 Agent，每个在独立 worktree 中，自动追踪 diff，一键比较和合并，手机端实时监控

## 生产力影响 (How)

1. **并行化加速**：一个任务分发给 N 个 Agent 同时执行，开发速度线性提升
2. **质量择优**：同一任务产生多个方案，比较后选最优
3. **移动可控**：手机端实时收到 Agent 完成通知，随时发送后续指令
4. **Review 内置**：直接在 diff 行上标注注释，反馈给 Agent 修改，无需切换工具

## 采用成本

- **时间**：10 分钟安装配置，学习曲线平缓（类似 VS Code 体验）
- **金钱**：免费开源，Agent 订阅费用需自行承担
- **学习曲线**：对已使用 Claude Code / Codex 的开发者几乎为零门槛

## 采用案例

- **Parallel Worktree**：一个 bug 修复 prompt 同时发给 Claude Code 和 Codex，比较两个修复方案
- **Mobile Companion**：下班后手机监控 Agent 编译结果，远程发送新任务
- **SSH Worktree**：在远程服务器上跑资源密集型 Agent，本地 Orca 监控
- **Design Mode**：点击页面元素，将 HTML/CSS 和截图直接注入 Agent prompt

## 风险/局限

- **Agent 订阅成本叠加**：并行运行 N 个 Agent 意味着 N 倍 API 调用费用
- **Git worktree 冲突**：多个 Agent 修改同一文件时需手动解决冲突
- **桌面端限制**：目前仅支持桌面 + 移动端，无 Web 版本
- **Agent 兼容性**：依赖 CLI Agent 的终端接口，GUI-only Agent 不支持

## 核心线索

- GitHub：https://github.com/stablyai/orca
- 首发来源：GitHub Trending TypeScript
- 发布时间：2026年中期
- 当前状态：活跃开发（每日发布）