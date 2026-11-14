# Apron Chat Protocol（极简自托管聊天协议 + Agent 原生规格分发）

## 技术定义 (What)
Apron 是一个面向「自托管小群组聊天」的极简协议：JSON over 任意 transport（通常一条 WebSocket），核心小到能用约 100 行写出服务端、几行写出无状态 bot，同时通过可选增量能力支持 rooms / threads / DMs / reactions / presence。它的设计取向是**显式放弃**三件事——全局联邦、E2E 加密、防女巫——以换取"正确实现一个客户端/服务端尽可能容易"。最具范式意义的一点是它把 `apron.chat/llms.txt` 作为一等公民的规格入口：直接向 Agent 提供 Markdown 规格、JSON Schema 和 wire fixtures，使"让 LLM 在一下午内写出一个后端"从愿景变成设计约束。

## 行业痛点 (Why)
聊天应用与它的网络过度耦合：你无法自托管 Discord，也无法把 Discord 客户端指向自己的服务器。想自建一个团队/家庭/客服群聊，只能在两种坏选项间选：①用 Matrix/XMPP/IRCv3 这类为联邦和通用性设计的重型协议，实现成本远超需求；②直接用 Slack/Discord 这类 SaaS，失去数据主权。而新协议往往又陷入 XKCD 927 的"再来一个标准"困境。Apron 的答案是：**砍掉复杂度来源本身**（不联邦、不 E2E、不防滥用），换取实现成本的数量级下降。

## 旧范式 vs 新范式
- **旧做法**：自托管聊天协议追求通用性：联邦、跨服务器身份、E2E 加密、SASL 认证套件、能力协商——每一层都必要，叠加起来则是"写一个可用实现需要数月"。与此同时，协议规格是为人类阅读者写的（散文式 RFC + 大量前置知识）。
- **新做法**：协议被设计成「可作为下午项目实现」：核心约 100 行，后端权威、前端退化为 renderer；JSON 消息故意携带冗余完整对象（如消息内嵌完整 user），牺牲带宽换取客户端无需查表即可渲染；只用 `guest` / `token` 两种登录原语覆盖大多数自托管场景，其余（webauthn/email/external）作为可选增量；不做能力协商，缺失能力自然优雅降级。**规格以 Agent 可消费形式分发**：`llms.txt` → Markdown 规格 + JSON Schema + wire 一致性 fixtures。

## 生产力影响 (How)
对想自建群聊的团队：从"研究 Matrix 栈"变成"跑一个参考实现或让 Agent 生成一个"。已提供三套参考实现（Cloudflare Worker 免费额度版、Go 完整自托管版、SvelteKit 前端）与一个 PR bot，证明协议在真实场景可落地。对 Agent 工程的意义更大：它示范了**新协议应有的交付形态**——规格不只给人读，同时给出 `llms.txt`、JSON Schema 和可测试的 wire fixtures，让 LLM 能直接生成并自测实现。这直接呼应 README 里"An afternoon or one-shot LLM prompt should implement a working backend provider"的设计目标。

## 采用成本
上手极低：读 `PROTOCOL.md` → 打开发布 demo（web.apron.chat）→ clone 参考实现。无 SDK 依赖包袱，无账户体系。代价是必须接受它的三个放弃项：没有跨服务器联邦、没有 E2E 加密（依赖 TLS 作传输层安全）、没有防女巫/反垃圾（信任模型假设"成员彼此基本认识"）。若需求超出小群组自托管，这个协议主动出局。

## 核心线索
- GitHub：https://github.com/shazow/apron
- 来源：https://apron.chat/
- 发布时间：2026-11-14
