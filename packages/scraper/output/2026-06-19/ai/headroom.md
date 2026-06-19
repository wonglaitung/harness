# Headroom

## 技术定义 (What)
Headroom 是一个 AI Agent 上下文压缩层，通过 6 种算法在发送给 LLM 前压缩工具输出、日志、RAG 片段和对话历史，实现 60-95% 的 token 削减，同时保持答案准确性。核心创新包括可逆压缩（CCR）、跨代理内存、输出 token 削减和 MCP 服务器支持。

## 行业痛点 (Why)
AI Agent 运行时产生大量上下文（工具输出、日志、RAG 结果），导致 token 成本飙升、推理延迟增加、上下文窗口快速耗尽。现有方案无法有效压缩结构化数据（JSON、代码），且压缩后无法恢复原始信息。

## 旧范式 vs 新范式
- **旧做法**：开发者手动截断上下文、使用固定窗口大小、或接受高昂的 token 成本。压缩方法粗糙，常丢失关键信息。
- **新做法**：智能路由到专门压缩器（JSON → SmartCrusher，代码 → CodeCompressor，文本 → Kompress-base），缓存对齐以命中 KV cache，CCR 技术实现可逆压缩（原始数据本地缓存，LLM 按需检索）。支持跨代理内存去重和输出 token 削减。

## 生产力影响 (How)
节省 60-95% 输入 token，同时减少输出 token 浪费（5x 成本差异）。基准测试显示 GSM8K 精度保持 ±0.000，TruthfulQA 甚至提升 0.030。支持库模式、代理模式、MCP 服务器和 agent wrap 一键集成。

## 采用成本
安装简单：`pip install headroom-ai[all]`。三种模式：库集成（`from headroom import compress`）、代理模式（`headroom proxy --port 8787`）、一键包装（`headroom wrap claude`）。本地优先，数据不出本地。学习曲线低，兼容主流编码代理。

## 核心线索
- GitHub：https://github.com/chopratejas/headroom
- 来源：https://github.com/trending/python
- 发布时间：2026-06-19
