# Harness Client

Windows 桌面客户端，基于 Harness AI Agent SDK。

## 功能特性

- **对话界面** - 与 AI Agent 交互，支持流式输出
- **MCP 服务器管理** - 添加、配置、连接 MCP 服务器
- **技能系统** - 加载、创建、管理技能文件
- **工作目录** - 选择和切换工作目录
- **多模型支持** - 支持 Claude、OpenAI 及兼容 API

---

## Windows 配置指南

### 系统要求

- Windows 10/11
- Python 3.10+（推荐 3.11）
- uv 包管理器

### 步骤 1: 安装 Python

从官网下载安装：https://www.python.org/downloads/

验证安装：
```powershell
python --version
# 输出: Python 3.11.x
```

### 步骤 2: 安装 uv

```powershell
# 使用 PowerShell 安装
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

验证安装：
```powershell
uv --version
# 输出: uv 0.x.x
```

### 步骤 3: 克隆项目

```powershell
git clone https://github.com/wonglaitung/harness.git
cd harness
```

### 步骤 4: 安装依赖

```powershell
# 安装所有包（SDK + 客户端）
uv sync --all-packages
```

### 步骤 5: 运行客户端

**方式一：模块方式**
```powershell
cd packages\client
uv run python -m harness_client
```

**方式二：入口命令**
```powershell
# 在项目根目录
uv run harness-client

# 或在 packages\client 目录
cd packages\client
uv run harness-client
```

---

## 常见问题

### 问题 1: No module named 'harness_client.__main__'

确保已拉取最新代码：
```powershell
git pull
uv sync --all-packages
```

### 问题 2: 找不到 harness 模块

确保在项目根目录运行过：
```powershell
uv sync --all-packages
```

这会自动安装 SDK 和客户端到虚拟环境。

### 问题 3: PyQt6 安装失败

```powershell
# 手动安装 PyQt6
uv pip install PyQt6 qasync
```

### 问题 4: 缺少依赖

编辑 `packages/sdk/pyproject.toml`，添加缺失的依赖后重新运行：
```powershell
uv sync
```

### 问题 5: uv 命令找不到

重启 PowerShell 或手动添加到 PATH：
```powershell
$env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"
```

---

## 一键启动脚本

在项目根目录创建 `run.ps1` 文件：

```powershell
# run.ps1 - Windows 启动脚本

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "安装依赖..." -ForegroundColor Green
uv sync --all-packages

Write-Host "启动 Harness Client..." -ForegroundColor Green
uv run harness-client
```

运行方式：
```powershell
.\run.ps1
```

---

## 使用指南

### 配置 API

**方式一：界面配置**

1. 点击菜单 "设置" → "首选项"
2. 选择 Provider (`anthropic` 或 `openai`)
3. 输入 API Key
4. 如使用第三方 API，填写 Base URL
5. 选择模型

**方式二：环境变量**

```powershell
# OpenAI 兼容 API（如智谱 GLM）
$env:OPENAI_API_KEY = "your-api-key"
$env:OPENAI_BASE_URL = "https://api.example.com/v1"

# Anthropic API
$env:ANTHROPIC_API_KEY = "your-api-key"
```

**第三方 API 配置示例：**

| 字段 | 值 |
|------|---|
| Provider | `openai` |
| API Key | `bce-v3/ALTAKSP-...` |
| Base URL | `http://47.115.141.152:8080/v2/coding` |
| Model | `glm-5` |

### 添加 MCP 服务器

1. 在左侧边栏点击 "MCP 服务器" → "添加"
2. 选择传输方式：
   - **stdio**: 本地进程，需要填写命令和参数
   - **http**: 网络服务，需要填写 URL
3. 点击确定保存

**示例 - filesystem MCP：**

| 字段 | 值 |
|------|---|
| 名称 | `filesystem` |
| 传输方式 | `stdio` |
| 命令 | `npx` |
| 参数 | `-y, @anthropic/mcp-server-filesystem, C:\Users\YourName\Documents` |

### 加载技能

1. 点击 "技能列表" → "加载"
2. 选择包含 `.md` 技能文件的目录
3. 技能会自动加载到列表

**技能文件格式：**

```markdown
---
name: code-review
version: 1.0.0
description: 代码审查技能
triggers:
  keywords:
    - review
    - 审查
---

你是一个专业的代码审查专家...

```

### 开始对话

1. 在底部输入框输入消息
2. 按 Enter 或点击 "发送"
3. Agent 会自动调用工具完成任务

---

## 打包为 EXE

### 打包步骤

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

```python
# 输出文件名
name='HarnessClient',

# 是否显示控制台
console=False,

# 应用图标
icon='resources/icons/app.ico',

# 额外依赖模块
hiddenimports=[
    'qasync',
    'harness',
    ...
],
```

### 打包后目录结构

```
dist/
└── HarnessClient.exe    # 可执行文件（约 50-100MB）
```

---

## 项目结构

```
packages/client/
├── src/harness_client/
│   ├── __init__.py
│   ├── __main__.py          # 模块入口 (python -m harness_client)
│   ├── main.py              # 入口函数
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

---

## 开发

### 安装开发依赖

```powershell
uv sync --all-packages
```

### 运行测试

```powershell
# 测试 SDK
cd packages\sdk
PYTHONPATH=src uv run pytest

# 测试客户端
cd packages\client
uv run pytest
```

### 代码风格

```powershell
uv run ruff check src/
uv run ruff format src/
```

---

## 技术栈

| 组件 | 技术 |
|------|------|
| GUI 框架 | PyQt6 |
| 异步支持 | qasync |
| Agent SDK | harness-sdk |
| 打包工具 | PyInstaller |
| 包管理 | uv |

---

## 许可证

MIT License
