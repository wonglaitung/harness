---
name: compare-design-impl
description: 使用 ultrathink 比较设计文档与实际实现，分析完成度，识别缺失的 MVP 必要功能，生成实施计划
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

# Compare Design vs Implementation - 设计与实现对比分析

深度分析设计文档与代码实现的差距，识别关键缺失功能，生成优先级实施计划。

## 触发条件

当用户需要：
- 了解项目完成度
- 识别遗漏的必要功能
- 制定实施计划
- 进行架构审计

## 标准操作流程 (SOP)

### Phase 1: 设计文档扫描

1. **扫描所有设计文档**
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
   ├── 09-implementation.md # 实施路线图 (关键！)
   ├── 10-comparison.md    # 对比分析
   ├── 11-testing.md       # 测试策略
   └── 12-deployment.md    # 部署指南
   ```

2. **重点读取 MVP 定义**
   - `docs/09-implementation.md` 中的 **MVP 必须有** 章节
   - `docs/09-implementation.md` 中的 **MVP 必须强化** 章节
   - 记录所有标记为 "必须" 的功能

3. **提取设计要求**
   - 类定义与接口规范
   - 数据结构定义
   - 行为约束
   - 配置参数
   - 错误处理策略

### Phase 2: 实现代码扫描

1. **扫描核心模块**
   ```
   src/harness/
   ├── sdk/harness.py          # 主入口
   ├── core/
   │   ├── agent_loop.py       # Agent Loop
   │   ├── circuit_breaker.py  # 熔断器
   │   └── error_handler.py    # 错误处理
   ├── llm/
   │   ├── base.py             # LLM 接口
   │   ├── anthropic.py        # Claude
   │   └── openai.py           # OpenAI
   ├── tools/
   │   ├── base.py             # Tool 抽象
   │   ├── builtins.py         # 内置工具
   │   └── executor.py         # 执行器
   ├── memory/
   │   ├── session.py          # 会话
   │   ├── store.py            # 存储
   │   └── context_builder.py  # 上下文构建
   ├── progress.py             # 进度格式化
   └── types.py                # 类型定义
   ```

2. **检查关键文件**
   - `src/harness/__init__.py` - 公共 API 导出
   - `src/harness/types.py` - 类型定义完整性
   - `tests/` - 测试覆盖情况

3. **提取实际实现**
   - 已实现的类和函数
   - 已定义的数据结构
   - 实际行为逻辑
   - 配置参数处理

### Phase 3: 差距分析 (Ultrathink 深度分析)

1. **功能对照表生成**

   ```
   ## 功能完成度对照表

   | 模块 | 设计要求 | 实现状态 | 完成度 | 缺失项 |
   |-----|---------|---------|-------|-------|
   | Agent Loop | ReAct循环 | ✅ 完成 | 85% | - |
   | Cost Control | 预算限制 | ❌ 缺失 | 0% | CostConfig, CostController |
   ```

2. **MVP 必要功能检查**

   对照 `docs/09-implementation.md` MVP 定义，逐项检查：

   ```
   ## MVP 必要功能检查清单

   ### ✅ 已完成
   - [x] Agent Loop (ReAct 循环)
   - [x] Tool System (工具抽象与执行)
   - [x] Skills System (技能加载与注入)
   
   ### ❌ 缺失
   - [ ] Cost Control (Session级预算)
   - [ ] Sliding Window Context (自动压缩)
   - [ ] Streaming Backpressure (背压控制)
   ```

3. **关键缺失识别**

   对每个缺失功能评估：

   - **影响级别**: P0 (关键) / P1 (重要) / P2 (次要)
   - **用户影响**: 功能缺失导致的用户问题
   - **技术依赖**: 是否阻塞其他功能
   - **实施难度**: 预计工作量

### Phase 4: 实施计划生成

1. **优先级排序规则**

   ```
   P0 (立即实施):
   - 影响用户安全或费用的功能
   - 阻塞其他关键功能的依赖
   
   P1 (近期实施):
   - 影响核心用户体验
   - 系统稳定性相关
   
   P2 (后续实施):
   - 优化性功能
   - 开发效率工具
   ```

2. **Phase 划分**

   每个缺失功能作为一个实施 Phase：

   ```
   ### Phase X: 功能名称 (优先级: P0/P1/P2)

   **目标**: 简短描述实施目标
   
   **设计来源**: 
   - docs/XX-xxx.md (第 N 行)
   
   **任务清单**:
   1. 任务1 - 文件路径
   2. 任务2 - 文件路径
   3. 任务3 - 文件路径
   
   **依赖关系**:
   - 依赖 Phase Y
   
   **预计工作量**: N 小时
   
   **验收标准**:
   - 标准1
   - 标准2
   ```

3. **时间规划**

   ```
   ## 实施时间规划

   Week 1: Phase 4 + Phase 5 (P0 功能)
   Week 2: Phase 6 + Phase 7 (P1 功能)
   Week 3: Phase 8 + Phase 9 (P2 功能)
   ```

### Phase 5: 报告生成

生成完整分析报告：

```markdown
# 设计文档 vs 实现对比分析报告

## A. 完成度总览

[功能对照表]

**总体完成度: X%**

## B. MVP 必要功能缺失分析

### 1. ❌ 功能名称 (完全缺失)

**设计要求** (docs/XX.md 第 N 行):
```python
# 设计代码片段
```

**当前实现** (src/harness/xxx.py):
```python
# 实际代码片段（或说明缺失）
```

**影响**: 用户影响描述

---

## C. 实施计划

### Phase 4: 功能名称 (优先级: P0)

**目标**: 功能目标

**任务**:
1. 任务1
2. 任务2

**预计工作量**: N 小时

---

## D. 建议执行顺序

[时间规划]

---

## E. 风险评估

| 风险 | 影响 | 缓解措施 |
|-----|-----|---------|
| 功能缺失风险 | 用户影响 | 实施优先级 |
```

## 输出规则

1. **使用 Ultrathink**: 必须进行深度分析，不浅尝辄止
2. **引用精确**: 所有设计要求必须标注文档路径和行号
3. **代码对比**: 设计与实现代码并列展示差异
4. **优先级明确**: 每个缺失功能必须标注 P0/P1/P2
5. **计划可执行**: 任务清单必须具体到文件路径

## 分析重点

### 必须检查的设计章节

| 文档 | 关键章节 | 行号范围 |
|-----|---------|---------|
| 09-implementation.md | MVP 必须有 | 442-450 |
| 09-implementation.md | MVP 必须强化 | 479-487 |
| 02-agent-loop.md | CostController | 1026-1131 |
| 02-agent-loop.md | LoopSnapshot | 1256-1327 |
| 02-agent-loop.md | StreamingHandler | 527-573 |
| 04-memory-system.md | ScalableSessionStore | 1171-1262 |
| 04-memory-system.md | IncrementalTokenCounter | 1348-1413 |

### 必须检查的实现文件

| 文件 | 检查内容 |
|-----|---------|
| types.py | TokenUsage, CostConfig 是否存在 |
| agent_loop.py | 状态机、熔断、快照 |
| context_builder.py | 滑动窗口、压缩触发 |
| tools/executor.py | JSON Schema 验证 |
| llm/base.py | stream() 背压控制 |

## 注意事项

1. **区分 "缺失" vs "不完整"**:
   - 缺失 = 完全没有实现
   - 不完整 = 有基本实现但缺少关键特性

2. **区分 "必要" vs "可选"**:
   - 必要 = MVP 定义中明确要求
   - 可选 = 设计文档中标记为可选或未来功能

3. **检查 lessons.md**:
   - 避免重复已知问题
   - 参考历史教训

4. **检查 progress.txt**:
   - 了解当前进展
   - 避免重复已完成的工作

## 与 sync-design-docs 的区别

| 命令 | 方向 | 目的 |
|-----|-----|-----|
| sync-design-docs | 代码 → 文档 | 将新功能同步回文档 |
| compare-design-impl | 文档 → 代码 | 找出文档中未实现的功能 |

两个命令互补使用：
- 开发后运行 `sync-design-docs` 更新文档
- 规划时运行 `compare-design-impl` 找差距