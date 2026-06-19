# Enterprise-Managed Authorization (EMA) for MCP

## 技术定义 (What)
EMA 是 MCP 协议的企业级认证扩展，允许组织通过身份提供商（IdP）集中管理 MCP 服务器访问权限。用户单次登录即可自动连接所有授权的 MCP 服务器，无需逐个 OAuth 授权。核心技术是 ID-JAG（Identity Assertion JWT Authorization Grant）授权流。

## 行业痛点 (Why)
标准 MCP 授权模型要求员工逐个授权每台服务器，入职流程繁琐。安全团队无法强制执行一致策略，缺乏审计跟踪。工作和个人账户容易混淆，存在数据泄露风险。企业级 MCP 部署受阻。

## 旧范式 vs 新范式
- **旧做法**：每个用户独立授权每台 MCP 服务器，手动配置 OAuth，分散管理，无集中控制。企业部署时每个员工需要逐一连接各服务，效率低下且安全风险高。
- **新做法**：管理员在 IdP 定义一次策略，用户通过现有企业身份登录 MCP 客户端，IdP 根据组/角色/条件访问规则自动授予或拒绝服务器访问。ID-JAG 流程在 SSO 期间获取身份断言 JWT，交换为 MCP 服务器访问令牌，用户无需经过逐服务器同意屏幕。

## 生产力影响 (How)
零接触入职：用户登录即获得所有授权工具。集中式策略与审计：所有访问决策在 IdP 控制台统一管理。防止个人/企业账户混淆：移除交互式账户选择步骤，降低数据流错误风险。已获 Anthropic、Microsoft、Okta、Linear、Figma、Supabase 等采用。

## 采用成本
组织需要支持 EMA 的 IdP（目前 Okta 已支持 Cross App Access）。MCP 客户端和服务器需要实现扩展规范。用户端零成本：单次登录即可。详见规范：https://modelcontextprotocol.io/extensions/auth/enterprise-managed-authorization

## 核心线索
- GitHub：https://github.com/modelcontextprotocol/ext-auth
- 来源：https://blog.modelcontextprotocol.io/posts/enterprise-managed-auth/
- 发布时间：2026-06-19
