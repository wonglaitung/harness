# Harness Client 文档索引

## 概述

Harness Client 是 Harness SDK 的 Windows 桌面客户端，提供友好的图形用户界面。

**核心公式**：`Client = PyQt6 UI + Harness SDK + Controllers`

## 文档目录

| 文档 | 说明 |
|------|------|
| [01-overview.md](./01-overview.md) | 项目概述与架构总览 |
| [02-ui-components.md](./02-ui-components.md) | UI 组件详解 |
| [03-controllers.md](./03-controllers.md) | 控制器详解 |
| [04-configuration.md](./04-configuration.md) | 配置与部署 |
| [05-client-lessons.md](./05-client-lessons.md) | **开发经验总结（推荐阅读）** |

## 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/wonglaitung/harness.git
cd harness

# 安装所有包
uv sync --all-packages
```

### 运行

```powershell
# Windows
cd packages\client
uv run python -m harness_client
```

### 配置

1. 首次运行时点击右上角 ⚙️ 打开设置
2. 配置 Provider 和 API Key
3. 开始对话

## 核心功能

### 三栏布局

- **左侧栏**：会话列表、排程入口（可折叠）
- **中央区**：对话面板（Markdown 渲染 + 流式输出）
- **右侧面板**：记忆/技能/MCP 服务器/文件树（可折叠区块）

### 多模态消息

支持上传图片和文档，发送多模态消息：

- **图片格式**：PNG, JPEG, GIF, WebP（≤ 10MB）
- **文档格式**：PDF, TXT（≤ 10MB）
- **预览功能**：图片缩略图、文档图标
- **快捷操作**：一键移除附件

使用方式：
1. 点击输入框左侧的 📎 按钮
2. 选择图片或文档文件
3. 输入文本说明（可选）
4. 发送消息

### 全局记忆

- 记忆文件：`~/.harness/MEMORY.md`
- 自动注入到 Agent 上下文
- 修改后即时生效

### 排程管理

- 配置文件：`~/.harness/schedules.json`
- 支持 Cron 表达式和固定间隔
- 可视化创建、编辑、启停排程
- 下次运行时间预览

### MCP 集成

- 配置文件：`~/.harness/mcp.json`
- 可视化管理服务器连接
- 工具自动加载到 Agent

### 技能系统

- 支持 `/` 自动补全
- 根据关键词自动匹配
- 可视化创建和编辑技能

## 架构概览

```
┌─────────────────────────────────────────────┐
│              UI Layer (PyQt6)                │
│  Sidebar  │  ChatPanel  │  RightPanel       │
└────────────────────┬────────────────────────┘
                     │
┌────────────────────┴────────────────────────┐
│            Controller Layer                  │
│  ChatController │ MCPController │ ...       │
│  SessionManager (Single Source of Truth)    │
└────────────────────┬────────────────────────┘
                     │
┌────────────────────┴────────────────────────┐
│              Harness SDK                     │
│  AgentHarness │ MCPManager │ SkillRegistry  │
└─────────────────────────────────────────────┘
```

## 配置目录

```
~/.harness/
├── settings.json     # 应用设置
├── mcp.json          # MCP 服务器配置
├── schedules.json    # 排程配置
├── MEMORY.md         # 全局记忆
└── skills/           # 技能目录
```

## 开发指南

### 异步操作

使用 `@asyncSlot` 装饰器：

```python
from qasync import asyncSlot

@asyncSlot(str)
async def _on_message_sent(self, message: str):
    async for chunk in self.controller.send_message(message):
        ...
```

### 信号机制

```python
# 定义信号
message_sent = pyqtSignal(str)

# 连接信号
self.chat_panel.message_sent.connect(self._on_message_sent)

# 发射信号
self.message_sent.emit(message)
```

### 单一数据源

所有会话状态存储在 `SessionManager` 中，UI 只负责渲染。

## 相关资源

- [Harness SDK 文档](../../sdk/docs/)
- [编程技能规范](../../sdk/docs/programmer_skill.md)
- [项目经验教训](../../../lessons.md)
- [PyQt6 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [qasync GitHub](https://github.com/CabbageDevelopment/qasync)
