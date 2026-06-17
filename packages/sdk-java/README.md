# Harness SDK Java

可内嵌的 AI Agent Harness 框架 - Java 实现

## 项目状态

🚧 **开发中** - 当前处于 Phase 1: 项目初始化

## 模块结构

```
harness-sdk-java/
├── harness-sdk-core/      # 核心模块（类型定义、接口）
├── harness-sdk-llm/       # LLM 客户端（Anthropic、OpenAI）
├── harness-sdk-mcp/       # MCP 协议集成
├── harness-sdk-tools/     # 内置工具
├── harness-sdk-memory/    # 记忆系统
├── harness-sdk-skills/    # 技能系统
├── harness-sdk-security/  # 安全模块
└── harness-sdk-all/       # 聚合模块（Shadow JAR）
```

## 构建

```bash
# 构建所有模块
./gradlew build

# 构建 Shadow JAR
./gradlew :harness-sdk-all:shadowJar
```

## 依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| anthropic-java | 2.40.1 | Anthropic Claude API |
| openai-java | 4.39.1 | OpenAI 兼容 API |
| mcp-java-sdk | 0.5.0 | MCP 协议 |
| jtokkit | 1.0.0 | Token 计数 |
| jackson | 2.17.0 | JSON 处理 |

## 文档

详细设计文档请见 [docs/](docs/) 目录。
