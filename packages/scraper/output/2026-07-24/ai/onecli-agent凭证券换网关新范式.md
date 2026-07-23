# OneCLI

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首创"Agent凭证券换网关"概念：Agent持假密钥，网关透明替换为真密钥，Agent永远看不到真实凭据 |
| 采用广度 | ☆☆/5 | 早期项目，Show HN 67 points，尚无已知大规模采用 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年7月首发，极新 |
| 社区热度 | ☆☆/5 | Show HN 67 points，社区初步认可 |
| **总体判断** | ⚠️ | **观察中（概念创新强+时间新鲜，采用广度待验证）** |

## 技术定义 (What)
OneCLI是一个开源凭据网关，位于AI Agent与外部API服务之间。Agent使用占位符密钥（如`FAKE_KEY`）发出HTTP请求，网关拦截请求后将占位符替换为真实凭据，转发给目标API。Agent永远不接触真实密钥。

## 行业痛点 (Why)
AI Agent需要调用数十个API，但将真实凭据硬编码到每个Agent中是巨大安全风险：Agent可能泄露密钥、被注入攻击窃取、或跨环境滥用。现有方案要么给Agent完整密钥（不安全），要么用环境变量（仍可被读取），缺乏专门为Agent设计的凭据隔离层。

## 旧范式 vs 新范式
- **旧做法**：将API密钥硬编码到Agent代码/环境变量中，Agent直接持有真实凭据；或使用Vault SDK但Agent仍需读取权限
- **新做法**：Agent仅持占位符密钥，Rust网关透明替换；AES-256-GCM加密存储，仅请求时解密；支持host/path模式匹配路由

## 生产力影响 (How)
- 一处存储、随处注入：凭据集中管理，Agent零感知
- 多Agent支持：每个Agent独立访问令牌+作用域权限
- 密钥轮换不影响Agent：只需更新网关中的凭据
- 审计能力：网关层记录所有Agent API调用

## 采用成本
- 低成本：`curl -fsSL https://onecli.sh/install | sh` 一键安装
- 支持Docker Compose部署
- 需要将Agent的HTTP代理指向网关（localhost:10255）
- Rust网关+Next.js Dashboard+PostgreSQL，资源占用适中

## 采用案例
- 本地开发：单用户模式，无需登录
- 团队协作：Google OAuth多用户模式
- Vault集成：支持Bitwarden等密码管理器按需注入

## 风险/局限
- 早期项目，生产环境未经大规模验证
- HTTPS需要MITM拦截（证书信任链）
- 仅支持HTTP协议凭据注入，不支持gRPC/WebSocket等
- 尚无RBAC细粒度权限控制

## 核心线索
- GitHub：https://github.com/onecli/onecli
- 官网：https://onecli.sh
- 首发来源：Show HN (67 points)
- 发布时间：2026年7月
- 当前状态：活跃 / 早期