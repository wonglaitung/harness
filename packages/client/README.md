# Harness Client

Windows 桌面客户端，基于 Harness AI Agent SDK。

## 功能

- 对话界面：与 AI Agent 交互
- MCP 服务器管理：配置和管理 MCP 服务器
- 技能系统：加载和管理技能
- 工作目录：选择和切换工作目录

## 开发

### 安装依赖

```bash
# 在项目根目录
uv sync
```

### 运行客户端

```powershell
cd packages\client
uv run python -m harness_client
```

### 打包

```powershell
cd packages\client
uv run pyinstaller harness-client.spec
```

输出：`dist/HarnessClient.exe`

## 技术栈

- PyQt6 - GUI 框架
- qasync - 异步支持
- harness-sdk - AI Agent SDK
