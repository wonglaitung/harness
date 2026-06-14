# SkillSpector

## 技术定义 (What)
NVIDIA 推出的 AI Agent Skills 安全扫描器，可在安装前检测漏洞、恶意模式和安全隐患。支持 64 种漏洞模式检测，覆盖提示注入、数据窃取、权限提升、供应链攻击等 16 大类。

## 行业痛点 (Why)
AI Agent Skills（如 Claude Code、Codex CLI 使用的 skills）默认以隐式信任执行，缺乏审查。研究显示 26.1% 的 skills 包含漏洞，5.2% 具有明显恶意意图。企业在采用 Agent 工作流时面临严重安全风险。

## 旧范式 vs 新范式
- **旧做法**：手动审查 skill 代码，依赖经验判断安全性，缺乏系统性检测工具，容易遗漏隐藏漏洞和供应链风险。
- **新做法**：自动化静态分析 + 可选 LLM 语义评估，两阶段扫描：静态分析快速识别已知模式（64 种），LLM 深度理解语义威胁。支持 Git 仓库、URL、zip、目录、单文件多种输入格式，输出终端、JSON、Markdown、SARIF 多种报告格式。

## 生产力影响 (How)
将 Agent Skills 安全审查时间从小时级降至分钟级，集成到 CI/CD 流程后可在部署前自动拦截高危 skills，降低企业 AI 采用的安全门槛。支持实时 CVE 查询（OSV.dev），自动检测依赖漏洞。

## 采用成本
低。Python 3.12+ 环境即可安装，支持 Docker 部署。静态分析无需 LLM API key，语义分析需配置 OpenAI/Anthropic/NVIDIA 端点。学习曲线平缓，命令行接口简洁。

## 核心线索
- GitHub：https://github.com/NVIDIA/SkillSpector
- 来源：https://github.com/NVIDIA/SkillSpector
- 发布时间：2026-06-15
