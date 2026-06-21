# Hermes Agent

## 技术定义 (What)
Hermes Agent 是 Nous Research 开发的自我改进型 AI Agent，核心创新是**闭环学习系统**（Closed Learning Loop）：Agent 从经验中创建技能、在使用中改进技能、自动持久化知识、搜索历史对话、跨会话构建用户模型。支持多模型切换、多平台部署（Telegram/Discord/Slack/Signal/WhatsApp）、服务器化运行。

## 行业痛点 (Why)
现有 AI Agent 存在三大学习障碍：
1. **无记忆积累**：每次对话从零开始，无法从历史经验中学习
2. **技能不可复用**：完成复杂任务后，经验无法沉淀为可复用能力
3. **用户模型缺失**：无法理解用户偏好，每次交互需要重新调整
4. **平台锁定**：Agent 只能在单一环境运行（如本地 CLI）
5. **成本不透明**：无法在低成本基础设施上运行

## 旧范式 vs 新范式
- **旧做法**：**旧做法**：
1. 无状态对话 → 每次重新开始
2. 手动记录笔记 → 知识难以结构化
3. 固定技能集 → 无法自主扩展
4. 单平台运行 → 笔记本电脑绑定
5. 高成本运行 → GPU 集群或本地资源独占
- **新做法**：**新做法**：
1. **自主技能创建**：复杂任务后自动生成可复用技能
2. **技能自改进**：使用过程中持续优化
3. **Agent 策展记忆**：定期 nudges 持久化关键知识
4. **FTS5 会话搜索**：跨会话召回相关对话（带 LLM 总结）
5. **Honcho 方言用户建模**：深度理解用户偏好
6. **多平台网关**：Telegram/Discord/Slack/Signal/WhatsApp/Email
7. **服务器化运行**：$5 VPS 或 GPU 集群，Modal/Daytona 无服务器持久化

## 生产力影响 (How)
**典型应用场景**：
- 长期项目协作：跨周/月的持续工作
- 自动化任务：cron 定时报告、备份、审计
- 多人协作：团队共享 agent 实例
- 远程访问：Telegram 控制 VPS 上的 agent

**对开发者价值**：
1. 一键安装：curl 脚本自动配置所有依赖
2. 多模型支持：200+ 模型（OpenRouter/Nous Portal/NVIDIA NIM/小米 MiMo 等）
3. 研究就绪：轨迹生成和压缩，用于训练下一代工具调用模型
4. 生产级部署：Docker/SSH/Singularity/Modal/Daytona 六种后端

## 采用成本
**时间成本**：5-10 分钟（一键安装）
**金钱成本**：
- 开源免费
- Nous Portal 订阅：涵盖模型 + Web 搜索 + 图像生成 + TTS + 云浏览器
- 自带模型 API：按使用付费
**学习曲线**：低（详细文档 + 多语言支持）
**系统要求**：Python 3.11+ / Node.js / FFmpeg

## 核心线索
- GitHub：https://github.com/NousResearch/hermes-agent
- 来源：https://github.com/trending/python
- 发布时间：2026-06-22
