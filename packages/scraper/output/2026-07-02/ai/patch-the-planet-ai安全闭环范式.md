# Patch the Planet

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首次提出"AI发现→人类验证→AI修补→人类审核"的安全闭环模式，将AI安全从"漏洞扫描"推进到"漏洞修复全流程" |
| 采用广度 | ☆☆☆☆/5 | 首批参与项目包括 cURL、Python、Go、OpenBSD、Sigstore 等核心开源基础设施，覆盖网络、加密、供应链 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年7月1日发布，OpenAI Daybreak 系列最新动作 |
| 社区热度 | ☆☆☆☆/5 | OpenAI 官方博客首发，Trail of Bits 全职投入，HackerOne 和 Calif 合作，Linux Kernel/Chrome/Safari/Firefox 均有实战成果 |
| **总体判断** | ✅ | **新范式** |

## 技术定义 (What)
Patch the Planet 是 OpenAI Daybreak 计划下的开源安全倡议，核心是将前沿AI模型（GPT-5.5-Cyber、Codex Security）与专业安全工程师配对，形成"AI辅助发现→人类验证→AI辅助修补→人类审核→维护者部署"的完整安全闭环。不同于传统AI漏洞扫描器只报告问题，Patch the Planet 直接交付经审核的补丁和测试。

## 行业痛点 (Why)
开源维护者面临安全报告泛滥：AI加速了漏洞发现，但维护者时间和资源没有增加。大量误报、重复报告、缺少补丁的问题让维护者不堪重负。传统模式是"发现→报告→等待"，Patch the Planet 改为"发现→验证→修补→审核→交付"。

## 旧范式 vs 新范式
- **旧做法**：AI漏洞扫描器批量发现 → 生成大量未验证报告 → 维护者自行甄别和修复 → 补丁质量参差不齐
- **新做法**：AI发现漏洞 → 安全工程师验证并去重 → AI生成补丁和测试 → 安全工程师审核 → 交付可合并的PR → 维护者决定是否部署

## 生产力影响 (How)
- **发现速度**：1天内建成完整 Fuzzing Lab（传统需数周）
- **修复效率**：差异测试从数周/月压缩到数天
- **实战成果**：19个项目中已发现数百个安全问题并合并数十个补丁；Linux Kernel 生成8个指针信息泄露PoC + 24个本地提权PoC；Chrome V8 发现5个可利用漏洞；Safari 一周内发现10+可利用漏洞；OpenBSD 发现23年历史的 UAF 漏洞
- **可复用基础设施**：Fuzzing harness、CVE变体分析管道、差异测试系统、威胁模型、去重/误报过滤工作流

## 采用成本
- 开源维护者：免费接入，获得 ChatGPT Pro + Codex Security 访问权 + API 额度
- 安全团队：需要 GPT-5.5-Cyber 级别模型能力和专业安全工程师
- 学习曲线：低（维护者只需审核和决定部署，无需学习新工具）

## 采用案例
- **Linux Kernel**：GPT-5.5-Cyber 在3000万行代码中定位安全相关组件，自动生成 PoC
- **cURL**：Trail of Bits 使用 Codex 构建完整 Fuzzing Lab
- **OpenBSD**：发现23年历史的 System V 信号量 UAF 漏洞
- **FreeBSD**：Calif 使用 Codex 发现并验证多个本地提权漏洞
- **Chrome/Safari/Firefox**：三大浏览器引擎均发现可利用漏洞

## 风险/局限
- AI 误报率仍然较高，必须依赖安全工程师人工审核
- 协调披露流程可能延长修复时间
- 目前仅覆盖特定高影响力开源项目，规模化能力待验证
- 依赖 OpenAI 前沿模型，存在供应商锁定风险

## 核心线索
- 首发来源：https://openai.com/index/patch-the-planet
- Daybreak 主站：https://openai.com/daybreak/
- 合作方：Trail of Bits（安全工程）、HackerOne（漏洞协调）、Calif（漏洞发现）
- 发布时间：2026年7月1日
- 当前状态：活跃（首批冲刺已产出实战成果）
