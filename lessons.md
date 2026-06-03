# Lessons Learned

开发过程中积累的经验教训，避免重复踩坑。

---

## 2026-05-31: QThread + qasync 不兼容导致程序崩溃

### 问题

客户端使用 `AsyncWorker(QThread)` 运行异步协程，在创建 OpenAI client 时程序静默崩溃，无异常输出。

### 原因

`AsyncWorker` 在 QThread 中创建新的 event loop (`asyncio.new_event_loop()`)，这与 qasync 的 `QEventLoop` 不兼容。qasync 要求所有异步操作都在主线程的 `QEventLoop` 中运行。

### 解决

使用 qasync 提供的 `@asyncSlot()` 装饰器，替代 `QThread`：

```python
# ❌ 错误：QThread + 新 event loop 与 qasync 不兼容
class AsyncWorker(QThread):
    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(self.coro)

self._current_worker = AsyncWorker(coro)
self._current_worker.start()

# ✅ 正确：使用 @asyncSlot() 装饰器
from qasync import asyncSlot

@asyncSlot(str)  # 必须声明信号参数类型
async def _on_message_sent(self, message: str):
    async for chunk in self.chat_controller.send_message(message):
        response = chunk
    self._on_response_received(response)
```

### 教训

1. **qasync 使用原则**：所有异步操作必须在主线程的 `QEventLoop` 中运行，不能在 QThread 中创建新的 event loop
2. **使用 @asyncSlot()**：Qt 信号连接的异步方法应使用 `@asyncSlot()` 装饰器
3. **查阅官方文档**：遇到框架兼容性问题，先查阅框架文档（如 qasync 文档）

### 参考

- qasync 文档：https://github.com/CabbageDevelopment/qasync
- 关键提交：`d5082f7 fix: Complete fix for qasync/Windows crashes`

---

## 2026-05-31: 会话管理重构 - 状态分散问题

### 问题

客户端会话管理设计存在多处缺陷：

1. **状态分散**：同一概念（当前会话）在多处存储
   - `ChatController.state.session_id`
   - `ChatController._session_cache`
   - `SidebarPanel._current_session_id`

2. **UI 与数据混合**：`SidebarPanel.switch_to_session()` 做了数据操作（交换会话 ID），违反单一职责

3. **消息缓存 Bug**：
   ```python
   # 错误：full_response 还是空的
   if full_response:
       assistant_msg = Message(...)
   full_response = result.content  # 这里才赋值
   ```

4. **线程安全隐患**：子线程写 `_session_cache`，主线程读，无同步机制

### 原因

功能逐步添加时，没有统一的数据模型，各组件自行存储状态。

### 解决

引入 `SessionManager` 作为单一数据源：

```python
class SessionManager:
    _sessions: OrderedDict[str, ClientSession]
    _current_id: str | None

    def create() -> ClientSession
    def get_current() -> ClientSession | None
    def switch_to(session_id) -> bool
    def get_history_list() -> list[ClientSession]
```

UI 组件只负责渲染，不存储状态：
```python
def update_sessions(self, current: ClientSession, history: list[ClientSession]):
    """被动接收数据，只负责渲染"""
```

### 教训

1. **单一数据源原则**：同一数据只应在一处存储，其他地方通过查询获取
2. **UI 组件不存状态**：UI 只负责渲染，状态由数据层管理
3. **数据模型要完整**：会话不只是消息列表，还应包含名称、时间戳、元数据
4. **先设计再实现**：功能逐步添加时，要定期审视整体设计

---

## 2026-05-31: QListWidget 初始项未设置数据

### 问题

PyQt6 的 `QListWidget.addItem(str)` 只添加文本，不会设置 `UserRole` 数据。点击历史会话时：
- `item.data(Qt.ItemDataRole.UserRole)` 返回 `None`
- 导致会话切换信号不触发

### 原因

初始化时使用了简化的 `addItem("文本")` 而非创建 `QListWidgetItem` 并设置数据。

### 解决

```python
# ❌ 错误：只添加文本，没有数据
self.session_list.addItem("🔵 当前会话")

# ✅ 正确：创建项并设置数据
current_item = QListWidgetItem("🔵 当前会话")
current_item.setData(Qt.ItemDataRole.UserRole, "default")
self.session_list.addItem(current_item)
```

### 教训

1. **列表项数据很重要**：如果后续需要获取项的关联数据，初始化时就要设置
2. **信号处理要检查数据**：`item.data()` 可能返回 `None`，要防御性处理

---

## 2026-05-31: 会话切换时的重复添加问题

### 问题

`_on_session_switch` 中先调用 `add_session` 添加当前会话到历史列表，再调用 `switch_to_session`。但 `switch_to_session` 本身就处理了列表项交换，导致重复添加。

### 原因

两个方法的职责重叠：
- `add_session`: 创建新的列表项
- `switch_to_session`: 交换两个已存在的列表项

调用者误以为需要先添加再切换。

### 解决

只调用 `switch_to_session`，它已经处理了完整的交换逻辑。

### 教训

1. **理解方法职责**：调用前要明确方法做了什么，避免重复操作
2. **方法命名要清晰**：`switch_to_session` 应暗示它处理完整切换，不需要额外准备

---

## 2026-05-29: ToolResult 类型定义不一致

### 问题

文档 `docs/03-tool-system.md` 中定义的 `ToolResult` 有 `ok()` 和 `error()` 工厂方法：

```python
@classmethod
def ok(cls, content: str, **metadata) -> "ToolResult":
    return cls(success=True, content=content, metadata=metadata)

@classmethod
def error(cls, message: str) -> "ToolResult":
    return cls(success=False, content="", error=message)
```

但实际 `src/harness/types.py` 中的 `ToolResult` 是一个简单的 dataclass，没有这些方法。导致 MCPToolWrapper 使用时报错。

### 原因

1. 设计文档和实现不同步
2. 新增代码参考了文档中的"理想"接口，而非实际实现

### 解决

修改 `MCPToolWrapper` 直接构造 `ToolResult` 对象：

```python
# ❌ 按文档写（会报错）
return ToolResult.ok(content)

# ✅ 按实际实现写
return ToolResult(
    tool_call_id="",
    success=True,
    content=content,
    metadata={...}
)
```

### 教训

1. **先读实现再写代码**：不要只看设计文档，要检查实际代码
2. **类型检查很重要**：mypy 可以在编译期发现这类问题
3. **文档要和实现同步**：如果文档是设计目标，要显式标记"待实现"

### 检查方法

```bash
# 检查类是否有某个方法
python -c "from harness.types import ToolResult; print(hasattr(ToolResult, 'ok'))"
```

---

## 2026-05-29: 公共组件未被复用

### 问题

`harness.py` 中有独立的 `_default_progress_handler`（约35行），没有使用 `progress.py` 的公共格式化器，导致：
- 代码重复
- 修改一处忘记另一处（截断长度 20 字符只改了 `progress.py`，没改 `harness.py`）

### 原因

新增功能时直接在调用处实现，没有检查是否有现成的公共模块。

### 解决

删除 `harness.py` 的 `_default_progress_handler`，改用 `progress.py` 的 `create_progress_handler()`。

### 教训

1. **新增显示/格式化逻辑时**：先检查是否有现成的公共模块
2. **公共模块要导出**：在 `__init__.py` 中导出，方便发现和复用
3. **代码审查重点**：关注"重复实现"而非只是"重复代码"（相同功能在不同位置实现）

### 检查方法

```bash
# 搜索类似的实现模式
grep -r "strftime.*%H:%M:%S" src/
grep -r "duration_ms.*ms" src/
grep -r "icon.*=.*{" src/
```

---

## 2026-05-29: ErrorHandler 初始化但未使用

### 问题

`agent_loop.py` 中初始化了 `ErrorHandler`，但 `except Exception` 块中没有使用它，错误处理逻辑是硬编码的。

### 原因

功能规划了但未完成实现。

### 解决

在 LLM 调用和全局异常处理中使用 `ErrorHandler`，根据错误类型决定重试、压缩上下文或中止。

### 教训

1. **初始化了就要用**：如果组件初始化但未使用，要么完成实现，要么删除
2. **代码审查**：检查 `_xxx` 私有变量是否被实际调用
3. **TODO 标记**：未完成的功能要显式标记，不要留下"僵尸代码"

### 检查方法

```bash
# 检查初始化但未使用的私有变量
grep -r "self\._\w+ =" src/ | cut -d: -f2 | sort | uniq
grep -r "self\._\w+\." src/ | cut -d: -f2 | sort | uniq
# 对比两个列表，找出未调用的变量
```

---

## 2026-05-29: 测试失败时的渐进修复策略

### 问题

编写 `test_security.py` 时，3 个测试失败：
- `test_custom_rule`: 自定义规则传入字符串而非 `re.compile` 编译的正则
- `test_sanitize_dict`: 断言检查不匹配实际输出格式
- `test_get_redaction_report`: 断言过于具体，实际 regex 匹配结果不确定

### 原因

1. 自定义规则接口设计：`SanitizationRule.pattern` 应为 `Pattern` 类型，但测试传入字符串
2. 测试断言写得太具体：假设特定输出格式，但实际 regex 可能不匹配

### 解决

1. 修正测试：使用 `re.compile(r"...")` 传入编译后的正则
2. 放宽断言：检查关键属性而非精确匹配，如检查 `"[REDACTED]" in result` 而非精确字符串

### 教训

1. **类型一致性**：测试用例要与接口类型定义一致
2. **断言适度**：检查核心行为而非边界细节，regex 匹配结果可能因输入格式变化
3. **渐进修复**：先修复明显错误（import 缺失、类型错误），再调整断言逻辑

### 检查方法

```python
# 断言原则
# ❌ 过于具体
assert result == "exact string"

# ✅ 检查核心行为
assert "[REDACTED]" in result
assert result.startswith("expected_prefix")
assert len(result) > 0
```

---

## 2026-06-03: 测试边界条件的精确性

### 问题

编写 `test_phase25_step_budget.py` 时，多个测试因边界条件不精确而失败：
- `max_tool_calls_per_task=5` 但 `max_tool_calls_per_step=10`，违反 `per_task >= per_step` 约束
- 测试假设 100% 使用率触发 CRITICAL，但实际触发 EXCEEDED（ratio >= 1.0）
- 测试假设 90% 使用率触发 CRITICAL，但实际是 WARNING（threshold 配置为 warning=0.8, critical=0.95）

### 原因

1. **配置约束未遵守**：`StepBudgetConfig` 有 `max_tool_calls_per_task >= max_tool_calls_per_step` 约束
2. **阈值理解偏差**：
   - `warning_threshold=0.8`：80% 及以上触发 WARNING
   - `critical_threshold=0.95`：95% 及以上触发 CRITICAL
   - `ratio >= 1.0`：触发 EXCEEDED（超出预算）
3. **百分比计算**：10/10 = 100%，不是 95%

### 解决

1. 修正配置：`max_tool_calls_per_task` 必须大于或等于 `max_tool_calls_per_step`
2. 精确计算使用率：
   ```python
   # 9/10 = 90% >= 0.8 → WARNING
   # 10/10 = 100% >= 0.95 → CRITICAL
   # 但 ratio >= 1.0 触发 EXCEEDED
   ```
3. 测试使用明确的边界值：
   ```python
   # 测试 WARNING: 使用 80% 左右
   for i in range(8): controller.record_tool_call(f"tool_{i}")  # 8/10 = 80%
   
   # 测试 CRITICAL: 使用 95% 左右（但要避免 100%）
   for i in range(95): controller.record_tool_call(f"tool_{i}")  # 95/100 = 95%
   ```

### 教训

1. **先读配置约束**：编写测试前检查 `__post_init__` 中的验证逻辑
2. **精确计算百分比**：ratio = current / limit，1.0 意味着 100%
3. **避免边界混淆**：`>= critical_threshold` 和 `>= 1.0` 是不同的触发条件
4. **使用安全值**：测试 WARNING 用 80-85%，测试 CRITICAL 用 95-99%，避免 100%

### 检查方法

```python
# 检查配置约束
config = StepBudgetConfig(max_tool_calls_per_step=10, max_tool_calls_per_task=5)
# ValueError: max_tool_calls_per_task must be >= max_tool_calls_per_step

# 精确计算使用率
ratio = current / limit
level = EXCEEDED if ratio >= 1.0 else CRITICAL if ratio >= 0.95 else WARNING if ratio >= 0.8 else NORMAL
```