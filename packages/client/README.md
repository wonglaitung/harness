# Harness Client

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

基于 Harness AI Agent SDK 的跨平台桌面客户端。

---

## 快速开始

```powershell
# 1. 克隆项目
git clone https://github.com/wonglaitung/harness.git
cd harness

# 2. 安装依赖
uv sync --all-packages

# 3. 运行客户端
uv run harness-client
```

---

## 功能特性

| 功能 | 描述 |
|------|------|
| 💬 **对话界面** | 与 AI Agent 交互，支持 Markdown 渲染和流式输出 |
| 📐 **三栏布局** | 可折叠左侧边栏 + 中央对话 + 右侧面板（技能/MCP/文件树） |
| 🌐 **浏览器控制** | Agent 自动操作浏览器，支持 Edge/Chrome/Firefox |
| 🔌 **MCP 服务器** | 添加、配置、连接 MCP 服务器扩展能力 |
| 📝 **技能系统** | 加载、创建、管理技能文件，支持 `/` 自动补全 |
| 📁 **会话管理** | 多会话支持，历史记录持久化 |
| 🌐 **多模型支持** | 支持 Claude、OpenAI 及兼容 API |
| 📂 **统一配置** | 所有配置集中存储在 `~/.harness/` 目录 |
| ⚙️ **设置持久化** | 配置自动保存，重启后自动加载 |
| 🎨 **Hermes 暗色主题** | 现代化暗色 UI 风格 |

### 界面布局

```
┌─────────────────────────────────────────────────────────────┐
│  Header Bar (Logo + 标题 + 快捷操作)                          │
├────────┬──────────────────────────────┬─────────────────────┤
│ 左侧栏  │       中央对话区              │     右侧面板         │
│        │                              │                     │
│ 📁 会话 │  用户消息                     │ ▼ 技能              │
│   列表  │  ─────────────               │   ✓ skill-1        │
│        │  AI 响应 (Markdown)           │   ○ skill-2        │
│ ⚙ 设置  │  ─────────────               │                     │
│        │  输入框...                    │ ▼ MCP 服务器        │
│        │                              │   ● filesystem (已连接)│
│        │                              │   ○ github          │
│        │                              │                     │
│        │                              │ ▼ 工作区            │
│        │                              │   📁 src/           │
│        │                              │   📄 README.md      │
├────────┴──────────────────────────────┴─────────────────────┤
│  Status Bar                                                  │
└─────────────────────────────────────────────────────────────┘
```

- **左侧栏**：可折叠（56px/220px），包含会话列表和设置入口
- **右侧面板**：可折叠区块，显示技能、MCP 服务器状态、文件树

---

## 系统要求

| 平台 | 要求 |
|------|------|
| Windows | Windows 10/11, Python 3.10+ |
| macOS | macOS 11+, Python 3.10+ |
| Linux | Python 3.10+ |

**推荐**: Python 3.11 + [uv](https://docs.astral.sh/uv/) 包管理器

---

## 安装指南

### 1. 安装 Python

从 [python.org](https://www.python.org/downloads/) 下载安装。

```powershell
python --version  # 验证安装
```

### 2. 安装 uv

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. 安装项目依赖

```powershell
git clone https://github.com/wonglaitung/harness.git
cd harness
uv sync --all-packages
```

### 4. 运行客户端

```powershell
# 方式一：入口命令
uv run harness-client

# 方式二：模块方式
cd packages\client
uv run python -m harness_client
```

---

## 配置 API

### 界面配置

1. 菜单 **设置 → 首选项**
2. 选择 Provider (`anthropic` 或 `openai`)
3. 输入 API Key
4. 第三方 API 填写 Base URL
5. 选择或输入模型名称
6. 确定（自动保存）

**配置存储位置**: 
- 统一配置目录: `~/.harness/`（所有平台）
  - 设置文件: `~/.harness/settings.json`
  - MCP 配置: `~/.harness/mcp.json`
  - 用户技能: `~/.harness/skills/`

> **自动迁移**: 首次启动时，旧配置（`%LOCALAPPDATA%`、`~/Library`、`~/.config`）会自动迁移到 `~/.harness/`

### 环境变量配置

```powershell
# OpenAI / 兼容 API
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://api.example.com/v1"  # 可选

# Anthropic
export ANTHROPIC_API_KEY="your-api-key"
```

### 第三方 API 示例

| Provider | API Key | Base URL | Model |
|----------|---------|----------|-------|
| 智谱 GLM | `bce-v3/...` | `https://open.bigmodel.cn/api/paas/v4/` | `glm-5` |
| DeepSeek | `sk-...` | `https://api.deepseek.com/v1` | `deepseek-chat` |
| Ollama | `ollama` | `http://localhost:11434/v1` | `llama3` |

---

## 使用指南

### MCP 服务器

MCP (Model Context Protocol) 服务器可扩展 Agent 能力，提供外部工具访问。

#### 添加服务器

1. 右侧面板 **MCP 服务器 → + 添加服务器**
2. 填写配置：
   - 名称：服务器标识
   - 传输方式：`stdio` 或 `sse`
   - 命令/URL：启动命令或服务器地址
   - 参数：命令行参数（逗号分隔）
   - 环境变量：可选的环境变量
3. 确定保存

#### 连接/断开服务器

- 点击服务器项的 **连接** 或 **断开** 按钮
- 双击服务器项快速切换连接状态

#### 配置存储位置

- 统一配置目录: `~/.harness/mcp.json`（所有平台）

> MCP 配置保存在用户目录，所有项目共享。

#### 示例配置

**filesystem MCP（本地文件访问）**:

| 字段 | 值 |
|------|---|
| 名称 | `filesystem` |
| 传输方式 | `stdio` |
| 命令 | `npx` |
| 参数 | `-y, @anthropic/mcp-server-filesystem, /path/to/dir` |

**GitHub MCP**:

| 字段 | 值 |
|------|---|
| 名称 | `github` |
| 传输方式 | `stdio` |
| 命令 | `npx` |
| 参数 | `-y, @anthropic/mcp-server-github` |
| 环境变量 | `GITHUB_TOKEN=ghp_xxxx` |

**SSE 远程服务器**:

| 字段 | 值 |
|------|---|
| 名称 | `remote-api` |
| 传输方式 | `sse` |
| URL | `http://localhost:8080/sse` |

### 浏览器控制

浏览器控制功能允许 Agent 自动操作浏览器，执行网页导航、点击、输入等操作。

#### 快速开始

**1. 启动浏览器**

点击左侧侧边栏的 **"浏览器"** 按钮：

```
┌──────────────┐
│  对话        │
│  排程        │
│  ● 浏览器    │  ← 点击启动（绿色圆点表示运行中）
│  设置        │
└──────────────┘
```

浏览器会在独立窗口中打开，用户可实时观看 Agent 操作。

**2. 使用浏览器**

浏览器启动后，Agent 自动获得 7 个浏览器工具：

| 工具 | 功能 |
|------|------|
| `browser_navigate` | 导航到 URL |
| `browser_click` | 点击元素 |
| `browser_type` | 输入文本 |
| `browser_extract` | 提取页面内容 |
| `browser_screenshot` | 截图 |
| `browser_wait` | 等待元素加载 |
| `browser_close` | 关闭浏览器 |

**示例对话**：

```
用户: 打开百度搜索 "MCP protocol"
Agent: [调用 browser_navigate, browser_type, browser_click]
       已在百度搜索 "MCP protocol"，找到了相关结果...
```

**3. 关闭浏览器**

两种方式关闭：

- **状态条关闭**：点击输入框上方状态条的 `×` 按钮
- **侧边栏关闭**：再次点击侧边栏的 **"● 浏览器"** 按钮

#### 配置选项

打开 **设置 → 浏览器** 标签页：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| 浏览器类型 | msedge（推荐）/ chrome / chromium / firefox | msedge |
| 无头模式 | 后台运行，不显示窗口 | 关闭 |
| 自动截图 | 每次操作后自动截图（审计） | 开启 |
| 超时时间 | 页面加载超时（毫秒） | 30000 |

**浏览器类型建议**：

| 类型 | 适用场景 |
|------|---------|
| `msedge` | Windows 企业环境，系统自带，**推荐** |
| `chrome` | 需要已安装 Google Chrome |
| `chromium` | 跨平台一致性，需运行 `playwright install` |
| `firefox` | 需运行 `playwright install` |

#### 首次使用

如果提示 **"Playwright 未安装"**：

```powershell
pip install playwright
playwright install
```

#### 工作流程

```
用户点击 "浏览器" 按钮
        ↓
浏览器窗口打开（独立窗口）
        ↓
7 个浏览器工具注入 Agent
        ↓
状态条显示 "浏览器工具已激活"
        ↓
用户发送指令（如 "打开百度"）
        ↓
Agent 调用浏览器工具执行操作
        ↓
用户可实时观看浏览器操作
        ↓
点击关闭按钮 → 浏览器关闭
```

### 技能系统

技能是可复用的提示词模板，当用户输入匹配触发条件时自动激活。

#### 技能目录

客户端自动扫描以下目录（按优先级排序）：

| 目录 | 优先级 | 说明 |
|------|--------|------|
| `~/.harness/skills/` | 最高 | 用户级（所有项目共享，UI 创建默认保存位置） |
| `~/.harness/shared-skills/` | 高 | 共享技能 |
| `./.agent/skills/` | 中 | 项目级 |
| `./skills/` | 低 | 项目级（备选） |

> **技能自动补全**: 输入 `/` 可触发技能名称自动补全

#### 创建技能

**方式一：界面创建**

1. 右侧面板 **技能 → + 新建技能**
2. 填写名称、描述、触发条件、内容
3. 保存到 `.agent/skills/` 目录

**方式二：手动创建文件**

在技能目录下创建 `.md` 文件：

```markdown
---
name: code-review
version: 1.0.0
author: Your Name
description: 代码审查技能
triggers:
  keywords:
    - review
    - 审查
    - 检查代码
  patterns:
    - "review\\s+\\w+"
---

# Code Review Skill

你是一个专业的代码审查专家。

## 检查步骤

1. **代码风格**: 检查命名规范、缩进、注释
2. **逻辑正确性**: 检查边界条件、错误处理
3. **性能**: 识别潜在的性能问题
```

#### 编辑技能

双击技能列表中的技能项，打开编辑对话框修改。

#### 触发机制

- **关键词匹配**：用户输入包含任一关键词（不区分大小写）
- **正则匹配**：用户输入匹配任一正则表达式

匹配的技能内容会自动注入到 system prompt 中。

---

## 故障排除

### 程序崩溃 / 事件循环错误

**症状**: Windows 上启动或运行时崩溃，出现 `ProactorEventLoop` 错误。

**原因**: Windows 默认事件循环与 qasync 不兼容。

**解决**: 已自动处理，确保使用最新代码：

```powershell
git pull && uv sync --all-packages
```

### 找不到模块

```powershell
# 确保在项目根目录运行过
uv sync --all-packages
```

### 发送消息无响应

从命令行启动查看日志：

```powershell
cd packages\client
uv run python -m harness_client
```

检查 API 配置是否正确。

### 更多问题

| 问题 | 解决方案 |
|------|---------|
| `uv` 命令找不到 | 重启终端或添加到 PATH |
| PyQt6 安装失败 | `uv pip install PyQt6 qasync` |
| 缺少依赖 | 编辑 `pyproject.toml` 后 `uv sync` |

---

## 打包为 EXE

### 前提条件

- Windows 10/11
- Python 3.10+
- 已安装项目依赖（`uv sync --all-packages`）

### 打包步骤

```powershell
cd packages\client

# 1. 安装 PyInstaller（dev 可选依赖）
uv sync --extra dev

# 2. 执行打包
uv run python build.py

# 输出: dist/HarnessClient.exe
```

### 清理构建产物

```powershell
uv run python build.py --clean
```

清理 `build/`、`dist/`、`__pycache__/` 及 `.spec.bak` 文件。

### 打包配置

打包由 `harness-client.spec` 控制，主要配置：

| 配置 | 说明 |
|------|------|
| `console=False` | 隐藏控制台窗口 |
| `upx=True` | UPX 压缩减小体积 |
| `icon` | 应用图标 `resources/icons/app.ico` |
| `datas` | 包含 `resources/` 和 SDK 源码 |
| `hiddenimports` | PyQt6/SDK/LLM 等隐式依赖 |

> **注意**：如果提示找不到 UPX，可下载 [UPX](https://upx.github.io/) 解压后将 `upx.exe` 放入 `packages/client/` 目录，或将 `upx=True` 改为 `upx=False` 跳过压缩。

---

## 开发

```powershell
# 安装开发依赖
uv sync --all-packages

# 代码检查
uv run ruff check packages/client/src/

# 代码格式化
uv run ruff format packages/client/src/
```

### 项目结构

```
packages/client/
├── src/harness_client/
│   ├── __main__.py          # 模块入口
│   ├── main.py              # 入口函数
│   ├── app.py               # QApplication
│   ├── _win_event_loop.py   # Windows 事件循环兼容
│   ├── ui/                  # UI 组件
│   ├── controllers/         # 控制器
│   └── utils/               # 工具模块
├── resources/
│   ├── styles/main.qss      # 样式表
│   └── templates/           # 技能模板
├── pyproject.toml
├── harness-client.spec      # PyInstaller 配置
└── build.py                 # 打包脚本
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

[MIT License](LICENSE)
