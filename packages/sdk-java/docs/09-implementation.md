# 09 - 实施路线图

## 概述

本文档说明 Harness SDK Java 版本的实施计划和里程碑。

## 阶段划分

```
Phase 0: 项目初始化 (1 周)
    ↓
Phase 1: 核心框架 (2 周)
    ↓
Phase 2: 工具系统 (2 周)
    ↓
Phase 3: MCP 集成 (1 周)
    ↓
Phase 4: 记忆系统 (1 周)
    ↓
Phase 5: 安全模块 (1 周)
    ↓
Phase 6: 测试覆盖 (2 周)
    ↓
Phase 7: 文档完善 (1 周)
    ↓
Phase 8: 发布准备 (1 周)
```

## Phase 0: 项目初始化

### 目标

- 搭建项目结构
- 配置构建系统
- 验证依赖兼容性

### 任务清单

- [ ] 创建 Monorepo 结构
  ```
  harness-java/
  ├── harness-sdk-core/
  ├── harness-sdk-anthropic/
  ├── harness-sdk-mcp/
  ├── harness-sdk-tools/
  ├── harness-sdk-memory/
  ├── harness-sdk-security/
  └── harness-sdk-all/
  ```

- [ ] 配置 Gradle
  - 根项目 build.gradle.kts
  - 各模块 build.gradle.kts
  - Shadow JAR 配置

- [ ] 验证依赖
  - Anthropic Java SDK 集成测试
  - MCP Java SDK 集成测试
  - jtokkit 精度验证

- [ ] CI/CD 配置
  - GitHub Actions 工作流
  - 自动测试
  - 自动构建 JAR

### 交付物

- 可编译的项目骨架
- CI/CD 流水线
- 依赖兼容性报告

## Phase 1: 核心框架

### 目标

- 实现核心类和接口
- 实现 Agent Loop
- 实现 LLM 客户端

### 任务清单

#### 1. 类型定义 (2 天)

- [ ] `Message.java` - 消息类型
- [ ] `Session.java` - 会话类型
- [ ] `LoopResult.java` - 循环结果
- [ ] `TokenUsage.java` - Token 统计
- [ ] `ToolCall.java` - 工具调用
- [ ] `ToolResult.java` - 工具结果

#### 2. 配置系统 (1 天)

- [ ] `HarnessConfig.java` - 配置类
- [ ] `LoopConfig.java` - 循环配置
- [ ] 配置文件加载（YAML）

#### 3. LLM 客户端 (3 天)

- [ ] `LLMClient.java` - 接口定义
- [ ] `AnthropicClient.java` - Anthropic 实现
- [ ] 流式响应支持
- [ ] 错误处理和重试

#### 4. Agent Loop (4 天)

- [ ] `AgentLoop.java` - 循环引擎
- [ ] `ContextBuilder.java` - 上下文构建
- [ ] 生命周期钩子系统
- [ ] 中断和超时处理

### 交付物

- 可运行的 Agent Loop
- 基本的 LLM 调用能力
- 单元测试覆盖

## Phase 2: 工具系统

### 目标

- 实现工具接口
- 实现内置工具
- 实现工具执行器

### 任务清单

#### 1. 工具接口 (1 天)

- [ ] `Tool.java` - 工具接口
- [ ] `ToolContext.java` - 执行上下文
- [ ] `ToolResult.java` - 执行结果
- [ ] `ToolCategory.java` - 工具分类

#### 2. 内置工具 (5 天)

- [ ] `ReadTool.java` - 文件读取
- [ ] `WriteTool.java` - 文件写入
- [ ] `EditTool.java` - 文件编辑
- [ ] `GlobTool.java` - 文件搜索
- [ ] `GrepTool.java` - 内容搜索
- [ ] `BashTool.java` - 命令执行

#### 3. 工具执行器 (2 天)

- [ ] `ToolExecutor.java` - 执行调度
- [ ] 并行执行支持
- [ ] 超时和错误处理

#### 4. 自定义工具支持 (2 天)

- [ ] 注解式工具定义
- [ ] 工具注册 API
- [ ] 工具文档生成

### 交付物

- 完整的工具系统
- 6 个内置工具
- 工具开发文档

## Phase 3: MCP 集成

### 目标

- 集成 MCP Java SDK
- 实现 MCP 工具包装器
- 支持多种传输方式

### 任务清单

#### 1. MCP 客户端 (3 天)

- [ ] `McpConfig.java` - 配置类
- [ ] `HarnessMcpClient.java` - 客户端包装
- [ ] Stdio 传输支持
- [ ] HTTP/SSE 传输支持

#### 2. MCP 工具适配 (2 天)

- [ ] `McpToolWrapper.java` - 工具包装器
- [ ] JSON Schema 验证
- [ ] 错误处理

#### 3. MCP 管理器 (2 天)

- [ ] `McpManager.java` - 多服务器管理
- [ ] 连接生命周期
- [ ] 工具发现和注册

### 交付物

- MCP 集成模块
- 支持主流 MCP 服务器
- MCP 集成文档

## Phase 4: 记忆系统

### 目标

- 实现持久化记忆
- 实现 Token 计数
- 实现上下文管理

### 任务清单

#### 1. Token 计数 (2 天)

- [ ] `TokenCounter.java` - 使用 jtokkit
- [ ] 缓存优化
- [ ] 精度验证测试

#### 2. 记忆管理 (3 天)

- [ ] `MemoryManager.java` - 记忆管理器
- [ ] `Memory.java` - 记忆实体
- [ ] MEMORY.md 解析和生成
- [ ] 记忆 CRUD 操作

#### 3. 上下文构建 (2 天)

- [ ] `ContextBuilder.java` - 上下文构建
- [ ] Token 预算管理
- [ ] 历史消息截断

### 交付物

- 完整的记忆系统
- Token 计数准确性验证
- 记忆系统文档

## Phase 5: 安全模块

### 目标

- 实现输入验证
- 实现沙箱执行
- 实现输出清理
- 实现审计日志

### 任务清单

#### 1. 输入验证 (2 天)

- [ ] `InputValidator.java` - 验证接口
- [ ] 注入攻击检测
- [ ] 敏感数据检测

#### 2. 沙箱执行 (3 天)

- [ ] `SandboxExecutor.java` - 沙箱执行器
- [ ] 文件系统隔离
- [ ] 命令白名单/黑名单
- [ ] 资源限制

#### 3. 输出清理 (2 天)

- [ ] `ResultSanitizer.java` - 清理接口
- [ ] 敏感数据脱敏规则
- [ ] 银行特定规则

#### 4. 审计日志 (1 天)

- [ ] `AuditLogger.java` - 日志记录器
- [ ] 审计日志钩子
- [ ] 日志轮转和清理

### 交付物

- 安全模块
- 银行级安全配置
- 安全最佳实践文档

## Phase 6: 测试覆盖

### 目标

- 单元测试覆盖
- 集成测试
- 性能测试

### 任务清单

#### 1. 单元测试 (5 天)

- [ ] 核心类型测试
- [ ] 工具系统测试
- [ ] MCP 集成测试
- [ ] 记忆系统测试
- [ ] 安全模块测试

#### 2. 集成测试 (3 天)

- [ ] 端到端测试
- [ ] 与真实 API 集成测试
- [ ] MCP 服务器集成测试

#### 3. 性能测试 (2 天)

- [ ] Token 计数性能
- [ ] 并发执行测试
- [ ] 内存使用测试

### 交付物

- 80%+ 测试覆盖率
- 集成测试套件
- 性能基准报告

## Phase 7: 文档完善

### 目标

- API 文档
- 使用指南
- 示例代码

### 任务清单

#### 1. API 文档 (2 天)

- [ ] Javadoc 生成
- [ ] API 参考文档
- [ ] 类型定义文档

#### 2. 使用指南 (2 天)

- [ ] 快速开始指南
- [ ] 工具开发指南
- [ ] MCP 集成指南
- [ ] 安全最佳实践

#### 3. 示例代码 (3 天)

- [ ] 基础使用示例
- [ ] 自定义工具示例
- [ ] MCP 集成示例
- [ ] 银行集成示例

### 交付物

- 完整文档集
- 可运行的示例代码
- Javadoc API 文档

## Phase 8: 发布准备

### 目标

- 构建 JAR 包
- 质量检查
- 发布

### 任务清单

#### 1. 构建配置 (1 天)

- [ ] Shadow JAR 配置优化
- [ ] 模块化 JAR 构建
- [ ] 校验和生成

#### 2. 质量检查 (2 天)

- [ ] OWASP 依赖扫描
- [ ] SBOM 生成
- [ ] 许可证检查

#### 3. 发布 (2 天)

- [ ] 发布到 Maven Central（可选）
- [ ] 构建离线部署包
- [ ] 版本标签

### 交付物

- harness-sdk-all-1.0.0.jar
- 模块化 JAR 包
- 离线部署包
- 发布说明

## 里程碑

| 里程碑 | 目标日期 | 状态 |
|--------|---------|------|
| M1: 项目初始化完成 | 第 1 周结束 | 待开始 |
| M2: 核心框架可用 | 第 3 周结束 | 待开始 |
| M3: 工具系统完成 | 第 5 周结束 | 待开始 |
| M4: MCP 集成完成 | 第 6 周结束 | 待开始 |
| M5: 记忆系统完成 | 第 7 周结束 | 待开始 |
| M6: 安全模块完成 | 第 8 周结束 | 待开始 |
| M7: 测试覆盖达标 | 第 10 周结束 | 待开始 |
| M8: 文档完善 | 第 11 周结束 | 待开始 |
| M9: 发布就绪 | 第 12 周结束 | 待开始 |

## 资源需求

### 人力

- **核心开发**: 1 人，全职
- **技术审查**: 按需

### 技术依赖

- Java 17+ 环境
- Gradle 8.x
- 测试 API Key（Anthropic）

### 外部依赖

- Anthropic Java SDK
- MCP Java SDK
- jtokkit

## 风险与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| MCP SDK API 变更 | 高 | 中 | 封装适配层，跟进官方更新 |
| Token 计数精度 | 中 | 低 | 编写对比测试，文档说明 |
| Anthropic API 变更 | 高 | 低 | 使用官方 SDK，关注更新日志 |
| 性能不达预期 | 中 | 低 | 性能测试，优化热点 |

## 下一步

- [10-comparison.md](./10-comparison.md) - Python SDK 对比分析
- [11-testing.md](./11-testing.md) - 测试策略