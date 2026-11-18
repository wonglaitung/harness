# Codex Security — 扫描产物即审计记录（Rubric-as-Input + 跨 worktree 去重）

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 把 Agent 安全扫描重新定义为**审计记录生产**：report + findings 落盘且含源码证据与覆盖排除项；同一 state dir 的 linked git worktree 共享扫描历史以做跨分支去重；severity **按用户自带 rubric** 判定而非工具内建标准；威胁模型 `SECURITY.md` 本身成为可生成/复用的策略工件 |
| 采用广度 | ☆☆☆/5 | 官方三种接入面（Codex 插件工作流、CLI、TypeScript SDK）+ GitHub Action；产物对接 SARIF/JSON/CSV 与 Linear/Jira/GitHub；支持导入第三方 scanner 报告，处于「平台化接口」而非单点工具 |
| 时间新鲜 | ☆☆☆☆/5 | 2026 年在榜（Codex 安全线当期发布物） |
| 社区热度 | ☆☆/5 | GitHub trending TypeScript 上榜；暂无 HN 大讨论（企业与安全团队为主要受众） |
| **总体判断** | ✅ | **新范式（Agent 安全扫描的产物与度量契约层）** |

## 技术定义 (What)
OpenAI 官方开源的 Codex 安全工具链：`@openai/codex-security` CLI + TypeScript SDK + Codex 插件 + GitHub Action。每次扫描落盘一份带源码证据与 coverage limits 的 Markdown 报告与结构化 findings；`cs scans show` 可回溯；linked worktree 共享扫描历史以去重；支持第三方 scanner 结果导入与 SARIF/JSON/CSV 导出。

## 行业痛点 (Why)
Agent 安全扫描的失效点不是「找不到」，而是**「说了不算、算了不复现」**：结论留在聊天流里，没有证据链、没有「哪些路径没扫」的声明、无法与上一轮比对、无法去重、无法交给既有 AppSec 流程。多分支/多 worktree 重复报同一问题；severity 又被工具内建标准绑架，而非组织自己的风险口径。

## 旧范式 vs 新范式
- **旧做法**：让 Agent 在对话里找漏洞，结论在聊天记录中；severity 由模型/工具决定；各分支各自为政。
- **新做法**：扫描 = 产出审计记录（report + findings + 排除项）；state dir 成为去重与复算锚点；severity 由用户 rubric 判定；第三方 scanner 结果作为外部证据汇入同一记录；按 SARIF/JSON/CSV 导出并建单；威胁模型作为可版本化工件（`SECURITY.md`）复用。

## 生产力影响 (How)
- 可复算：同仓库重跑可与上轮比对，验证修复（"verify an existing fix"）。
- 可审计：报告含源码证据与覆盖边界，能回答「你没扫什么」。
- 可交接：SARIF / Linear / Jira / GitHub，进入既有 AppSec 流程。
- 可批量：bulk scans 支持可续跑的多仓战役；CI 与容器内可跑。

## 采用成本
- `npm i -g @openai/codex-security` + `cs login`（或 `npx`）；Node 22.13+/24/26；Python 3.10+（3.10 需 `tomli`）。
- CI 需 `OPENAI_API_KEY` 或 `CODEX_API_KEY`；headless 机器支持 device/SSH 登录。
- 真实成本：扫描时长/费用（`--max-time`、cost limits 可约束）与为 severity 自建 rubric 的一次性投入。部分能力需 Trusted Access for Cyber / Daybreak。

## 采用案例
- 单仓扫描：`cs scan . --path src --path tests`，读报告 → 要 patch → 验证修复。
- 变更门禁：`cs scan . --diff origin/main` 只扫提交差异。
- 策略建设：`cs policy . --knowledge-base architecture.md` 生成威胁模型草稿（写在仓库外，不改既有文件）。

## 风险/局限
- 依赖 Codex/OpenAI 账户与额度；部分安全请求受策略限制（需 Trusted Access）。
- "shared history + 去重" 要求保持 `CODEX_SECURITY_STATE_DIR` 稳定，跨环境迁移易断。
- 覆盖面由扫描器自身决定；报告中的 coverage limits 必须被人工阅读，别把 pass 当全覆盖。
- OpenAI 生态单向绑定较强（CLI/SDK/Cloud 一体），与同类开源 red-team 工具（Strix、deepsec）并存竞争。

## 核心线索
- GitHub：https://github.com/openai/codex-security
- 首发来源：GitHub trending（TypeScript, daily）
- 发布时间：2026 年
- 当前状态：活跃
