# SkillSpector

## 技术定义 (What)
AI Agent 技能安全扫描器，用于在安装 Claude Code、Codex CLI、Gemini CLI 等平台的 Agent 技能之前，检测漏洞、恶意模式和安全风险。支持 64 种漏洞模式检测，覆盖 16 个安全类别。

## 行业痛点 (Why)
当前 AI Agent 技能（如 Claude Code Skills、Codex Plugins）以隐式信任方式执行，缺乏安全审查。研究表明 26.1% 的技能存在漏洞，5.2% 具有恶意意图，但没有标准化的安全审计工具。

## 旧范式 vs 新范式
- **旧做法**：开发者通过阅读代码或简单测试判断技能安全性，缺乏系统性安全审计流程，容易忽略供应链攻击、提示注入、权限提升等隐蔽风险。
- **新做法**：使用自动化扫描器在安装前进行安全审计：静态分析快速识别已知漏洞模式 + LLM 语义分析评估复杂攻击场景，输出风险评分和修复建议，集成到 CI/CD 流程中。

## 生产力影响 (How)
将 Agent 技能安全审计从人工审查转变为自动化流程，可在几分钟内完成 64 类漏洞检测。支持 SARIF 格式输出，可直接集成到 GitHub Actions 等 CI 工具，防止恶意技能进入生产环境。

## 采用成本
安装简单（pip install 或 Docker），学习成本低。静态分析无需额外成本，LLM 语义分析需要配置 OpenAI/Anthropic API。单次扫描通常在秒级完成，适合作为 CI/CD 必检项。

## 核心线索
- GitHub：https://github.com/NVIDIA/SkillSpector
- 来源：https://github.com/NVIDIA/SkillSpector
- 发布时间：2026-06-14
