# Oak

## 技术定义 (What)
Oak 是专为 AI Agent 设计的版本控制系统，替代传统 Git。核心创新：**Lazy working tree**（延迟加载工作树）、**Agent action contracts**（Agent 操作合约）、**Branch review/triage**（分支审查与分类）。Agent 可通过 `oak mount` 挂载仓库而无需完整克隆，通过结构化 JSON 接口完成分支管理、代码审查、合并操作。

## 行业痛点 (Why)
Git 为人类设计，Agent 使用困难：1) 大仓库克隆耗时长、占用空间；2) 命令输出非结构化，Agent 难以解析；3) 无原生的 Agent 权限控制；4) 分支管理需多步操作，Agent 容易出错。

## 旧范式 vs 新范式
- **旧做法**：Agent 模拟人类使用 Git：`git clone` → `git checkout -b` → 修改 → `git add/commit/push`。输出解析依赖正则表达式，错误处理脆弱。大规模仓库（50k+ 文件）克隆慢、占用大。
- **新做法**：Agent-native 版本控制：`oak mount` 按需加载文件（O(1) 分支创建）、结构化 JSON 输出（`--json` flag）、内置 Agent 操作合约（`finish` saga 自动化推送审查）、多仓库空间（`oak space` 跨仓库工作）。Benchmark：50k 文件仓库分支创建 7.5ms vs Git 10.5ms。

## 生产力影响 (How)
让 Agent 高效操作大规模代码库。延迟加载减少网络和存储开销，结构化接口提升 Agent 可靠性。适用于自动化代码审查、多仓库重构、大规模迁移等场景。

## 采用成本
**时间成本**：安装简单（`oak clone`），需学习 Oak 命令集。与 Git 语义类似，迁移成本低。**金钱成本**：开源免费。云托管服务（oak.space）提供协作功能。**生态成本**：早期项目，工具链和社区支持有限。

## 核心线索
- GitHub：https://github.com/oakvcs/oak
- 来源：https://news.ycombinator.com/show
- 发布时间：2026-06-23
