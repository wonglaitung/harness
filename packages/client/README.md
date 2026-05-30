# Harness Client

Windows 桌面客户端，基于 Harness AI Agent SDK。

## 功能特性

- **对话界面** - 与 AI Agent 交互，支持流式输出
- **MCP 服务器管理** - 添加、配置、连接 MCP 服务器
- **技能系统** - 加载、创建、管理技能文件
- **工作目录** - 选择和切换工作目录
- **多模型支持** - 支持 Claude、OpenAI 及兼容 API

## 系统要求

- Windows 10/11
- Python 3.10+
- 推荐使用 uv 包管理器

## 安装

### 从源码安装

```powershell
# 克隆仓库
git clone https://github.com/wonglaitung/harness.git
cd harness

# 安装依赖
uv sync
```

### 运行客户端

```powershell
cd packages\client
uv run python -m harness_client
```

## 使用指南

### 配置 API

1. 点击菜单 "设置" -> "首选项"
2. 选择 Provider (anthropic/openai)
3. 输入 API Key
4. 如使用第三方 API，填写 Base URL
5. 选择模型

### 添加 MCP 服务器

1. 在左侧边栏点击 "MCP 服务器" -> "添加"
2. 选择传输方式：
   - **stdio**: 本地进程，需要填写命令和参数
   - **http**: 网络服务，需要填写 URL
3. 点击确定保存

### 加载技能

1. 点击 "技能列表" -> "加载"
2. 选择包含 `.md` 技能文件的目录
3. 技能会自动加载到列表

### 开始对话

1. 在底部输入框输入消息
2. 按 Enter 或点击 "发送"
3. Agent 会自动调用工具完成任务

## 打包为 EXE

```powershell
cd packages\client

# 安装 PyInstaller
uv pip install pyinstaller

# 打包
uv run python build.py

# 输出文件
# dist/HarnessClient.exe
```

### 打包配置

编辑 `harness-client.spec` 自定义打包选项：

- `name`: 输出文件名
- `icon`: 应用图标
- `console`: 是否显示控制台
- `hiddenimports`: 额外依赖模块

## 项目结构

```
packages/client/
├── src/harness_client/
│   ├── __init__.py
│   ├── main.py              # 入口
│   ├── app.py               # QApplication
│   ├── ui/                  # UI 组件
│   │   ├── main_window.py   # 主窗口
│   │   ├── chat_panel.py    # 对话面板
│   │   ├── sidebar.py       # 侧边栏
│   │   ├── settings_dialog.py
│   │   ├── mcp_panel.py
│   │   └── skill_dialog.py
│   └── controllers/         # 控制器
│       ├── chat_controller.py
│       ├── mcp_controller.py
│       └── skill_controller.py
├── resources/
│   ├── icons/
│   ├── styles/main.qss
│   └── templates/
├── tests/
├── pyproject.toml
├── harness-client.spec
└── build.py
```

## 开发

### 安装开发依赖

```powershell
uv sync --all-packages
```

### 运行测试

```powershell
uv run pytest
```

### 代码风格

```powershell
uv run ruff check src/
uv run ruff format src/
```

## 技术栈

| 组件 | 技术 |
|------|------|
| GUI 框架 | PyQt6 |
| 异步支持 | qasync |
| Agent SDK | harness-sdk |
| 打包工具 | PyInstaller |
| 包管理 | uv |

## 许可证

MIT License
