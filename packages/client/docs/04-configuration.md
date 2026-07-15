# 04 - 配置与部署

## 概述

客户端使用统一的配置目录 `~/.harness` 存储所有配置文件。本章详细介绍配置管理和部署流程。

## 配置目录

### 目录结构

```
~/.harness/
├── settings.json        # 应用设置（API Key、模型等）
├── mcp.json             # MCP 服务器配置
├── schedules.json       # 排程配置
├── MEMORY.md            # 全局记忆文件
├── sessions/            # 会话持久化目录
│   ├── abc12345.json    # 单个会话文件
│   ├── def67890.json
│   └── ...
├── skills/              # 全局技能目录
│   ├── code-review/
│   │   └── skill.md
│   └── md-to-word/
│       ├── skill.md
│       └── scripts/
│           └── md_to_word.py
└── audit/               # 审计日志（可选）
    └── 2026-06-07.log
```

### 配置文件说明

| 文件/目录 | 格式 | 说明 | 管理 UI |
|-----------|------|------|---------|
| `settings.json` | JSON | 应用设置 | SettingsDialog |
| `mcp.json` | JSON | MCP 服务器列表 | RightPanel MCP Section |
| `schedules.json` | JSON | 排程配置 | ScheduleDialog |
| `MEMORY.md` | Markdown | 全局记忆 | RightPanel Memory Section |
| `sessions/*.json` | JSON | 会话历史（自动持久化） | Sidebar Session List |
| `skills/*.md` | Markdown | 技能定义 | RightPanel Skills Section |

## settings.json

### 配置项

```json
{
  "provider": "anthropic",
  "api_key": "sk-ant-...",
  "base_url": "",
  "model": "claude-sonnet-4-6",
  "context_window": "auto",
  "max_iterations": 10,
  "temperature": 0.3,
  "tool_result_role": "tool",
  "system_prompt": "你是一个有帮助的 AI 助手...",
  "stream_enabled": true,
  "auto_update_memory": true,
  "theme_mode": "auto"
}
```

### 配置项说明

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `provider` | string | `"anthropic"` | LLM 提供商 |
| `api_key` | string | `""` | API 密钥 |
| `base_url` | string | `""` | 自定义 API 端点 |
| `model` | string | `"claude-sonnet-4-6"` | 模型名称 |
| `context_window` | string | `"auto"` | 上下文窗口大小 |
| `max_iterations` | int | `10` | 最大迭代次数 |
| `temperature` | float | `0.3` | 温度参数 |
| `tool_result_role` | string | `"tool"` | 工具结果角色 |
| `system_prompt` | string | `""` | 系统提示 |
| `stream_enabled` | bool | `true` | 是否启用流式输出 |
| `auto_update_memory` | bool | `true` | 允许 Agent 自主更新 Core Memory |
| `theme_mode` | string | `"auto"` | 主题模式：`auto`/`light`/`dark` |

### auto_update_memory 设置

`auto_update_memory` 控制 Agent 是否能自主调用 `UpdateCoreMemoryTool` 更新 Core Memory：

- **`true`（默认）**：Agent 可以在对话过程中自主判断并更新记忆
- **`false`**：禁用 Agent 自主更新，用户需手动编辑 MEMORY.md

```python
# ChatConfig 中使用
config = ChatConfig(
    auto_update_memory=True,  # 允许 Agent 自主更新记忆
)

# 在 ChatController 中条件性添加工具
if self.config.auto_update_memory:
    tools.append(UpdateCoreMemoryTool())
```


### 使用第三方 API

```json
{
  "provider": "openai",
  "api_key": "your-api-key",
  "base_url": "https://api.your-provider.com/v1",
  "model": "your-model-name"
}
```

### 浏览器配置

从 v1.5.0 开始，支持浏览器自动化配置：

```json
{
  "browser_type": "msedge",
  "browser_headless": false,
  "browser_screenshot": true,
  "browser_timeout": 30000
}
```

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `browser_type` | string | `"msedge"` | 浏览器类型：msedge/chrome/chromium/firefox |
| `browser_headless` | bool | `false` | 无头模式（后台运行，不显示窗口） |
| `browser_screenshot` | bool | `true` | 每次操作后自动截图（审计） |
| `browser_timeout` | int | `30000` | 页面加载超时时间（毫秒） |

**浏览器类型说明**：

| 类型 | 说明 | 适用场景 |
|------|------|---------|
| `msedge` | Microsoft Edge | Windows 企业环境，系统自带，推荐 |
| `chrome` | Google Chrome | 需要 Chrome 已安装 |
| `chromium` | Playwright 自带 | 跨平台一致性，需 `playwright install` |
| `firefox` | Playwright 自带 | 需 `playwright install` |

## mcp.json

### 配置格式

```json
{
  "servers": [
    {
      "name": "filesystem",
      "transport": "stdio",
      "command": "mcp-filesystem",
      "args": ["--root", "/path/to/workspace"],
      "env": {}
    },
    {
      "name": "github",
      "transport": "stdio",
      "command": "mcp-github",
      "args": [],
      "env": {
        "GITHUB_TOKEN": "ghp_xxx"
      }
    },
    {
      "name": "brave-search",
      "transport": "stdio",
      "command": "mcp-brave-search",
      "args": [],
      "env": {
        "BRAVE_API_KEY": "your-key"
      }
    }
  ]
}
```

### 服务器配置说明

| 配置项 | 类型 | 说明 |
|--------|------|------|
| `name` | string | 服务器名称（唯一标识） |
| `transport` | string | 传输方式：`"stdio"` 或 `"http"` |
| `command` | string | 启动命令（stdio 传输） |
| `args` | array | 命令参数 |
| `env` | object | 环境变量 |

## schedules.json

### 配置格式

```json
{
  "schedules": [
    {
      "id": "schedule_20260628120000",
      "name": "每日报告",
      "goal": "生成每日工作总结并发送到 Slack",
      "trigger_type": "cron",
      "trigger_value": "0 9 * * *",
      "enabled": true,
      "max_iterations": 50,
      "timeout_seconds": 3600,
      "skills": [],
      "created_at": "2026-06-28T12:00:00",
      "last_run": null,
      "next_run": "2026-06-29T09:00:00",
      "run_count": 0,
      "status": "idle",
      "error_message": ""
    },
    {
      "id": "schedule_20260628130000",
      "name": "健康检查",
      "goal": "检查系统健康状态",
      "trigger_type": "interval",
      "trigger_value": "300",
      "enabled": true,
      "max_iterations": 20,
      "timeout_seconds": 600,
      "skills": [],
      "created_at": "2026-06-28T13:00:00",
      "status": "running"
    }
  ]
}
```

### 配置项说明

| 配置项 | 类型 | 说明 |
|--------|------|------|
| `id` | string | 唯一标识（自动生成） |
| `name` | string | 排程名称 |
| `goal` | string | 任务目标描述 |
| `trigger_type` | string | 触发类型：`"cron"` 或 `"interval"` |
| `trigger_value` | string | Cron 表达式或间隔秒数 |
| `enabled` | bool | 是否启用 |
| `max_iterations` | int | 最大迭代次数 |
| `timeout_seconds` | int | 超时时间（秒） |
| `skills` | array | 关联技能列表 |
| `status` | string | 当前状态：`idle`/`running`/`paused`/`error` |

### Cron 表达式格式

```
┌──────── 分钟 (0-59)
│ ┌────── 小时 (0-23)
│ │ ┌──── 日 (1-31)
│ │ │ ┌── 月 (1-12)
│ │ │ │ ┌ 星期 (0-6, 0=Sunday)
│ │ │ │ │
* * * * *
```

常用模式：
| 表达式 | 说明 |
|--------|------|
| `*/5 * * * *` | 每 5 分钟 |
| `0 * * * *` | 每小时整点 |
| `0 9 * * *` | 每天 9:00 |
| `0 9 * * 1-5` | 工作日 9:00 |
| `0 0 1 * *` | 每月 1 日 |

## MEMORY.md

### 文件格式

```markdown
# MEMORY.md

## User Profile
- 使用 Windows 操作系统
- 偏好 Python 语言
- 使用 VS Code 编辑器

## Key Decisions
- 2026-06-07: 选择 SQLite 作为会话存储

## Learned Patterns
- 用户喜欢详细的代码示例
- 用户偏好中文回复

## Project Context
- 项目使用 Python 3.11+
- 代码风格遵循 Black 格式化
```

### 记忆类别

| 类别 | 章节标题 | 说明 |
|------|----------|------|
| `USER_PROFILE` | User Profile | 用户角色、偏好、技能 |
| `KEY_DECISIONS` | Key Decisions | 重要技术决策 |
| `LEARNED_PATTERNS` | Learned Patterns | Agent 学习到的模式 |
| `PROJECT_CONTEXT` | Project Context | 项目特定约定 |

### 自动注入

MEMORY.md 内容在每次 `run()` 调用时自动注入到 system prompt。

## 技能文件

### 文件格式

```markdown
---
name: code-review
description: Review code for issues and improvements
tools: [read, grep, glob]
triggers:
  keywords: [review, 检查, 审查]
---

# Code Review Skill

You are an expert code reviewer. Your task is to:
1. Read the code files carefully
2. Identify bugs, security issues, performance problems
3. Provide actionable suggestions

## Guidelines
- Focus on correctness first
- Always check for security vulnerabilities
```

### 技能目录结构

```
skills/
├── code-review/
│   └── skill.md           # 技能定义
└── md-to-word/
    ├── skill.md           # 技能定义
    └── scripts/           # 辅助脚本
        └── md_to_word.py
    └── requirements.txt   # 依赖（可选）
```

## 配置迁移

### 旧版本迁移

客户端支持从旧版本配置目录自动迁移：

```python
def migrate_old_config() -> None:
    """从旧位置迁移配置到 ~/.harness"""
    old_dir = get_old_config_dir()
    new_dir = get_config_dir()
    
    if not old_dir.exists():
        return
    
    # 迁移 settings.json
    old_settings = old_dir / "settings.json"
    new_settings = new_dir / "settings.json"
    if old_settings.exists() and not new_settings.exists():
        shutil.copy2(old_settings, new_settings)
    
    # 迁移其他文件...
```

### 旧配置位置

| 系统 | 旧位置 |
|------|--------|
| Windows | `%LOCALAPPDATA%\HarnessClient` |
| macOS | `~/Library/Application Support/HarnessClient` |
| Linux | `~/.config/HarnessClient` |

## 运行客户端

### 开发模式

```powershell
# Windows
cd packages\client
uv run python -m harness_client
```

```bash
# Linux/macOS
cd packages/client
uv run python -m harness_client
```

### 日志级别

客户端默认使用 DEBUG 日志级别：

```python
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
    ],
)
```

可在生产环境中调整：

```python
level=logging.INFO  # 生产环境推荐
```

## 打包为 EXE

### PyInstaller 配置

`harness-client.spec`:

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = pyi_crypto.Cipher("pyi")

a = Analysis(
    ['src/harness_client/__main__.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('src/harness_client/resources', 'harness_client/resources'),
    ],
    hiddenimports=[
        'qasync',
        'markdown',
        'markdown.extensions.fenced_code',
        'markdown.extensions.codehilite',
        'markdown.extensions.tables',
    ],
    hookspath=['hooks'],
    runtime_hooks=[],
    excludes=['tkinter'],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='HarnessClient',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

### 构建命令

```powershell
cd packages\client
uv run python build.py
```

### 输出

```
dist/
└── HarnessClient.exe   # 可执行文件
```

## 部署注意事项

### 1. Python 环境

打包后的 EXE 不依赖 Python 环境，可直接运行。

### 2. 配置文件

首次运行时会在 `~/.harness` 创建配置目录。

### 3. MCP 服务器

MCP 服务器需要单独安装：

```powershell
# 安装常用 MCP 服务器
pip install mcp-filesystem
pip install mcp-github
```

### 4. 技能脚本

技能中的 Python 脚本需要正确配置路径：

```markdown
---
name: md-to-word
---

# MD to Word

执行命令：
```bash
python .harness/skills/md-to-word/scripts/md_to_word.py <input.md>
```

技能脚本在项目目录 `.harness/skills/` 下。

## 故障排除

### 常见问题

#### 1. API Key 未配置

```
未配置 API Key。请在设置中配置 API Key。
```

**解决**：打开 Settings 对话框，配置 API Key。

#### 2. MCP 服务器连接失败

```
Error: 'mcp-filesystem' is not recognized as a command
```

**解决**：安装对应的 MCP 服务器包。

#### 3. 流式输出卡住

**原因**：可能是在非主线程执行异步操作。

**解决**：确保使用 `@asyncSlot` 装饰器。

#### 4. 程序崩溃无提示

**原因**：在 QThread 中创建了新的 event loop。

**解决**：检查异步代码，确保所有 async 操作在主线程执行。

### 日志查看

开发模式下日志输出到 stderr。打包后可添加日志文件：

```python
logging.basicConfig(
    handlers=[
        logging.FileHandler('~/.harness/client.log'),
        logging.StreamHandler(sys.stderr),
    ],
)
```

## 下一步

- [01-overview.md](./01-overview.md) - 了解客户端整体架构
- [02-ui-components.md](./02-ui-components.md) - 了解 UI 组件设计
- [03-controllers.md](./03-controllers.md) - 了解控制器层设计（BrowserController）