---
name: sync-design-docs
description: 将开发中新增的功能同步回设计文档，保持文档与代码的一致性
user_invocable: true
tools:
  allowed:
    - read
    - write
    - edit
    - glob
    - grep
    - bash
---

# Sync Design Docs - 文档同步技能

将开发过程中新增的功能同步回设计文档，确保文档始终反映代码的最新状态。

## 标准操作流程 (SOP)

### Phase 1: 代码分析

1. **识别变更范围**
   - 检查 git status 了解未提交的变更
   - 检查 git diff 了解具体改动
   - 查看 recent commits 了解最近的变更

2. **提取新增功能**
   - 新增的类、函数、模块
   - 新增的配置项
   - 新增的 API 接口
   - 新增的工具
   - 行为变更

3. **生成功能清单**
   ```
   ## 新增功能清单

   ### 新增类/模块
   - `ClassName` (file_path:line) - 简短描述

   ### 新增 API
   - `method_name()` (file_path:line) - 简短描述

   ### 新增配置项
   - `config_option` - 类型 - 描述

   ### 行为变更
   - 变更描述
   ```

### Phase 2: 文档定位

1. **扫描现有文档**

   **SDK 文档** (`packages/sdk/docs/`)：
   ```
   docs/
   ├── 01-overview.md      # 项目概述与架构
   ├── 02-agent-loop.md    # Agent Loop
   ├── 03-tool-system.md   # 工具系统
   ├── 04-memory-system.md # 记忆系统
   ├── 05-skills-system.md # 技能系统
   ├── 06-triggers.md      # 触发器
   ├── 07-sdk-api.md       # SDK 与 API
   ├── 08-security.md      # 安全设计
   ├── 09-implementation.md # 实施路线图
   ├── 10-comparison.md    # 对比分析
   ├── 11-testing.md       # 测试策略
   ├── 12-deployment.md    # 部署指南
   ├── HARNESS_DESIGN.md   # 设计文档索引
   ├── programmer_skill.md # 编程规范
   └── README.md           # 用户文档
   ```

   **客户端文档** (`packages/client/docs/`)：
   ```
   docs/
   ├── 01-overview.md      # 客户端概述
   ├── 02-ui-components.md # UI 组件
   ├── 03-controllers.md   # 控制器
   ├── 04-configuration.md # 配置
   ├── 05-client-lessons.md # 经验教训
   └── README.md           # 用户文档
   ```

   **Cloud 文档** (`packages/cloud/docs/`)：
   ```
   docs/
   ├── 01-overview.md      # Cloud 架构概述
   ├── 02-agent.md         # Agent glue layer
   ├── 03-gateway.md       # Gateway 控制层
   ├── 05-messages.md      # WebSocket 协议
   ├── 06-deployment.md    # 部署指南
   └── README.md           # 用户文档
   ```

   **根目录文档**：
   ```
   CLAUDE.md               # Claude Code 工作指引
   lessons.md              # 经验教训总结
   progress.txt            # 项目进展记录
   ```

2. **确定文档映射关系**

   **SDK 文档映射**：
   | 功能类型 | 目标文档 |
   |---------|---------|
   | Agent Loop 相关 | 02-agent-loop.md |
   | 工具相关 | 03-tool-system.md |
   | 记忆系统相关 | 04-memory-system.md |
   | 技能相关 | 05-skills-system.md |
   | 触发器相关 | 06-triggers.md |
   | SDK/API 相关 | 07-sdk-api.md |
   | 安全相关 | 08-security.md |
   | 快速开始示例 | README.md |
   | 架构概述 | 01-overview.md |
   | 编程规范/经验教训 | programmer_skill.md |

   **客户端文档映射**：
   | 功能类型 | 目标文档 |
   |---------|---------|
   | UI 组件 | 02-ui-components.md |
   | 控制器逻辑 | 03-controllers.md |
   | 配置相关 | 04-configuration.md |
   | 经验教训 | 05-client-lessons.md |

   **Cloud 文档映射**：
   | 功能类型 | 目标文档 |
   |---------|---------|
   | 架构概述 | 01-overview.md |
   | Agent 层设计 | 02-agent.md |
   | Gateway 层设计 | 03-gateway.md |
   | WebSocket 协议 | 05-messages.md |
   | 部署配置 | 06-deployment.md |
   | 用户指南 | README.md |

   **根目录文档映射**：
   | 功能类型 | 目标文档 |
   |---------|---------|
   | Claude 工作指引 | CLAUDE.md |
   | 跨包经验教训 | lessons.md |
   | 项目进展 | progress.txt |

3. **生成文档更新计划**
   ```
   ## 文档更新计划

   | 文档 | 更新内容 | 优先级 |
   |-----|---------|-------|
   | 07-sdk-api.md | 添加 OpenAIClient 第三方 API 支持说明 | 高 |
   | README.md | 更新 LLM 配置示例 | 高 |
   ```

### Phase 3: 内容生成

1. **生成文档内容格式规范**

   - **代码示例**: 使用可运行的代码块，包含必要的 import
   - **API 文档**: 包含参数、返回值、示例
   - **配置说明**: 包含类型、默认值、可选值

2. **内容生成模板**

   ```markdown
   ### 功能名称

   简短描述功能的作用。

   #### 使用示例

   ```python
   from harness import XXX

   # 示例代码
   ```

   #### 参数说明

   | 参数 | 类型 | 默认值 | 说明 |
   |-----|------|-------|------|
   | param | str | "default" | 参数说明 |

   #### 注意事项

   - 注意事项1
   - 注意事项2
   ```

### Phase 4: 执行更新

1. **确认更新内容**
   - 向用户展示更新计划
   - 等待用户确认

2. **执行文档更新**
   - 使用 Edit 工具进行精确更新
   - 保持现有文档结构和格式
   - 不删除现有内容，只添加或修正

3. **验证更新结果**
   - 检查更新后的文档格式
   - 确认代码示例语法正确
   - 确认链接有效

### Phase 5: 总结报告

生成更新报告：

```markdown
## 文档同步完成报告

### 更新的文档
- docs/07-sdk-api.md: 添加了 OpenAIClient 第三方 API 支持章节
- README.md: 更新了 LLM 配置章节

### 新增内容摘要
1. 添加了 OpenAI 第三方 API 配置说明
2. 添加了环境变量配置方式
3. 更新了完整配置参数示例

### 建议后续操作
- 检查代码示例是否可运行
- 更新 CHANGELOG（如有）
```

## 规则

1. **扫描所有包的文档**: 必须检查 SDK、Client、Cloud 三个包的文档目录
2. **不删除现有内容**: 只添加或修正，保留有价值的现有文档
3. **保持格式一致**: 遵循现有文档的格式风格
4. **代码可运行**: 所有代码示例必须是有效的 Python 代码
5. **先分析后更新**: 必须先完成代码分析再执行更新
6. **用户确认**: 执行更新前必须展示计划并等待用户确认

## 注意事项

1. 对于大型变更，分批更新文档
2. 保持中英文术语一致性
3. 注意文档间的交叉引用
4. 更新各包 README.md 的功能列表
5. 如有 API 变更，检查是否需要更新类型定义文档
6. **Cloud 相关变更**: 同时更新 `packages/cloud/docs/` 和 `packages/cloud/README.md`
7. **跨包经验教训**: 更新 `lessons.md` 和 `packages/sdk/docs/programmer_skill.md`
