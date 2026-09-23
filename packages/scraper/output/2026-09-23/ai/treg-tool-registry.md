# treg — "OpenRouter for Tools"

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | "OpenRouter for tools"框架明确，核心是服务端凭证注入 + 凭证阶梯，直接解决 Agent 工具获取痛点 |
| 采用广度 | ☆☆☆/5 | 60+ 供应商、3000+ 端点，自托管可用，团队内部已使用 |
| 时间新鲜 | ☆☆☆☆/5 | 新发布，GitHub trending 230 stars/day |
| 社区热度 | ☆☆☆/5 | 230 stars/day，Discord 社区活跃 |
| **总体判断** | ✅ | **新范式（观察中）** |

## 技术定义
treg 是 Agent 工具层的"目录 + 凭证中介"。Agent 指向单一 base URL，用单一 token 调用全部已编目端点。密钥在服务端注入，调用方永不接触真实凭证；按次计费（一分钱起）。

## 行业痛点
Agent 做真实工作所需的 API 被锁在昂贵订阅墙后（Semrush $139/月等），单一调用无法覆盖整月订阅成本；凭证管理散漏、无法跨团队共享与计量。OpenRouter 解决了模型的此问题，工具层长期空白。

## 旧范式 vs 新范式
- **旧做法**：每个工具单独注册、保管密钥、为单次调用买单月订阅
- **新做法**：一个 token 统一目录调用，凭证阶梯自动降级（自有 key > 共享密钥 > 免费路由 > treg 计费），按需付费

## 生产力影响
让 Agent 数分钟内获得 3000+ 真实生产工具；`treg scan`/`upload` 零思考共享团队工具；`treg run stripe` 以组织凭证执行 CLI；402 响应携带余额元数据，Agent 可程序化处理计费。

## 采用成本
极低。一条 curl 命令装 CLI，登录即用无需注册；Claude Code 插件 / npx skills 一键接入；自托管免费。

## 采用案例
- Superdesign 团队（缔造方）内部生产使用
- 供应商覆盖：Fish Audio（TTS）、Hunter（邮箱查找）、Stripe、GitHub、Vercel CLI 等

## 风险/局限
- 上游 API 变化依赖 treg 的"只转发不建模"设计来吸收，但仍存在依赖风险
- 计费透明性依赖 treg 的服务端诚实性
- 生态尚早期，供应商规模需持续扩大

## 核心线索
- GitHub：https://github.com/superdesigndev/treg
- 在线托管：https://treg.to
- 发布时间：近期（GitHub trending daily）
- 当前状态：活跃 / 早期