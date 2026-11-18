# turbo-browser-mcp — 调用经济 + 提交守卫

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆/5 | 两个可命名的新设计：**Tool-Call Economy**（工具粒度 = 用户意图批次，而非原子动作）与 **Submit Guard**（不可逆动词的多语言默认拦截）；配合 `onlyChanged` 增量快照，构成"少调用 + 少回放 + 有边界"的完整主张 |
| 采用广度 | ☆/5 | 已发 npm 包，但暂无第三方项目引用/集成 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026-11 新发布，Show HN 首发，远在 6 个月内 |
| 社区热度 | ☆☆/5 | Show HN 49 分，略低于 50 分门槛 |
| **总体判断** | ⚠️ | **观察中（概念有真创新，但与既有 browser MCP 生态差异需时间验证）** |

## 技术定义 (What)

基于 Playwright 的 MCP 浏览器服务，11 个工具，核心是把"原子动作"聚合成"意图批次"：

| 工具 | 关键设计 |
|---|---|
| `smart_fill_form` | 一次调用填完整张表单：文本/range/复选/单选/select/ARIA combobox/contenteditable/Gmail 撰写/文件上传（路径直传 Playwright，**内容不进模型上下文**） |
| `inspect_compact` | `onlyChanged: true` 只返回增量，`*` 标新增 ref、`Removed:` 列消失 ref；`maxChars` 截断 + `savePath` 落盘 |
| `batch_actions` | 点击/按键/表单/多页 `navigate`+`extract` 串成一次调用，支持 `expect`（urlMatches/textMatches/selector）、`submissionKey` 防重复提交 |
| `tabs_batch` | 标签页生命周期批处理，`open_many` 并发最多 10 个 URL，`isolatedContext` 独立 cookie 域 |
| `wait_for_human` | 遇到人机验证把标签页交给真人，之后在同一会话续跑 |

## 行业痛点 (Why)

浏览器 Agent 的成本大头不是页面加载，是**回放**：一次调用一个动作、每次回吐整页快照，填 10 字段表单 = 10+ 次调用，每轮的全文快照都重复进上下文。更危险的是"填完"与"提交"之间没有边界——Agent 会把最后一下也点掉，于是没有任何真实业务表单敢让它进。

## 旧范式 vs 新范式

- **旧做法**：一次调用一个动作（click / type / snapshot 各算一次），返回完整 DOM。多轮试错推进，token 随动作数膨胀。提交按钮无区别对待。
- **新做法**：工具粒度 = 用户意图批次；增量快照把回放压到"增量 × N"；**不可逆动作默认强制拦截**，提交需显式 `allowSubmit: true`。

## 生产力影响 (How)

- **降本**：同任务更少轮次、更少 token、更快收敛。
- **可合规**：把"人工确认最后一步"编码进工具层而非 prompt 约定——这是 Agent 进入报销/报名/下单/政务表单的前置条件。
- **诚实边界**：明确不做 stealth、不伪造指纹、不破解验证码；有 bot 检查就交还给人（`wait_for_human`），而非对抗。
- **安全沙箱**：`TURBO_BROWSER_SAVE_ROOT` 限定唯一可写目录。

## 采用成本

- Node 20+ 与任一 Chromium 内核浏览器；`claude mcp add turbo-browser -- npx -y turbo-browser-mcp` 一行装好，或写 `mcpServers` JSON。
- 零配置可跑（`--mode auto` 先探 9222 已登录浏览器，否则自起 headless）；`--doctor` 自检。
- 学习成本主要在 `batch_actions` 的 steps 语义与 `expect` 校验写法。
- MIT 许可，无云依赖、无 API key。

## 采用案例

- 暂无第三方公开案例。README 内置示例：填表 + 从磁盘附 PDF + 同调用返回结果；打开弹窗后只读增量；并行开标签页于独立 cookie 域；带 `expect` 校验提交凭证、用 `submissionKey` 拒绝重复提交。

## 风险/局限

- **生态未验证**：Show HN 49 分，无下游引用；"批量工具"这条路是否比"原子工具 + 更好的快照压缩"更优，尚无第三方数据。
- **工具过多**：11 个工具仍会占满模型选择空间；`--tools core` 可降到 6 个，但默认配置下工具选择本身是成本。
- **提交守卫是启发式**：靠多语言动词表识别不可逆动作，自定义按钮文案（图标按钮、非常规措辞）会漏判；拦错也有（把普通"下一篇"当成提交）。
- **基准自证**：README 的 benchmark 数字由作者自测，无独立复现。

## 核心线索

- GitHub：https://github.com/Tthanh2k6/turbo-browser-mcp
- npm：`turbo-browser-mcp`
- 首发来源：Show HN（49 points）
- 发布时间：2026-11
- 当前状态：试验中
