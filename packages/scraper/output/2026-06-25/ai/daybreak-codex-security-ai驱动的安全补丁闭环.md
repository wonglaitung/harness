# Daybreak / Codex Security

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首次将AI安全能力从"发现漏洞"推进到"自动生成补丁"的完整闭环 |
| 采用广度 | ☆☆☆/5 | 已扫描30K+代码库、30M+提交、500K+自动修复 |
| 时间新鲜 | ☆☆☆☆/5 | 2026年6月24日发布更新 |
| 社区热度 | ☆☆☆/5 | OpenAI官方发布，安全行业高度关注 |
| **总体判断** | ✅ | **新范式 — AI驱动的安全补丁闭环** |

## 技术定义 (What)
OpenAI推出的Daybreak安全平台，核心是Codex Security插件 + GPT-5.5-Cyber模型。它不只是发现漏洞，而是理解代码威胁模型→识别可达漏洞→收集验证证据→生成针对性补丁→验证修复结果的完整闭环。GPT-5.5-Cyber在CyberGym上达到85.6%（超越GPT-5.5的81.8%）。

## 行业痛点 (Why)
AI改变了网络安全的物理规律：过去瓶颈是"发现漏洞"（需要稀缺专家），现在瓶颈变成了"修补漏洞"——发现速度远超修补速度，防御者被漏洞报告淹没。仅报告漏洞不保护任何人，价值在于验证→理解影响→开发补丁→协调披露→部署修复。

## 旧范式 vs 新范式
- **旧做法**：SAST/DAST扫描器生成告警→安全工程师手动验证→开发者手动写补丁→手动测试→手动部署。周期数天到数周。
- **新做法**：AI理解代码威胁模型→自动识别可达漏洞→自动生成验证步骤→自动生成针对性补丁→自动验证修复。从发现到修复可在分钟级完成。

## 生产力影响 (How)
- 将安全工程师的产能从"逐个验证告警"解放到"审核AI补丁"
- 500K+发现已被自动判定为已修复，70K+被人工标记为已修复
- 支持SARIF/CodeQL导出，可集成到现有漏洞管理系统
- Patch the Planet计划：30+开源项目（cURL、Go、Python等）参与

## 采用成本
- Codex Security插件：需Codex订阅
- GPT-5.5-Cyber：受限发布，仅限受信任的防御者
- Daybreak Cyber Partner Program：合作伙伴计划
- 学习曲线低：集成在Codex工作流中，无需额外工具

## 采用案例
- 30K+代码库已扫描
- 30M+提交已分析
- Patch the Planet：与Trail of Bits、HackerOne合作，帮助开源项目从发现到修复
- cURL、Go、Python、Sigstore、pyca/cryptography等开源项目参与

## 风险/局限
- GPT-5.5-Cyber受限发布，普通开发者无法直接使用
- AI生成的补丁仍需人工审核确认
- 安全能力民主化的双刃剑：防御者和攻击者都可能使用
- 目前主要覆盖软件漏洞，物理安全/社会工程不在范围内

## 核心线索
- 官方页面：https://openai.com/index/daybreak-securing-the-world
- Codex Security插件：https://openai.com/daybreak/codex-security-plugin/
- Patch the Planet：https://openai.com/index/patch-the-planet
- 发布时间：2026-06-24
- 当前状态：活跃发布中