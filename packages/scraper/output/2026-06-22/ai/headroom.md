# Headroom

## 技术定义 (What)
Headroom 是首个明确定义的 AI Agent 上下文压缩层（Context Compression Layer）。它在工具输出、日志、RAG 文档、对话历史等内容发送到 LLM 之前进行智能压缩，实现 60-95% 的 token 节省，同时保持答案准确性。支持库模式、代理模式、MCP 服务器三种集成方式。

## 行业痛点 (Why)
AI Agent 在处理大量上下文时面临 token 成本高昂的问题：代码搜索结果可能产生 17,765 tokens，SRE 调试日志可达 65,694 tokens。现有方案要么截断信息（丢失关键细节），要么直接发送（成本失控）。开发者缺乏一种既保留完整信息又降低成本的系统化方案。

## 旧范式 vs 新范式
- **旧做法**：**旧做法**：
1. 直接发送完整上下文 → 高 token 成本
2. 简单截断或摘要 → 丢失关键信息
3. 手动筛选内容 → 效率低、易出错
4. 各 agent 重复存储相同信息 → 冗余浪费
- **新做法**：**新做法**：
1. 智能压缩层：ContentRouter 自动识别内容类型（JSON/代码/文本），选择最优压缩算法
2. 可逆压缩（CCR）：缓存原始内容，LLM 可按需检索
3. 跨 Agent 内存：共享存储，自动去重
4. 输出 token 优化：压缩模型回复内容，而不只是输入
5. 学习式精简：`headroom learn` 从历史会话学习用户偏好的精简程度

## 生产力影响 (How)
**实际节省**：
- 代码搜索：17,765 → 1,408 tokens（节省 92%）
- SRE 调试：65,694 → 5,118 tokens（节省 92%）
- GitHub issue 分类：节省 73%
- 准确性保持：GSM8K 0.870 → 0.870（无损失）

**对开发者价值**：
1. 即插即用：`headroom wrap claude` 一行命令集成
2. 零代码修改：代理模式支持任何 LLM API
3. 多语言支持：Python + TypeScript
4. 本地优先：数据不离开本地环境

## 采用成本
**时间成本**：5-10 分钟（安装 + 配置）
**金钱成本**：开源免费
**学习曲线**：低（提供详细文档 + llms.txt）
**系统要求**：Python 3.10+ 或 Node.js 18+

## 核心线索
- GitHub：https://github.com/chopratejas/headroom
- 来源：https://github.com/trending/python
- 发布时间：2026-06-22
