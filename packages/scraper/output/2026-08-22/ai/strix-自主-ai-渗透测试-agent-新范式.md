# Strix — 自主 AI 渗透测试 Agent 新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ★★★★/5 | 将渗透测试从人工/脚本化转为自主多 Agent 协作，真正的 PoC 验证而非误报扫描 |
| 采用广度 | ★★★/5 | GitHub trending，多个集成（GitHub Actions、Agent Skills） |
| 时间新鲜 | ★★★★/5 | 活跃开发中 |
| 社区热度 | ★★★/5 | GitHub trending Python，Discord 社区活跃 |
| **总体判断** | ✅ | **新范式 — 安全测试自动化** |

## 技术定义 (What)
Strix 是一组自主 AI 渗透测试 Agent，像真正的黑客一样动态运行代码、发现漏洞并通过实际 PoC 验证。它内置完整的渗透测试工具链：HTTP 拦截代理（Caido）、浏览器利用、Shell 执行、Python 漏洞利用沙箱、侦察/OSINT、SAST+DAST。

## 行业痛点 (Why)
- 传统漏洞扫描器误报率高，无验证能力
- 人工渗透测试耗时长（几周）、成本高
- 静态分析工具无法发现运行时漏洞
- 安全团队需要在 CI/CD 中集成持续安全测试

## 旧范式 vs 新范式
- **旧做法**：人工渗透测试（数周周期）+ 静态扫描（高误报）+ 手动 PoC 编写
- **新做法**：AI Agent 自主发现→利用→验证→修复→报告，全自动闭环

## 生产力影响 (How)
- 渗透测试从数周压缩到数小时
- 零误报（每个漏洞附带可执行 PoC）
- CI/CD 集成：每个 PR 自动安全扫描
- 自动生成修复 patch 和合规报告

## 采用成本
- 安装：一键 curl 脚本
- 依赖：Docker + LLM API key
- 学习曲线：低（CLI 即用）
- 云平台：app.strix.ai 免费注册

## 采用案例
- CI/CD 安全扫描：PR 提交自动检测
- Bug Bounty 自动化：快速生成 PoC
- Agent 集成：支持 Claude Code、Cursor、Codex 通过 SKILL.md

## 风险/局限
- 依赖 LLM 质量（需要强大推理模型）
- 仅限授权目标的合法测试
- 可能需要专业安全知识解读结果

## 核心线索
- GitHub：https://github.com/usestrix/strix
- 网站：https://strix.ai
- 当前状态：活跃开发中
- 许可证：Apache 2.0