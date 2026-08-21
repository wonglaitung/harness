# AI-Infra-Guard — 全栈AI安全红队统一平台

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首次将 Agent Skill/MCP/Agent/越狱/AI Infra 五大安全维度统一为单一平台+独立CLI |
| 采用广度 | ☆☆☆/5 | Black Hat EU 25 Arsenal 入选，DeepSeek Awesome 收录，Tencent 品牌背书 |
| 时间新鲜 | ☆☆/5 | 项目成熟（v4.5.2），但独立 CLI 工具（skill-scan/mcp-scan）2026-07 新发布 |
| 社区热度 | ☆☆☆☆/5 | GitHub trending 435⭐/天，多语言 README，活跃社区 |
| **总体判断** | ⚠️ | **成熟项目中的新能力** — 核心平台成熟，但 CLI 化 + 统一分类标准是新范式信号 |

## 技术定义 (What)
腾讯朱雀实验室的全栈 AI 红队平台：ClawScan（Agent 安全扫描）+ Agent Scan + MCP Server Scan + Skill Scan + Jailbreak Evaluation，统一为一个 Web 平台 + 独立 CLI 工具。漏洞库 2000+ CVE，SkillTrustBench T01-T09 分类标准。

## 行业痛点 (Why)
AI 安全攻击面爆炸：Agent 越权、MCP 工具注入、Skill 供应链投毒、模型越狱、框架 RCE——每种攻击面需要不同工具，企业安全团队疲于集成。缺乏统一的 AI 安全风险评估框架。

## 旧范式 vs 新范式
- **旧做法**：Garak 测越狱 + 手动审计 Skills + 独立 MCP 扫描脚本 + Trivy 扫镜像 → 碎片化、无统一视图
- **新做法**：一个 docker-compose up → 全栈 AI 安全扫描 → 统一风险仪表盘 + CI/CD CLI 集成

## 生产力影响 (How)
- CI/CD 集成：`pip install aig-skill-scan && aig-skill-scan --repo ./skills` 即可在 PR 中自动扫描
- 统一风险视图：CISO 可在单一仪表盘看到全栈 AI 风险
- 社区生态：Skill Market 允许安全研究员贡献扫描技能

## 采用成本
- Docker 部署：4GB RAM + 10GB 磁盘
- CLI：`pip install aig-skill-scan`
- 需要 LLM API Key
- 学习曲线中等

## 核心线索
- GitHub：https://github.com/Tencent/AI-Infra-Guard
- 团队：Tencent Zhuque Lab
- 当前版本：v4.5.2 (2026-08-17)
- Black Hat EU 25 Arsenal 入选
- 状态：活跃迭代中