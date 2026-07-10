# Agent Governance Toolkit (AGT)

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首个"Agent治理即代码"工具包：将Policy-as-Code从云原生(Kubernetes)迁移到Agent原生，用确定性代码拦截替代提示词安全 |
| 采用广度 | ☆☆☆☆/5 | OWASP Agentic Top 10 全10项覆盖；AARM Extended R1-R9认证；ATF全5要素；多语言SDK(Python/TS/.NET/Rust/Go) |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年7月Public Preview，首发<1个月 |
| 社区热度 | ☆☆☆/5 | GitHub trending 81 stars/day；PyPI/npm/NuGet三端发布；OpenSSF Scorecard认证 |
| **总体判断** | ✅ | **新范式 — Agent从"请遵守规则"到"结构上不可能违规"** |

## 技术定义 (What)
微软发布的Agent治理工具包，在Agent每次工具调用前插入确定性策略拦截层。核心公式：`govern(tool, policy_yaml) → safe_tool`，被拒绝的动作不是"不太可能发生"，而是**结构上不可能发生**。覆盖策略执行、零信任身份(SPIFFE/DID/mTLS)、执行沙箱、防篡改审计四大层。

## 行业痛点 (Why)
当前Agent安全依赖提示词级约束（"请遵守规则"），但OWASP LLM01:2025明确指出提示注入无完美防御。Andriushchenko et al. (ICLR 2025)报告GPT-4o/Claude 3/Llama-3的攻击成功率100%。OAuth和IAM只控制Agent能访问哪些服务，不控制连接后做什么。多Agent共享API密钥时，"某个Agent做了这事"不是有效的事故响应。

## 旧范式 vs 新范式
- **旧做法**：提示词安全（"请勿删除数据"）→ 概率性防御，可被绕过；OAuth scope控制服务访问权限，不控制操作语义
- **新做法**：确定性代码拦截（YAML策略引擎在工具调用前评估）→ 被拒绝的动作结构上不可能执行；SPIFFE/DID身份标识每个Agent；防篡改审计日志满足合规要求

## 生产力影响 (How)
- 2行代码即可治理任何工具函数：`safe_tool = govern(my_tool, policy="policy.yaml")`
- `agt verify` 一键OWASP合规检查，可集成CI/CD
- `agt red-team scan` 自动化提示注入审计
- Claude Code插件直接安装，无需修改现有Agent代码
- 多框架兼容：任何Python Agent框架均可接入

## 采用成本
- 时间：5分钟快速启动，策略编写按复杂度1-4小时
- 金钱：MIT开源免费
- 学习曲线：低（YAML策略声明式，类似Kubernetes NetworkPolicy）

## 采用案例
- **OWASP Agentic Top 10**：10/10全覆盖，作为官方参考实现
- **AARM Extended**：R1-R9全部认证通过
- **Claude Code**：通过插件市场直接安装治理插件
- **MCP Server集成**：.NET版本原生支持MCP Server治理

## 风险/局限
- Public Preview阶段，GA前可能有破坏性变更
- 策略引擎目前为YAML声明式，复杂条件可能需要OPA/Cedar扩展
- 沙箱层依赖Docker/E2B/OpenSandbox，本地开发需额外配置
- 不解决模型本身的幻觉/可靠性问题，只解决工具调用安全

## 核心线索
- GitHub：https://github.com/microsoft/agent-governance-toolkit
- 首发来源：GitHub Trending (Python) 2026-07-10
- 发布时间：2026年7月（Public Preview）
- 当前状态：Public Preview / 活跃开发