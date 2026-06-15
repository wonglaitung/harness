# SkillSpector - AI Agent 技能安全扫描器

## 技术定义 (What)
NVIDIA 发布的 AI Agent 技能安全扫描器，可在安装前检测技能包中的漏洞、恶意模式和安全风险。支持 64 种漏洞模式，覆盖 16 个类别。

## 行业痛点 (Why)
AI Agent 技能（Claude Code、Codex CLI、Gemini CLI 等）以隐式信任和最小审查执行。研究显示 **26.1% 的技能包含漏洞**，**5.2% 显示恶意意图**。开发者缺乏工具评估"这个技能安全吗？"

## 旧范式 vs 新范式
- **旧做法**：盲目信任安装 AI agent 技能，无安全审计
- **新做法**：使用静态分析 + LLM 语义评估双阶段扫描，生成风险评分（0-100）和修复建议

## 生产力影响 (How)
- CI/CD 集成：生成 SARIF 报告，与 GitHub Security 集成
- 快速扫描：静态分析模式无需 LLM，秒级出结果
- 深度分析：可选 LLM 语义评估，识别复杂攻击链

## 采用成本
- 安装：`pip install skillspector` 或 Docker 镜像
- 学习曲线：命令行工具，5 分钟上手
- 成本：静态扫描免费，LLM 分析需 API 调用费用

## 检测的漏洞类别
1. Prompt Injection（提示注入）
2. Data Exfiltration（数据泄露）
3. Privilege Escalation（权限提升）
4. Supply Chain（供应链攻击）
5. Excessive Agency（过度授权）
6. Output Handling（输出处理）
7. System Prompt Leakage（系统提示泄露）
8. Memory Poisoning（记忆污染）
9. Tool Misuse（工具滥用）
10. Rogue Agent（恶意代理）
11. Dangerous Code（危险代码 AST）
12. Taint Tracking（污点追踪）
13. YARA Signatures
14. MCP Least Privilege
15. MCP Tool Poisoning
16. Trigger Abuse

## 核心线索
- GitHub：https://github.com/NVIDIA/SkillSpector
- 来源：GitHub Trending (Python)
- 发现时间：2026-06-15
- 今日 Stars：964