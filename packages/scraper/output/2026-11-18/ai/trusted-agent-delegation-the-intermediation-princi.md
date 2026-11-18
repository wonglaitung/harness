# Trusted Agent Delegation — The Intermediation Principle（中介原则：Agent 作为可问责中介的身份层）

## 技术定义 (What)
Cloudflare 提出的 Agent 网络身份框架，核心是一条原则——**"用户与站点之间的商业关系，以及各方的安全责任，必须在中介存在的情况下依然成立"**（The Intermediation Principle）。它把远程托管的 Personal Agent 明确定义为一类"中介"（与云浏览器、代理/VPN 同类），并指出中介会系统性剥离站点对用户的可见性。解决方案是把安全与反欺诈领域沿用的三件套——**Identity（身份）/ Reputation（信誉）/ Accountability（问责）**——重新施加到 Agent 这一层，让站点能回答三个问题：这个行为主体是否如实表明了自己的身份？它是否可信？出了问题谁负责？

## 行业痛点 (Why)
站点今天只能看到 Agent，看不到 Agent 背后的人。而这一个事实同时打断了六条既有的商业与安全机制：(1) **账号共享**——一个订阅被用在无数用户身上；(2) **合规**——年龄/地域限制无法核实；(3) **友善欺诈**——用户授权了购买却事后否认，站点拿不出设备/IP/地址证据，因为请求来自 Agent 的基础设施；(4) **人机验证失效**——CAPTCHA 测的是"你是不是人"，而 Agent 从没假装是人，把信号透传给真人用户只是降低效率、不增加任何信息；(5) **身份伪装**——Agent 跑住宅 IP、用真浏览器、刻意混入人类流量；(6) **封禁连坐**——封掉一个作恶 Agent 会同时封掉它代理的所有无辜用户。

## 旧范式 vs 新范式
- **旧做法**：反爬/风控的默认动作是"识别并阻断自动化流量"。当自动化流量是少数时这可行；当它变成多数（文中判断 Agent 流量可能很快超过人类浏览），"阻断"直接等于"拒绝大部分客户"。于是站点陷入两难：要么放行并承担全部欺诈与合规风险，要么阻断并损失业务。
- **新做法**：不再试图把人机区分开（这是无解的，因为 Agent 越来越像人且从不声称自己是人），而是把**"用户—Agent—站点"三方关系显式建模并传递下去**：Agent 与 Operator 必须可识别、可问责，站点按"具体是哪个 Agent、代表哪个用户"做粒度化授权（allow / block-on-ad-pages / block），而非一刀切按流量类别封堵。Cloudflare 的落地形态是 Security Analytics 新增 "Personal Assistants" 流量类别 + 逐 Agent 策略 + Account Abuse Protection 中"该账号被哪些 Agent 代表"的视图——发现某个 Agent 在攻击某账号时，可用 Hashed User ID 的 WAF 规则只封该账号，而不封掉所有依赖该 Agent 的用户。

## 生产力影响 (How)
对站点运营方：从"要么全放要么全封"升级为可运营的中间态——可以欢迎某个 Personal Agent 抓取文章，同时在同一站点的广告页上封掉它；可以按用户维度而非 Agent 维度处置欺诈，避免连坐性业务损失。对 Agent 生态：把"可被识别"变成进入主流站点的前提条件，倒逼 Agent Operator 建立身份与问责机制（类似当年 Verified Bot 目录对搜索引擎爬虫的作用）。对合规团队：为年龄/地域等法规要求提供了可审计的链路依据。

## 采用成本
站点侧：需采用 Cloudflare 的 AI Crawler & Agent access policies（原名 AI bot policies 已扩容重命名），Account Abuse Protection 仍处 early access。Agent Operator 侧：需接入被认可的目录以"可被识别"，目前只覆盖 supported personal agents，存在准入名单问题。生态侧：这是单厂商推动的框架，跨厂商互认机制尚未建立——文中自述"下一步目标是帮站点保留用户关系的上下文"，说明当前仍未解决身份透传本身。

## 核心线索
- GitHub：
- 来源：https://blog.cloudflare.com/trusted-agent-delegation/
- 发布时间：2026-11-18
