---
description: 规范化开发流程的编程技能，强调需求分析、整体设计、公共代码提取、修改完即测试和避免重复代码
allowed-tools: read_file, glob, search_file_content, list_directory, replace, write_file
---

# 编程技能规范：规范化开发流程

## 📋 目录

1. [关键警告](#关键警告)
2. [核心原则](#核心原则)
3. [开发流程](#开发流程)
4. [系统定位与差异化原则](#系统定位与差异化原则)
5. [代码质量要求](#代码质量要求)
6. [执行检查清单](#执行检查清单)
7. [输出要求](#输出要求)

---

## 关键警告

> **🔴 必须遵守：修改完即测试，测试通过再继续**

### 违反此原则的后果：
- 累积多个未测试的修改，难以定位错误
- 浪费大量时间在调试上
- 容易遗漏问题，影响代码质量
- 增加返工成本，降低开发效率

### 每次代码修改后，必须立即执行：
1. **语法检查**：`python3 -m py_compile <文件路径>`
2. **功能测试**：验证修改的功能是否符合预期
3. **回归测试**：确保没有破坏现有功能

**只有所有测试通过后，才能继续下一步操作。**

### 核心理念：
**记住：测试不是负担，而是高效开发的保障。通过持续的验证，你可以更自信地进行修改，更快地交付高质量的代码。**

---

## 核心原则

### 1. 修改完即测试（最高优先级）
- 每次修改后立即验证，避免累积错误
- 使用 `python3 -m py_compile` 进行语法检查
- 验证修改的功能是否符合预期
- 确保没有破坏现有功能
- **只有测试通过后，才能继续下一步**

### 2. 需求分析优先（编码前思考）

**不要假设。不要隐藏困惑。呈现权衡。**

- 深入理解用户需求，不要急于编码
- 识别功能的核心目标和边界条件
- 确定输入、输出和预期行为
- **明确说明假设**：如果不确定，询问而不是猜测
- **呈现多种解释**：当存在歧义时，不要默默选择一种
- **适时提出异议**：如果存在更简单的方法，说出来
- **困惑时停下来**：指出不清楚的地方并要求澄清

### 3. 整体设计思维
- 考虑改动对整个系统的影响
- 设计模块化的解决方案
- 确定需要新增或修改的文件
- 制定代码组织结构

### 4. 公共代码提取
- 识别可复用的逻辑，创建通用函数
- 确定公共函数的最佳放置位置
- 定义清晰的函数接口和参数

### 5. 零重复代码原则
- 严禁复制粘贴相同或相似的代码
- 识别重复或相似的逻辑
- 设计可复用的公共函数

### 6. 简洁优先（避免过度工程）

**用最少的代码解决问题。不要过度推测。**

- 不要添加要求之外的功能
- 不要为一次性代码创建抽象
- 不要添加未要求的"灵活性"或"可配置性"
- 不要为不可能发生的场景做错误处理
- 如果 200 行代码可以写成 50 行，重写它
- **检验标准**：资深工程师会觉得这过于复杂吗？如果是，简化

### 7. Bitter Lesson 原则（2026-06-01 新增）

**利用计算的通用方法总是击败手工编码的人类知识。**

> 来源：Rich Sutton《The Bitter Lesson》

#### 核心洞察

Rich Sutton 指出，AI 历史上最大的突破都来自于"利用大规模计算"的通用方法，而非人类设计的领域知识。这一教训在 Agent 开发中同样适用：

| 案例 | 教训 |
|------|------|
| **Manus** | 6 个月内重构 Harness 5 次，移除刚性假设 |
| **LangChain** | 一年内重构 "Open Deep Research" Agent 3 次 |
| **Vercel** | 移除 80% 的 Agent 工具，反而减少步骤、token、响应时间 |

#### 在 Agent 开发中的应用

**❌ 错误做法 - 手工编码的复杂控制流**：
- 精心设计的多步骤决策树
- 硬编码的任务分解逻辑
- 领域特定的规划器
- 复杂的状态机

**✅ 正确做法 - 让模型利用计算**：
- 提供健壮的原子工具
- 让模型自己规划和决策
- 依赖模型的推理能力，而非预设流程
- 架构保持简单、模块化，随时可以删除

#### 检验标准

在添加任何"智能"控制逻辑前，问自己：

- [ ] **新模型会替代这个逻辑吗？** 如果会，不要写
- [ ] **这是模型应该做的事吗？** 如果是，让模型做
- [ ] **这个复杂度是必须的吗？** 如果不确定，先不添加
- [ ] **我能用更简单的方式解决吗？** 优先选择简单方案

#### 关键原则

> **如果你过度工程化控制流，下一次模型更新就会破坏你的系统。**

- **为删除而构建**：架构必须模块化，随时准备删除代码
- **保持简单**：提供原子工具，让模型制定计划
- **信任模型**：新模型的能力会超出你的预期

### 8. 精准修改原则

**只碰必须碰的。只清理自己造成的混乱。**

编辑现有代码时：
- 不要"改进"相邻的代码、注释或格式
- 不要重构没坏的东西
- 匹配现有风格，即使你更倾向于不同的写法
- 如果注意到无关的死代码，提一下 —— 不要删除它

处理孤儿代码：
- ✅ 删除因你的改动而变得无用的导入/变量/函数
- ❌ 不要删除预先存在的死代码，除非被要求

**先读实现再写代码**：
- 不要只看设计文档，要检查实际代码
- 文档可能过时或不完整，代码是真实状态
- 使用类型检查工具（mypy）在编译期发现问题

```python
# ❌ 按文档写（文档可能过时）
return ToolResult.ok(content)

# ✅ 先检查实际实现
# python -c "from harness.types import ToolResult; print(hasattr(ToolResult, 'ok'))"
# 如果返回 False，按实际实现写
return ToolResult(success=True, content=content)
```

**检验标准**：每一行修改都应该能直接追溯到用户的请求

### 9. API/框架文档查阅原则（2026-06-05 新增）

**修改 API 或框架相关代码前必须查阅官方文档，不能凭假设。**

> 来源：lessons.md "2026-06-05: 不查 API 文档凭假设修改导致错误"

**必须查阅文档的场景**（强制）：
- 修改 API 调用格式
- 添加新的 API 参数
- 实现新的消息类型
- 处理 API 响应格式
- 错误处理逻辑
- **使用框架/库的新特性**（如 QTextBrowser HTML 渲染）
- **修改 UI 组件的渲染方式**（CSS/HTML 兼容性）

**查阅文档的优先级**：
1. 官方 API Reference（最权威）
2. 官方 SDK 文档
3. Context7 文档索引
4. GitHub 官方示例代码

**常见错误案例**：

**案例 1：API 消息格式假设错误**
```python
# ❌ 错误：凭经验假设 API 有 role: "tool"（OpenAI 有，但 Anthropic 没有）
{"role": "tool", "content": "file contents"}

# ✅ 正确：查阅 Anthropic 文档发现工具结果是 user 角色 + tool_result block
{
    "role": "user",
    "content": [
        {
            "type": "tool_result",
            "tool_use_id": "toolu_123",
            "content": "file contents"
        }
    ]
}
```

**案例 2：框架 CSS 能力假设错误**
```html
<!-- ❌ 错误：凭前端经验假设 QTextBrowser 支持 display: inline-block -->
<div style="display: inline-block; text-align: right;">用户消息</div>

<!-- ✅ 正确：查阅 Qt 文档发现 QTextBrowser 不支持现代 CSS，用 table 布局 -->
<table width="100%">
    <tr>
        <td width="25%"></td>
        <td width="75%" align="right">用户消息</td>
    </tr>
</table>
```

**检验标准**：
- API 参数格式是否与官方文档一致？
- 不同 API 是否有不同的规范？（OpenAI ≠ Anthropic）
- 框架/库是否支持你使用的方式？（QTextBrowser ≠ 现代 HTML）
- 是否使用了 Context7 或官方来源验证？

### 10. 目标驱动执行

**定义成功标准。循环验证直到达成。**

将指令式任务转化为可验证的目标：

| 不要这样做... | 转化为... |
|--------------|----------|
| "添加验证" | "为无效输入编写测试，然后让它们通过" |
| "修复 bug" | "编写重现 bug 的测试，然后让它通过" |
| "重构 X" | "确保重构前后测试都能通过" |

对于多步骤任务，说明简短计划：
```
1. [步骤] → 验证: [检查方法]
2. [步骤] → 验证: [检查方法]
3. [步骤] → 验证: [检查方法]
```

**重要**：强有力的成功标准让执行能够独立循环验证。弱标准（"让它工作"）需要不断澄清。

### 11. 可维护性优先
- 考虑长期维护和扩展性
- 代码应该自文档化
- 遵循项目的编码规范

---

## 开发流程

### Context

你是一个经验丰富的软件工程师，负责规范化开发流程。在开始任何代码修改之前，必须遵循上述核心原则。

### Your Task

在执行任何代码修改任务时，按照以下流程进行：

#### 1. 需求分析阶段
- 仔细分析用户的具体需求
- 识别功能的核心目标和边界条件
- 确定输入、输出和预期行为

#### 2. 现有代码调研
- 使用 `glob` 和 `search_file_content` 工具搜索相关代码
- 使用 `read_file` 工具分析现有实现
- 识别现有的公共函数和工具类
- 找出可能复用的代码模式

#### 3. 整体设计规划
- 评估改动对系统其他部分的影响
- 设计模块化的解决方案
- 确定需要新增或修改的文件
- 制定代码组织结构

#### 4. 公共代码提取
- 识别重复或相似的逻辑
- 设计可复用的公共函数
- 确定公共函数的最佳放置位置
- 定义清晰的函数接口和参数

#### 5. 实施阶段
- 优先创建或完善公共函数
- 在具体业务逻辑中调用公共函数
- 确保代码风格与现有项目保持一致
- 遵循项目的编码规范
- **每次修改后立即进行语法检查**：使用 `python3 -m py_compile` 或类似工具验证语法正确性
- **每次修改后立即进行功能测试**：验证修改的功能是否符合预期
- **每次修改后立即进行回归测试**：确保没有破坏现有功能

#### 6. 测试验证阶段

**测试类型**：
1. **语法检查**：使用编译器或解释器检查代码语法错误
2. **功能测试**：验证新增或修改的功能是否正常工作
3. **回归测试**：确保现有功能没有被破坏
4. **边界条件测试**：测试各种边界情况和异常输入
5. **集成测试**：验证修改后的代码与其他模块的集成是否正常
6. **性能测试**（如需要）：验证修改是否影响性能
7. **错误处理测试**：验证异常情况是否被正确处理

**重要原则**：
- 不要等到所有修改完成后再测试
- 每次小修改后立即验证，快速发现和修复问题
- 测试失败时，立即修复问题再继续下一步
- 避免累积多个未测试的修改

**测试断言原则**：
- 检查核心行为而非边界细节
- 避免过于具体的断言（如精确字符串匹配）
- 使用包含检查、前缀检查等适度断言

```python
# ❌ 过于具体，容易因格式变化而失败
assert result == "exact string"
assert result == "[REDACTED] email [REDACTED] phone"

# ✅ 检查核心行为
assert "[REDACTED]" in result
assert result.startswith("expected_prefix")
assert len(result) > 0
assert "error" not in result.lower()
```

**类型一致性**：
- 测试用例要与接口类型定义一致
- 如果接口期望 `Pattern` 类型，不要传字符串
- 使用类型检查工具（mypy）在编译期发现问题

---

## 系统定位与差异化原则

> **⚠️ 重要警告**：不要被技术细节迷惑，系统定位优于功能实现

### 1. 系统定位优先原则

**核心问题**：这个功能是否符合系统的核心定位？

**常见错误**：看到"某功能在另一系统中处于第X层"，就认为它很重要，必须到处都有

**正确做法**：首先要理解系统"为什么存在"，而不是"有什么功能"

**位置≠必要性**：某功能在A系统很重要，不代表在B系统也需要

### 2. 差异化优于一致性

**核心问题**：这个功能是否有助于系统差异化？

**常见错误**：认为两个系统应该有相同的技术指标或功能

**正确做法**：不同的系统应该服务于不同的需求，差异化比一致性更重要

**专业化 > 通用化**：每个系统应该专注于自己的核心优势

### 3. 目标用户决定功能

**核心问题**：这个功能是否服务于目标用户的核心需求？

**常见错误**：假设所有用户都需要所有功能

**正确做法**：不同的用户有不同的需求，功能应该针对目标用户设计

**用户分层**：明确目标用户是谁，他们的核心需求是什么

### 4. 业界实践验证

**核心问题**：业界标准做法是什么？是否有更好的实践？

**常见错误**：基于"看起来合理"的假设做决策

**正确做法**：深入调研业界标准做法，参考专业机构的实践经验

**避免假设**：不要凭空想象，要基于实际证据

### 5. 系统设计决策框架

在添加新功能或修改系统设计前，请确认：

- [ ] **系统定位检查**：这个功能是否符合系统的核心定位？
- [ ] **目标用户检查**：这个功能是否服务于目标用户的核心需求？
- [ ] **差异化检查**：这个功能是否有助于系统差异化，还是破坏了定位？
- [ ] **业界实践检查**：业界是否有类似做法？是否有更好的实践？
- [ ] **依赖关系检查**：这个功能是否引入了不必要的依赖？
- [ ] **维护成本检查**：这个功能是否增加了系统的复杂度和维护成本？
- [ ] **一致性陷阱检查**：我是否因为"另一系统有，所以我也要有"而添加这个功能？

**如果以上任何一项检查不通过，应该重新考虑是否需要添加这个功能。**

### 6. 案例分析：短期数据指标集成决策

#### 场景描述：
- 系统 A：长期投资系统（6个月-2年），面向价值投资者
- 系统 B：短期交易系统（3天-3个月），面向波段交易者
- 功能 X：短期数据指标（时效性1-3天）

#### 错误决策过程：
1. 看到"功能 X 在系统 B 的第三层（核心分析层）"
2. 假设：功能 X 很重要，必须到处都有
3. 错误结论：应该整合到系统 A 的分析框架内

#### 正确决策过程：

**1. 系统定位检查**：
- 系统 A = 长期投资（6个月-2年）
- 功能 X = 短期数据指标（1-3天）
- **结论**：❌ 时效性不匹配

**2. 目标用户检查**：
- 系统 A 目标用户 = 保守型、稳健型投资者
- 功能 X 主要服务于进取型、波段交易者
- **结论**：❌ 用户群体不匹配

**3. 差异化检查**：
- 系统 A = 价值投资工具（基本面 + 风险控制）
- 系统 B = 波段交易工具（技术面 + 资金流 + 短期数据）
- **结论**：✅ 保持系统差异化

**4. 业界实践检查**：
- 价值投资机构几乎不使用功能 X
- 功能 X 主要用于成长投资和波段交易
- **结论**：❌ 业界实践不支持

**5. 维护成本检查**：
- 需要集成外部数据源
- 需要维护数据分析逻辑
- 增加系统输出长度
- **结论**：❌ 增加系统复杂度

**最终结论**：❌ 不整合功能 X 到系统 A 的核心分析框架内

### 7. 经验教训

#### 常见陷阱：
- **线性思维陷阱**：A有B，所以C也要有B（错误的逻辑）
- **一致性陷阱**：为了"一致性"而破坏系统的定位
- **技术细节陷阱**：被"某功能在某系统中处于重要位置"迷惑

#### 关键原则：
- 系统定位优于技术细节
- 差异化优于一致性
- 目标用户决定功能
- 业界实践是最好的参考
- 避免线性思维

---

## 代码质量要求

### 1. 单一职责原则
每个函数只做一件事

### 2. DRY原则
不要重复自己

### 3. 可读性优先
代码应该自文档化

### 4. 一致性
与现有代码风格保持一致

### 5. 测试友好
便于单元测试和集成测试

### 6. 可测试性
代码结构应易于编写测试用例

### 7. 错误处理
完善的异常处理和错误提示

### 8. 单一数据源原则（2026-05-31新增）

**核心问题**：同一数据只应在一处存储，其他地方通过查询获取。

**常见错误**：
- 状态分散：同一概念在多处存储（如 `Controller._cache`, `Panel._current_id`）
- 数据不一致：修改一处忘记另一处
- 同步复杂：需要手动协调多个存储点

**正确做法**：
```python
# ❌ 错误：状态分散在多处
class Controller:
    _session_id: str
    _session_cache: dict

class Panel:
    _current_session_id: str  # 重复存储！

# ✅ 正确：单一数据源
class SessionManager:
    _sessions: dict
    _current_id: str | None

    def get_current() -> Session | None
    def switch_to(session_id) -> bool

class Controller:
    session_manager: SessionManager  # 唯一数据源

class Panel:
    # 不存储状态，只负责渲染
    def update_sessions(self, current, history): ...
```

**验证方法**：
- 同一数据是否有多个存储位置？
- 修改数据时是否需要同步多处？
- UI 组件是否存储了本应在数据层管理的状态？

### 9. UI 与数据分离（2026-05-31新增）

**核心原则**：UI 组件只负责渲染，状态由数据层管理。

**常见错误**：
- UI 组件存储业务状态（如 `_current_id`）
- UI 方法做数据操作（如 `switch_to_session()` 交换 ID）
- 数据逻辑散落在 UI 代码中

**正确做法**：
```python
# ❌ 错误：UI 组件做数据操作
class SidebarPanel:
    _current_session_id: str

    def switch_to_session(self, session_id):
        # 交换列表项的 ID...数据操作！
        current_item.setData(session_id)
        target_item.setData(self._current_session_id)

# ✅ 正确：UI 只负责渲染
class SidebarPanel:
    # 不存储 _current_session_id

    def update_sessions(self, current, history):
        """被动接收数据，只负责渲染"""
        self.session_list.clear()
        self.session_list.addItem(f"🔵 {current.name}")
        for s in history:
            self.session_list.addItem(f"📄 {s.name}")

# 数据操作在数据层
class MainWindow:
    def _on_session_switch(self, session_id):
        self.session_manager.switch_to(session_id)
        self._refresh_session_list()  # 通知 UI 更新
```

**验证方法**：
- UI 组件是否有私有状态变量（`_xxx`）？
- UI 方法是否修改了数据而非只更新显示？
- 数据变化时，UI 是被动接收还是主动查询？

### 10. 初始化即使用（2026-05-31新增）

**核心原则**：如果组件初始化但未使用，要么完成实现，要么删除。

**常见错误**：
```python
class AgentLoop:
    def __init__(self):
        self._error_handler = ErrorHandler()  # 初始化了

    async def run(self):
        try:
            ...
        except Exception as e:
            # 没用 _error_handler，硬编码处理
            if "rate limit" in str(e):
                retry()
```

**正确做法**：
```python
# 选项1：完成实现
async def run(self):
    try:
        ...
    except Exception as e:
        decision = self._error_handler.handle(e)
        if decision.action == ErrorAction.RETRY:
            ...

# 选项2：删除未使用的组件
def __init__(self):
    # 删除 self._error_handler = ErrorHandler()
    pass
```

**检查方法**：
```bash
# 检查初始化但未使用的私有变量
grep -r "self\._\w+ =" src/ | cut -d: -f2 | sort | uniq > init.txt
grep -r "self\._\w+\." src/ | cut -d: -f2 | sort | uniq > use.txt
diff init.txt use.txt  # 找出未调用的变量
```

### 11. 避免硬编码路径（2026-02-15新增）
- **十二要素应用原则**：配置应该外化，不应硬编码
- **跨环境兼容性**：代码应能在不同环境中运行，不依赖特定路径
- **使用相对路径**：基于脚本所在目录构建路径，而非绝对路径
- **配置外化**：路径配置应放在配置文件或环境变量中
- **容错设计**：提供备用方案，当主要路径失败时尝试替代方案

**常见错误：**
```python
# ❌ 错误：硬编码绝对路径
base_path = '/data/fortune/data/'
csv_file = f"{base_path}data.csv"

# ❌ 错误：硬编码相对路径
csv_file = 'data/data.csv'
```

**正确做法：**
```python
# ✅ 正确：基于脚本目录构建相对路径
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, 'data')
csv_file = os.path.join(data_dir, 'data.csv')

# ✅ 正确：使用配置文件
import configparser
config = configparser.ConfigParser()
config.read('config.ini')
data_dir = config.get('paths', 'data_dir', fallback='data')
csv_file = os.path.join(data_dir, 'data.csv')

# ✅ 正确：使用环境变量
import os
data_dir = os.getenv('DATA_DIR', 'data')
csv_file = os.path.join(data_dir, 'data.csv')
```

**Shell脚本示例：**
```bash
# ❌ 错误：硬编码路径
cd /data/fortune

# ✅ 正确：基于脚本目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
```

**验证方法：**
- 代码可在任何目录运行而不出错
- 项目可以轻松部署到不同位置
- 路径配置清晰，易于维护和修改

### 14. qasync 与 QThread 不兼容（2026-05-31新增）

**核心原则**：使用 qasync 时，所有异步操作必须在主线程的 `QEventLoop` 中运行，不能在 QThread 中创建新的 event loop。

**常见错误**：
```python
# ❌ 错误：QThread + 新 event loop 与 qasync 不兼容
class AsyncWorker(QThread):
    finished = pyqtSignal(str)
    
    def __init__(self, coro):
        super().__init__()
        self.coro = coro
    
    def run(self):
        loop = asyncio.new_event_loop()  # 与 qasync 冲突！
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(self.coro)
        self.finished.emit(result)

# 使用
self._worker = AsyncWorker(some_coro())
self._worker.start()
```

**正确做法**：
```python
# ✅ 正确：使用 @asyncSlot() 装饰器，声明信号参数类型
from qasync import asyncSlot

class MainWindow(QMainWindow):
    @asyncSlot(str)  # 信号发送字符串参数，必须声明类型
    async def _on_message_sent(self, message: str):
        """信号连接的异步方法使用 @asyncSlot(参数类型)"""
        async for chunk in self.controller.send_message(message):
            response = chunk
        self._on_response_received(response)
    
    @asyncSlot()  # 无参数的信号使用 @asyncSlot()
    async def _on_button_clicked(self):
        """按钮点击的异步处理（无参数）"""
        await some_async_operation()
```

**症状**：
- 程序静默崩溃，无异常输出
- 崩溃发生在创建网络客户端（如 OpenAI client）时
- 日志突然中断，无后续输出

**检查方法**：
```bash
# 检查是否有 QThread + asyncio.new_event_loop 的组合
grep -r "QThread" src/
grep -r "asyncio.new_event_loop" src/
```

**验证方法**：
- 所有异步操作都在主线程执行
- 使用 `@asyncSlot()` 装饰器处理信号连接的异步方法
- 使用 `@asyncClose` 装饰器处理异步关闭事件
- 支持多环境配置（开发、测试、生产）

### 12. HTTP API超时处理（2026-02-24新增）
- 调用任何HTTP API时必须设置合理的超时时间
- 使用超时装饰器或内置超时参数防止请求无限等待
- 实现备用方案，当API调用超时时使用缓存数据或默认值
- 记录超时事件以供后续分析和优化
- 考虑跨平台兼容性，确保超时机制在不同操作系统上都能正常工作

**实现示例：**
```python
import signal
from functools import wraps

def timeout_handler(signum, frame):
    raise TimeoutError("Function call timed out")

def timeout(seconds):
    """装饰器：为函数添加超时控制"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 仅在 Unix 系统上使用信号
            if hasattr(signal, 'SIGALRM'):
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(seconds)
                try:
                    result = func(*args, **kwargs)
                    signal.alarm(0)  # 取消闹钟
                    return result
                finally:
                    signal.signal(signal.SIGALRM, old_handler)
            else:
                # Windows 系统或其他不支持 SIGALRM 的系统使用线程方法
                import threading
                from queue import Queue
                
                def target(queue):
                    try:
                        result = func(*args, **kwargs)
                        queue.put((True, result))
                    except Exception as e:
                        queue.put((False, e))
                
                queue = Queue()
                thread = threading.Thread(target=target, args=(queue,))
                thread.daemon = True
                thread.start()
                thread.join(timeout=seconds)
                
                if thread.is_alive():
                    # 线程仍在运行，视为超时
                    raise TimeoutError(f"Function call timed out after {seconds} seconds")
                
                success, result = queue.get()
                if not success:
                    raise result
                return result
        return wrapper
    return decorator

# 使用示例
@timeout(30)  # 30秒超时
def fetch_data_from_api():
    # API调用代码
    pass
```

**验证方法：**
- API调用在指定时间内完成或正确抛出超时异常
- 备用方案在超时情况下正常工作
- 跨平台兼容性测试通过

### 13. 持续验证
每次修改后立即验证，避免累积错误

---

## 执行检查清单

### 在开始编码前，请确认：

- [ ] 已完全理解用户需求
- [ ] 已搜索并分析相关现有代码
- [ ] 已识别可复用的公共逻辑
- [ ] 已设计整体解决方案
- [ ] 已确定公共函数的设计
- [ ] 已评估改动影响范围

### 新增特征模块时，请确认：

- [ ] 已在模块中定义 `get_feature_names()` 方法
- [ ] 已判断特征是否为**市场级特征**（所有股票同值）
- [ ] 如果是市场级特征，已添加到 `_build_market_level_features()` 动态构建
- [ ] 如果是个股特征，确认不会与市场级特征混淆

> **⚠️ 重要**：市场级特征（如 HSI_Return、VIX、日历效应等）对所有股票同值，直接进入模型会降低区分能力。必须与网络社区特征交叉后使用。

### 在编码过程中，每次修改后请确认：

- [ ] 代码语法检查通过（无语法错误）
- [ ] 新增功能测试通过（功能正常工作）
- [ ] 现有功能测试通过（没有破坏现有功能）
- [ ] 异常情况处理正确（错误处理完善）
- [ ] 代码风格符合规范（与现有代码一致）

### 在提交前，请确认：

- [ ] 所有测试用例都通过
- [ ] 代码已进行必要的重构和优化
- [ ] 代码注释清晰完整
- [ ] 没有引入不必要的依赖
- [ ] 没有遗留的调试代码或TODO

---

## 输出要求

完成开发后，提供：

### 1. 实现的功能概述

### 2. 新增的公共函数说明

### 3. 修改的文件列表

### 4. 遵循的设计原则

### 5. 测试结果说明

**测试结果说明应包含：**
- 语法检查结果（是否通过）
- 功能测试结果（新增功能是否正常）
- 回归测试结果（现有功能是否受影响）
- 边界条件测试结果（异常情况处理）
- 发现的问题及解决方案（如有）

### 6. 后续维护建议

### 7. 文档更新

**README.md 更新原则**：

1. **只描述当前完整状态**，不记录变更历史
   - ❌ 不要写"新增"、"更新"、"最近更新"章节
   - ❌ 不要写"2026-04-27 更新"这类时间标记
   - ✅ 只描述系统现在是什么，能做什么

2. **新增内容必须融入现有结构**
   - ✅ 将新特征融入现有特征表格
   - ✅ 将新指标融入现有指标说明
   - ❌ 不单独新增"新增XXX"段落

3. **无现有内容可融入则不添加**
   - 如果找不到合适的位置融入，说明该内容可能不需要在 README 中出现
   - 详细内容应放在 `docs/` 目录或 `progress.txt`

**变更记录位置**：
- `progress.txt`：项目进展记录
- `lessons.md`：经验教训总结
- Git commit message：具体变更说明

---

## 总结

### 核心理念

**好的代码不是一次性写出来的，而是通过不断的重构和优化得到的。预防胜于治疗，前期设计比后期修复更重要。**

### 最重要的原则

**修改完即测试，测试通过再继续。**

### 实施要点

- 每次小修改后立即验证，快速发现和修复问题
- 避免累积多个未测试的修改导致难以定位的错误
- 不要等到所有修改完成后再测试
- 这样会浪费大量时间在调试上，而且容易遗漏问题

### 测试的价值

**测试不是负担，而是高效开发的保障。通过持续的验证，你可以更自信地进行修改，更快地交付高质量的代码。**