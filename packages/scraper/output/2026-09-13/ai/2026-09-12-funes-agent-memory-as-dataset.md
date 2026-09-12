# Funes — Agent Memory as Dataset

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首次提出「记忆即数据集，非服务」——将 Agent 会话记录标准化为可跨 Agent、跨机器的持久记忆层 |
| 采用广度 | ☆☆/5 | 首发阶段，已支持 Claude Code、Codex、pi、Hermes |
| 时间新鲜 | ☆☆☆☆☆/5 | 发布于 2026-09-03（距今 < 2 周） |
| 社区热度 | ☆☆☆/5 | Hugging Face 官方博客发布，GitHub 开源 |
| **总体判断** | ✅ | **新范式** |

## 技术定义

Funes 是一个 Agent 记忆层：它将编码 Agent（Claude Code、Codex、pi、Hermes）的会话轨迹解析为统一格式，嵌入到本地 Lance 数据集，提供向量+BM25 混合检索。Agent 可在工作中主动调用 `recall` 工具检索历史决策。支持绑定 Hugging Face 数据集实现跨机器共享——记忆成为你拥有的数据集，而非租赁的 API 服务。

## 行业痛点

编码 Agent 每次新会话都是「陌生人」：上周的决策、尝试过的方案、放弃的方向全部消失。传统方案要么不解决（会话即焚），要么依赖云端服务（数据主权丧失）。Funes 让记忆本地优先、跨 Agent 通用、可移植。

## 旧范式 vs 新范式

- **旧做法**：每次新会话从零开始；或手动复制粘贴历史上下文；或绑定单一 Agent 的专有记忆服务
- **新做法**：统一的记忆数据集，Claude Code 的决策可被 Codex 次日召回；记忆跟随开发者跨机器移动

## 生产力影响

- 消除「重复解释代码库」的 token 浪费
- 跨 Agent 知识延续：不同 Agent 各有所长，记忆不再割裂
- 完全本地运行：嵌入和重排序都在本地，无数据外泄风险

## 采用成本

- 单条命令安装：`curl ... | sh` + `funes add claude`
- 本地推理，无需 GPU
- 开源（GitHub: huggingface/funes）

## 风险/局限

- 首批支持仅 4 个 Agent（Claude Code、Codex、pi、Hermes）
- 跨机器共享依赖 Hugging Face Hub 账号
- 隐私：尽管本地优先，Hub 同步需信任凭证扫描

## 核心线索

- GitHub：https://github.com/huggingface/funes
- 首发来源：https://huggingface.co/blog/funes
- 发布时间：2026-09-03
- 当前状态：活跃开发中