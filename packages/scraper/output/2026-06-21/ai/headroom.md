# Headroom

## 技术定义 (What)
Headroom 是一个 LLM 上下文压缩层，在 Agent 与 LLM 之间插入智能压缩管道，将工具输出、日志、RAG 结果、文件内容压缩 60-95%，同时保持答案准确性。首创 CCR（Cache-Compress-Retrieve）可逆压缩架构，支持 6 种压缩算法、跨 Agent 内存共享、输出 token 优化。

## 行业痛点 (Why)
AI Agent 上下文爆炸：工具输出、日志文件、RAG 检索结果动辄数万 token，导致成本高昂、响应延迟、KV 缓存失效。现有方案要么不压缩（浪费），要么不可逆（信息丢失）。

## 旧范式 vs 新范式
- **旧做法**：**旧做法**：1) 手动筛选内容，丢弃"不重要"的部分（不可逆）；2) 使用 RAG 分块，但每个查询都要重新检索（无状态）；3) 接受高昂的 token 成本；4) 无输出 token 优化能力。
- **新做法**：**新做法**：1) 自动识别内容类型（JSON/代码/文本），选择最优压缩算法；2) 本地缓存原始内容，LLM 需要时按需检索（CCR 可逆）；3) 稳定前缀对齐，最大化 KV 缓存命中率；4) 跨 Agent 内存去重；5) 自动调整模型输出冗余度。

## 生产力影响 (How)
**成本降低**：60-95% token 减少，实测 SRE 调试场景节省 92%。**延迟优化**：压缩后 prompt 更短，推理更快。**精度保持**：GSM8K/TruthfulQA 基准测试无精度损失。**开发效率**：零代码接入（proxy 模式），或一行代码集成（library 模式）。

## 采用成本
**低**：pip install 或 npm install 即可。支持 5 分钟快速集成（proxy 模式）。无需修改现有 Agent 代码。开源免费，支持本地部署。

## 核心线索
- GitHub：https://github.com/chopratejas/headroom
- 来源：https://github.com/trending/python
- 发布时间：2026-06-21
