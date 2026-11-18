# M3E Canvas — 设计稿即 Prompt 编译器（Prompt-as-Design-Artifact）

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 输出物不是图片、不是代码，而是「结构化 prompt brief」；同名屏幕写成「一屏双宽」；public/agent.md 支持 Agent 反向作图并回传链接 |
| 采用广度 | ☆☆/5 | 新项目，暂无跨项目集成；社区生态指向 matraic/m3e（Lit 组件）、Beer CSS 等 M3 体系 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026-11 首发，Trendshift 当日 #1 repository |
| 社区热度 | ☆☆☆/5 | GitHub Trending TypeScript 当日 103 stars/日、Trendshift 日榜第一、多语 README（英日中韩）与 12+ 贡献者 |
| **总体判断** | ✅ | **新范式（观察中偏确认）** |

满足维度：概念创新 + 时间新鲜 + 社区共鸣（Trendshift #1 / 多语社区扩张）。

## 技术定义 (What)

纯浏览器端的 App 屏幕草稿板，组件是真实的 Material 3 Expressive 部件（按钮、FAB 菜单、导航栏/轨、卡片、底部 sheet、日期选择器、shape-morphing loading 等）。三步工作流：**Sketch**（拖拽 + 4dp 网格吸附 + 磁性融合成连通组）→ **Tap through**（连线成可点击流程，带转场，Preview 可走通并可反向 back）→ **Copy the prompt**（整份设计编译成简短 brief）。若屏幕同名，prompt 中写作「同一屏幕的两个宽度」，导航栏自动变导航轨。设计层输出 PNG；也支持导出分享链接，或给编码 Agent 一条指令，让它读 `agent.md` 自行作图并回传链接。

## 行业痛点 (Why)

设计工具与编码 Agent 之间存在「意图损耗」：Figma 稿到可运行代码，中间靠人手写 prompt，颜色、间距、响应式断点、点击跳转关系全部在自然语言中蒸发。Agent 生成的 UI 常常结构对、布局错，人工逐像素返工使 Agent 提效被打回原形。

## 旧范式 vs 新范式

- **旧做法**：设计工具输出视觉稿（图片/矢量），人或 MCP 服务器再翻译成 prompt/代码；prompt 是手写的自由文本，无结构、不可校验。
- **新做法**：设计工具的输出物就是 prompt——引用真实组件标识、显式拼写行/重叠/对齐网格、编码交互目标屏与转场类型、编码响应式双宽映射。设计记录（Design-of-Record）随 prompt 一起进入编码 Agent。

## 生产力影响 (How)

- 消除「设计→prompt」的人工翻译环节，把原型与实现压进同一步骤。
- 布局约束被无损传递，显著降低 Agent 生成 UI 后的返工率。
- 对独立开发者：5 分钟得到可点击原型 + 一份可直接喂给 Claude Code / Codex / Cursor 的规格。
- 双向回环：Agent 可读 `agent.md` 反向生成设计并回传分享链接，适合让 Agent 做多方案比稿。

## 采用成本

- 金钱：0（MIT，静态托管，无后端）。
- 时间：拖拽上手约 15 分钟；AI 辅助为可选自带 key。
- 门槛：绑定 Material 3 Expressive 设计语言；非 M3 品牌需自行映射到自有设计系统（其姊妹方向可参考 DESIGN.md / Stitch Skills 等「设计系统即文件」路线）。
- 局限：桌面浏览器才有完整编辑器（手机端为简化按钮版）；生成质量依赖下游 Agent 对 M3 词汇的理解。

## 采用案例

- **独立开发者快速原型**：拖出 Pantry 菜谱 App 三屏 → 复制 prompt → 终端里 Claude Code 直接产出可运行 App（官方 demo 演示此流程）。
- **Agent 比稿**：给 Agent 一条分享指令，让其为同一需求画 3 个方案并回传链接，人工只做选择。
- **设计系统对齐**：与 matraic/m3e（Lit Web Components）、Beer CSS 配合，把草图直接落到既有 M3 组件库。

## 风险/局限

- 单一设计语言绑定，泛化到 Tailwind/shadcn 等体系需额外映射层。
- 「prompt 即产物」的可复现性依赖下游模型版本；prompt 缺少版本化与回归测试机制（对比 DESIGN.md、Stitch Skills 等正在补的这块）。
- 新项目，一人主导风险与长期维护不确定（但已有 12+ 贡献者，社区化迹象良好）。

## 核心线索

- GitHub：https://github.com/lnkiai/m3e-canvas
- 在线版：https://lnkiai.github.io/m3e-canvas/
- 首发来源：GitHub Trending TypeScript（daily）/ Trendshift 日榜 #1
- 发布时间：2026-11（首发 < 1 月）
- 当前状态：活跃（多语 README、sponsors、持续提交）
- 相邻信号：DESIGN.md（设计系统即代码规范）、Stitch Skills（设计⇄代码双向回环）、Plannotator（人工-Agent 决策回环）——「设计记录」这一层正在被多个独立项目同时补齐。
