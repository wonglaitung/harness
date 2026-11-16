# ChatGPT Wallet — Payment Token 隔离的 Agent 支付范式

## 技术定义 (What)
ChatGPT Wallet 是 OpenAI 与 Amex / Mastercard / Visa 共建的 Agent 支付层：用户一次性绑卡，Agent 每次购买前需用户生物识别（Face ID / 指纹）授权，授权后由支付网络签发 payment token（卡号+安全码+有效期的替代物）供 Agent 与商户使用，真实卡号永不暴露给 Agent 或商户，同时保留原有卡片返现与争议保护权益。

## 行业痛点 (Why)
Agent 要做「代买」这一步，卡在支付信任上：把真实卡号交给 Agent 风险极高；而商户侧的风控系统又会把 Agent 发起的合法交易判定为欺诈而拒绝。整个 Agent 电商缺少一个双方都能接受的凭证机制与配套的商户接纳规范。

## 旧范式 vs 新范式
- **旧做法**：旧做法：要么由人类在每个结账页手动输入卡号（Agent 无法闭环），要么把 API key / 卡号直接塞进 Agent 上下文（泄露即灾难），商户侧则靠 User-Agent 白名单或干脆全量拦截 bot。
- **新做法**：新做法：「人类逐笔生物识别授权 + 支付网络签发一次性 payment token」。Agent 拿到的是可支付但不可复用的凭证；人类保有每笔的清晰授权记录。配套 Commerce Partner Playbook 定义了商户侧三项接纳动作：产品信息可通过 feed 提交、站点用 Web Bot Auth 识别签名请求、风控侧与 Forter/Riskified/Sardine/Signifyd 及 Adyen/Stripe 协同识别 Agent 交易。

## 生产力影响 (How)
把「Agent 代买」（agentic commerce）从 demo 变成可上线的商业闭环。对商户：不必重写结账流程，token 兼容现有 checkout，只需放开签名 bot 访问并调整风控规则。对开发者：新增一条 Agent 可调用的变现通道，且合规边界清晰（真实卡号不出网）。长期路线是用户设定预算/类目/时间窗后预授权，Agent 完全自主完成采购。

## 采用成本
商户侧：配置 Web Bot Auth、上传产品 feed、与风控/Payment Service Provider 沟通识别规则（数十小时到数周，取决于风控供应商配合度）。开发者：接入 dots / Wallet 生态，目前仅 ChatGPT Pro 美国 18+ 用户可用，覆盖面窄。用户侧：零学习成本，绑卡 + 生物识别。

## 核心线索
- GitHub：
- 来源：https://openai.com/index/introducing-chatgpt-wallet
- 发布时间：2026-11-16
