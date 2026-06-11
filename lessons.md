# Lessons Learned

开发过程中积累的经验教训，避免重复踩坑。

---

## 2026-06-11: PyQt6 组件选择 - QLabel vs QTextBrowser

### 问题

消息气泡高度计算反复出错：
1. 最初使用 QTextBrowser，sizeHint() 在 widget 未显示时返回不可靠的值
2. 尝试用 QTextDocument.documentLayout().documentSize() 修复，仍然不对
3. 最终改用 QLabel 才彻底解决

### 根本原因

**QTextBrowser/QTextEdit 的 sizeHint() 在 widget 显示前不可靠**：
- 初始气泡高度过大
- 添加消息后，气泡高度逐渐收缩直到文字消失
- 这是因为 QTextBrowser 的 sizeHint 依赖于实际渲染后的布局信息

**QLabel 的 sizeHint() 是准确的**：
- 即使在 widget 显示前也能正确计算
- 支持 setWordWrap(True) 自动换行
- 支持 setTextInteractionFlags(TextSelectableByMouse) 文本选择
- 支持 setTextFormat(RichText) 富文本渲染

### 解决

```python
# ❌ 错误：QTextBrowser sizeHint 不可靠
self._text_browser = QTextBrowser()
self._text_browser.setHtml(html)
# sizeHint() 返回不准确的值

# ✅ 正确：QLabel sizeHint 准确
self._label = QLabel()
self._label.setWordWrap(True)
self._label.setTextFormat(Qt.TextFormat.RichText)
self._label.setText(html)
# sizeHint() 返回准确的值
```

### 教训

1. **PyQt6 组件行为要查文档**：不能凭经验假设，不同组件的 sizeHint 行为差异很大
2. **QLabel 优先用于静态文本**：如果只是显示文本（即使需要富文本、换行、选择），首选 QLabel
3. **QTextBrowser 用于编辑场景**：只有需要滚动、编辑功能时才用 QTextBrowser/QTextEdit
4. **写最小测试验证假设**：不确定组件行为时，先写小测试验证

### 参考

- Qt 文档：https://doc.qt.io/qt-6/qlabel.html
- Qt 文档：https://doc.qt.io/qt-6/qtextbrowser.html

---

## 2026-06-10: QTextBrowser 布局应避免复杂 CSS

### 问题

对话框多次修改后出现各种问题：
- 头像位置错误（inline 布局失败）
- HTML 结构被破坏
- 流式输出导致内容丢失
- 消息显示异常

### 根本原因

**QTextBrowser 的 CSS 支持非常有限**，而设计时使用了现代 CSS 布局：
- 使用了 `display: inline-flex`, `display: flex`
- 使用了 `align-items`, `vertical-align` 等属性
- 使用了复杂的 table 布局模拟 flexbox

根据 Qt 官方文档，QTextBrowser 只支持：
- 基本的 `display: block`, `display: inline`
- 简单的 `margin`, `padding`, `border`
- 不支持 flexbox, grid, position 等

### 解决：简化设计，拥抱限制

**ChatGPT 风格简化布局**：

```
用户消息：
┌─────────────────────────────────────┐
│ [蓝色背景区域]                       │
│ 用户输入的文本（Markdown 渲染）      │
└─────────────────────────────────────┘

助手消息：
┌─────────────────────────────────────┐
│ [头像]                               │  <- 单独 block，不尝试 inline
├─────────────────────────────────────┤
│ [灰色背景区域]                       │
│ 助手回复（Markdown 渲染）            │
└─────────────────────────────────────┘
```

**设计原则**：
1. **头像单独一行**：不要尝试 inline 布局
2. **只用 block 布局**：用 `margin` 控制间距
3. **用颜色区分**：不依赖复杂边框
4. **避免嵌套 div**：越简单越可靠

### 教训

1. **QTextBrowser 不是浏览器**：它是富文本编辑器，CSS 支持有限
2. **简化优于复杂**：复杂 CSS 布局在 QTextBrowser 中不可靠
3. **拥抱限制**：设计时要考虑平台限制，而不是假设浏览器兼容性
4. **一次设计正确**：反复修改复杂布局会引入更多问题，不如重新设计

### 参考

- [Qt Supported HTML Subset](https://doc.qt.io/qt-6/richtext-html-subset.html)
- ChatGPT 网页版设计参考

---

## 2026-06-10: SSE 长连接超时导致 MCP session 过期

### 问题

客户端使用 FastMCP SSE MCP 服务器时，每次调用工具都返回 404 "session expired"，即使重连后仍然失败。服务器每 15 秒发送 ping，但客户端仍出现超时。

### 原因

1. **对 aiohttp 超时参数理解不准确**：
   - `sock_read=None` 只控制**单次读取**超时
   - `total=30秒` 控制**整个请求**的总时间（累积计时）
   - 即使每次读取都成功（收到 ping），`total` 仍会触发超时

2. **单一 session 管理不合理**：
   - SSE 长连接和普通 POST 请求共用同一个 session
   - SSE 需要无限超时，POST 需要有限超时，两者冲突

3. **重连逻辑不完整**：
   - `_reconnect_fkmcp` 没有检查 SSE session 是否已关闭
   - 如果 session 已关闭，新的 SSE loop 会直接返回

### 解决

使用**双 Session 策略**：

```python
# SSE 长连接 session：无限超时
self._sse_session = aiohttp.ClientSession(
    timeout=aiohttp.ClientTimeout(total=None, sock_read=None),
)

# 普通 POST request session：可配置超时
self._session = aiohttp.ClientSession(
    timeout=aiohttp.ClientTimeout(total=self.timeout, sock_connect=self.timeout),
)
```

并在重连时检查并重建 SSE session。

### 教训

1. **查阅官方文档**：修改网络超时代码时，必须查阅官方文档理解各参数的精确含义，不能凭经验假设
2. **区分连接类型**：短连接（REST API）和长连接（SSE、WebSocket）需要不同的超时策略
3. **添加长时间测试**：对于长连接场景，测试必须运行超过默认超时时间
4. **添加集成测试**：单元测试无法覆盖真实服务器行为，需要添加集成测试连接真实 MCP 服务器
5. **修复后检查相关场景**：修复一个问题后，立即检查相关场景是否也有类似问题

### 参考

- aiohttp 超时文档：https://docs.aiohttp.org/en/stable/client_quickstart.html#timeouts
- SSE 规范：https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events

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

---
## 2026-06-03: Agent 任务完成后继续"自我延伸"

### 问题

用户请求："请列出当前目录下所有的 Python 文件，然后读取 pyproject.toml 的前 20 行。"

Agent 实际行为：
1. ✅ 正确执行了 `glob(**/*.py)` 和 `read(pyproject.toml, limit=20)`
2. ❌ 继续执行了 6 步额外操作，最终试图修改 README.md

Agent 的最终回复是："任务1：在 README.md 中添加'完整中文示例'章节"，与用户意图完全不符。

### 原因

1. **System Prompt 缺乏边界指导**：默认 `"你是一个有帮助的 AI 助手。"` 没有告诉 Agent：
   - 何时应该停止
   - 不应该做用户没要求的事
   - 如何判断任务完成

2. **循环终止条件单一**：Agent Loop 只在 LLM 返回 `END_TURN`（无 tool_calls）时停止。只要 LLM 继续调用工具，循环就不会终止。

3. **没有"任务完成检测"机制**：SDK 有 `StuckDetector` 检测"卡住"，但没有机制检测"任务是否已完成用户意图"。

### 业界最佳实践

根据 [Waylandz ReAct Loop](https://www.waylandz.com/ai-agent-book-en/chapter-02-the-react-loop)、[Pristren Blog](https://pristren.com/blog/prompting-for-agents-guide)、[AI SDK Loop Control](https://ai-sdk.dev/docs/agents/loop-control) 等资料，Agent 应有六大终止条件：

| 条件 | 说明 | 优先级 |
|------|------|--------|
| 用户中断 | 用户主动停止 | 最高 |
| **Task Complete** | LLM 明确表示任务完成 | 高 |
| Budget exhausted | Token/成本限制 | 高 (硬性保护) |
| Timeout | 延迟限制 | 高 (硬性保护) |
| Result converged | 连续观察相似，无新进展 | 中 |
| Max iterations | 达到预设迭代数 | 兜底 |

关键指导：
```markdown
## Stopping Conditions
Stop and provide a Final Answer when:
- You have enough information to answer the user's question accurately
- You have completed the task the user requested

Do NOT continue calling tools when:
- You have already retrieved the information needed to answer
- You are making the same tool call with the same parameters a second time (you are looping)
```

### 解决

改进 System Prompt，添加明确的停止条件和行为边界：

```python
system_prompt: str = """你是一个有帮助的 AI 助手。

## 停止条件

当满足以下条件时，**立即停止并给出最终回答**：
- 你已经获得了回答用户问题所需的全部信息
- 用户请求的任务已经完成
- 遇到无法解决的错误，需要用户输入

## 禁止继续调用工具的情况

- 你已经检索到了回答所需的信息
- 同一个工具调用第二次失败（应向用户报告错误）
- 你正在用相同的参数重复调用同一个工具（这表示你在循环）

## 行为准则

1. **只做用户明确要求的事**：不要延伸任务，不要做用户未请求的操作
2. **任务完成即停止**：完成任务后直接回答，不要继续调用工具
3. **避免无意义的循环**：如果连续两次观察结果相似，停止并报告当前进展

示例：
- 用户："列出 Python 文件" → 执行 glob，列出文件，停止
- 用户："读取文件前 20 行" → 执行 read(limit=20)，展示内容，停止
- 不要在完成后"顺便"做其他事或"改进"项目"""
```

### 教训

1. **System Prompt 是行为边界的关键**：不能只说"有帮助"，必须明确何时停止、何时不该继续
2. **参考业界最佳实践**：成熟的 Agent 框架（Claude Code、AI SDK、LangGraph）都有明确的 Stopping Conditions
3. **"same tool call twice" 检测很重要**：这是防止循环的最常见模式
4. **Task Complete 判断依赖 System Prompt**：SDK 层只能检测"卡住"，"任务完成"需要通过 prompt 引导 LLM 自己判断

### 参考

- [The Anatomy of an Agent Loop | Steve Kinsey](https://stevekinsey.com/writing/agent-loops)
- [Chapter 2: The ReAct Loop | Waylandz](https://www.waylandz.com/ai-agent-book-en/chapter-02-the-react-loop)
- [AI SDK Loop Control](https://ai-sdk.dev/docs/agents/loop-control)
- [Prompting for Agents | Pristren](https://pristren.com/blog/prompting-for-agents-guide)
- 关键文件：`packages/client/src/harness_client/controllers/chat_controller.py`

---

## 2026-06-05: 不查 API 文档凭假设修改导致错误

### 问题

修复"代理 API 不支持 tool role"问题时，凭假设修改了代码：

1. 假设 Anthropic API 有 `role: "tool"` 这个角色
2. 假设兼容模式就是简单地把 `role: "tool"` 改成 `role: "user"` 加点文本前缀
3. 没有查阅官方 API 文档确认正确的消息格式

导致：
- 第一次修改：格式不完整，模型无法正确理解工具结果
- 第二次修改：仍然错误，添加了不必要的复杂逻辑
- 第三次查阅文档后才发现：Anthropic API 根本没有 `role: "tool"`

### 正确的 API 规范

查阅 [Anthropic Tool Use 文档](https://docs.anthropic.com/en/docs/build-with-claude/tool-use) 和搜索结果后发现：

> **Tool results are user messages: There is no tool role. Tool output is sent as a user message containing tool_result blocks.**

正确格式：
```python
# ❌ 错误：没有 role: "tool"
{"role": "tool", "content": "file contents"}

# ✅ 正确：工具结果是 user 角色，内容是 tool_result block
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

### 原因

1. **惰性思维**：凭经验和直觉假设，而不是验证
2. **跳过文档**：查文档需要额外步骤，容易被跳过
3. **惯性思维**：OpenAI API 有 `role: "tool"`，假设 Anthropic 也有

### 解决

正确实现 `_convert_messages`：

```python
def _convert_messages(self, messages):
    converted = []
    for msg in messages:
        if msg.get("role") == "tool":
            # Anthropic API: tool results are user messages with tool_result blocks
            tool_result_block = {
                "type": "tool_result",
                "tool_use_id": msg.get("metadata", {}).get("tool_call_id", ""),
                "content": msg.get("content", ""),
            }
            converted.append({
                "role": "user",
                "content": [tool_result_block],
            })
        else:
            converted.append(msg)
    return converted
```

### 教训

1. **修改 API 相关代码前必须查文档**：不能凭假设，不能凭经验
2. **不同 API 有不同规范**：OpenAI 有 `role: "tool"`，Anthropic 没有
3. **文档查询是开发的一部分**：不是可选项，是必须步骤
4. **用官方来源验证**：Context7、官方文档、API Reference

### 防止措施

**必须查阅文档的场景**（强制）：
- 修改 API 调用格式
- 添加新的 API 参数
- 实现新的消息类型
- 处理 API 响应格式
- 错误处理逻辑

**查阅文档的优先级**：
1. 官方 API Reference（最权威）
2. 官方 SDK 文档
3. Context7 文档索引
4. GitHub 官方示例代码

### 检查方法

```bash
# 使用 Context7 查询 API 文档
# 在 Claude Code 中：直接询问关于 API 的问题

# 确认消息格式
# 问："Anthropic API tool_result 消息格式是什么？"
```

---

## 2026-06-05: Agent 循环检测与熔断器增强

### 问题

模型在完成任务后没有正确停止，继续调用工具直到触发熔断器：
- 同一个工具连续调用 5 次触发熔断器
- 使用的是第三方模型（`xopglm5`），通过 OpenAI 兼容 API 调用
- 系统提示中已有停止条件，但模型未遵守

### 业界最佳实践研究

研究 LangChain、LangGraph、OpenAI、Anthropic 等领先项目的实现：

| 机制 | LangChain | LangGraph | Harness 改进前 | Harness 改进后 |
|------|-----------|-----------|---------------|---------------|
| 迭代上限 | ✅ max_iterations=15 | ✅ recursion_limit=25 | ✅ max_iterations=100 | ✅ 不变 |
| 循环检测 | ⚠️ 需手动实现 | ⚠️ 需手动实现 | ✅ same_tool_threshold=5 | ✅ **增强检测** |
| 主动退出 | ❌ | ✅ remaining_steps | ❌ | ✅ **已添加** |
| tool:args 检测 | ✅ LoopDetector | ⚠️ | ❌ | ✅ **已添加** |

### 解决方案

**Phase 1 - 快速修复**：
1. 提高熔断器阈值：`same_tool_threshold: 5 → 8`（临时缓解）
2. 优化系统提示：使停止条件更明确

**Phase 2 - 根本解决**：

1. **增强熔断器检测**（参考 LangChain LoopDetector）：
```python
# 新增：检测 tool:args 组合调用次数
self._tool_args_counter: Counter[str] = Counter()

# 当同一工具+参数组合调用超过阈值时触发
if count >= self.config.same_args_threshold:
    self._open_reason = f"Tool '{tool_name}' with same arguments called {count} times"
```

2. **添加 remaining_steps 主动退出**（参考 LangGraph）：
```python
# 接近迭代上限时注入提示，让模型优雅收尾
remaining_steps = self.config.max_iterations - iteration
if remaining_steps <= 2 and iteration > 0:
    session.add_message(Message(
        role="user",
        content=f"[系统提示] 还有 {remaining_steps} 步达到迭代上限。请立即总结并给出最终回答。",
        metadata={"type": "remaining_steps_hint", "injected": True},
    ))
```

### Bitter Lesson：序列检测的教训

**最初设计**：添加了工具序列模式检测，检测 `read -> glob -> read -> glob` 这样的交替模式。

**问题**：并行工具调用导致误报。当模型在**单次响应**中调用多个工具时：
```
Iteration 1: LLM 返回 [read(file1), read(file2)]  # 并行调用
```
熔断器错误地检测到 `read -> read` 序列重复，触发熔断。

**根本原因**：并行工具调用是**同一批次**的，不应该被视为"循环"。

**解决**：禁用序列检测（`sequence_window=0`），只保留更可靠的 `tool:args` 检测。

**教训**：
1. **简单规则 > 复杂启发式**（Bitter Lesson）
2. **并行调用会干扰序列检测**：单次响应中的多工具调用会产生误导性的序列
3. **先理解再设计**：设计检测逻辑前，要理解 LLM 的工具调用模式（并行 vs 串行）

### 涉及文件

| 文件 | 改动 |
|------|------|
| `packages/sdk/src/harness/core/circuit_breaker.py` | 增强 tool:args 检测，禁用序列检测 |
| `packages/sdk/src/harness/core/agent_loop.py` | 添加 remaining_steps 主动退出（2026-06-07 真正实现） |
| `packages/client/src/harness_client/controllers/chat_controller.py` | 优化系统提示 |

### 参考

- [LangChain Agent Executor 源码](https://sj-langchain.readthedocs.io/en/latest/_modules/langchain/agents/agent.html)
- [LangGraph GraphRecursionError 处理](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [Why Your LangChain Agent Keeps Calling the Same Tool](https://dev.to/gabrielanhaia/why-your-langchain-agent-keeps-calling-the-same-tool-in-a-loop-and-how-to-stop-it-57gk)
- [LangGraph Best Practices](https://www.swarnendu.de/blog/langgraph-best-practices)

---

## 2026-06-06: 用户消息在第二次 LLM 调用时丢失

### 问题

用户发送消息后，日志显示：

**第一次 LLM 调用**（正确）：
```python
messages = [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "请列出当前目录下所有的 Python 文件..."}
]
```

**第二次 LLM 调用**（错误 - USER 消息丢失）：
```python
messages = [
    {"role": "system", "content": "..."},
    {"role": "tool", "content": "No files found", ...},
    {"role": "tool", "content": "[project]...", ...}
]
```

用户消息 (USER message) 在后续迭代中丢失，导致 LLM 不知道原始任务是什么。

### 原因

**代码设计缺陷**：

```python
# agent_loop.py:431 (原始代码)
context = self.context.build(session, prompt if iteration == 0 else None)

# context_builder.py:240-241
if new_prompt:
    windowed_messages.append(Message(role="user", content=new_prompt))
```

问题分析：
1. `new_prompt` 参数只在 `iteration == 0` 时传入
2. 用户消息被**临时添加**到 `windowed_messages`，没有**持久化**到 `session.messages`
3. 第二次迭代时，`session.messages` 中没有用户消息，`new_prompt` 为 `None`，导致丢失

**根本问题**：违反了"Session 作为单一数据源"原则。消息应该持久化在 session 中，而不是临时添加。

### 解决

在第一次迭代时，将用户消息持久化到 session：

```python
# agent_loop.py:431-434 (修复后)
# Add user message to session on first iteration (fixes USER message loss)
if iteration == 0 and prompt:
    session.add_message(Message(role="user", content=prompt))
context = self.context.build(session)  # 不再需要 new_prompt 参数
```

### 教训

1. **Session 是单一数据源**：所有消息都应该存储在 `session.messages` 中
2. **不要临时添加消息**：消息要么持久化到 session，要么不添加
3. **数据流要清晰**：
   ```
   用户输入 → session.add_message() → 持久化
                                   ↓
   ContextBuilder.build(session) → 从 session 读取
   ```
4. **测试多轮迭代**：需要测试验证多轮迭代后消息完整性

### 检查方法

```python
# 验证消息完整性
for i, msg in enumerate(session.messages):
    print(f"[{i}] {msg.role}: {msg.content[:50]}...")

# 验证 context 构建结果
context = builder.build(session)
user_msgs = [m for m in context.messages if m['role'] == 'user']
assert len(user_msgs) > 0, "USER message should not be lost"
```

### 关键文件

| 文件 | 改动 |
|------|------|
| `packages/sdk/src/harness/core/agent_loop.py` | 在第一次迭代时将用户消息添加到 session |
| `packages/sdk/src/harness/memory/context_builder.py` | 不需要修改，`new_prompt` 参数保留为可选功能 |

---

## 2026-06-06: MCPToolWrapper 缺少 Tool 接口必需属性

### 问题

运行 MCP 工具时报错：

```python
AttributeError: 'MCPToolWrapper' object has no attribute 'input_schema'
AttributeError: 'MCPToolWrapper' object has no attribute 'validate_arguments'
```

### 原因

`MCPToolWrapper` 类设计时只考虑了 MCP 协议需要的属性，没有完整实现 Harness `Tool` 接口：

1. `_input_schema` 私有属性存在，但没有公开的 `input_schema` property
2. `validate_arguments` 方法完全缺失
3. 没有参考 `Tool` 基类的接口规范

### 解决

为 `MCPToolWrapper` 添加缺失的属性和方法：

```python
class MCPToolWrapper:
    @property
    def input_schema(self) -> Dict[str, Any]:
        """Tool input schema (JSON Schema format)."""
        return self._input_schema

    def validate_arguments(
        self,
        arguments: Dict[str, Any],
    ) -> tuple[bool, str | None]:
        """Validate tool arguments using JSON Schema."""
        try:
            import jsonschema
            jsonschema.validate(arguments, self._input_schema)
            return True, None
        except ImportError:
            # Fall back to basic validation
            for field_name in self._required:
                if field_name not in arguments:
                    return False, f"Missing required field: {field_name}"
            return True, None
        except jsonschema.ValidationError as e:
            return False, str(e.message)
        except jsonschema.SchemaError as e:
            return False, f"Invalid schema: {e.message}"
```

### 教训

1. **包装器类要完整实现接口**：如果类要被当作 Tool 使用，必须实现 Tool 接口的所有方法和属性
2. **参考基类设计**：设计包装器时，要检查目标接口的完整定义
3. **添加新功能要测试端到端流程**：只测试了 MCP 连接，没测试实际工具调用
4. **私有属性要有公开访问器**：如果外部代码需要访问属性，要提供 property

### 检查方法

```python
# 检查类是否实现了接口的所有属性
from harness.tools.base import Tool
required_attrs = ['name', 'description', 'input_schema', 'execute', 'validate_arguments']

wrapper = MCPToolWrapper(...)
missing = [attr for attr in required_attrs if not hasattr(wrapper, attr)]
assert not missing, f"Missing attributes: {missing}"
```

### 关键文件

| 文件 | 改动 |
|------|------|
| `packages/sdk/src/harness/mcp/tool_wrapper.py` | 添加 `input_schema` 属性和 `validate_arguments` 方法 |
| `packages/sdk/pyproject.toml` | 添加 `mcp>=1.0.0` 依赖 |

---

## 2026-06-06: 技能文档需要明确的 LLM 执行指令

### 问题

用户请求转换 Markdown 到 Word 时，模型没有运行现有的转换脚本，而是尝试创建新的脚本文件。

### 原因

技能文档（SKILL.md）是为人类用户编写的，缺少明确告诉 LLM 如何执行的指令。模型不知道脚本已经存在，因此尝试自己创建解决方案。

### 解决

在技能文档顶部添加 "⚡ 执行指令（LLM 必读）" 章节：

```markdown
## ⚡ 执行指令（LLM 必读）

**当用户请求转换 Markdown 到 Word 时，你必须：**

1. **直接运行转换脚本**，脚本已存在于技能目录中：
   ```
   python .agent/skills/md-to-word/scripts/md_to_word.py <input.md> [--output <output.docx>]
   ```

**⚠️ 重要提示**：
- 不要尝试创建新脚本，脚本已经存在
- 不要尝试写入临时文件
- 直接使用 bash 工具运行上述命令
```

### 教训

1. **技能文档需要面向 LLM**：技能系统是给 LLM 使用的，文档必须包含明确的执行指令
2. **强调"已存在"**：明确告诉 LLM 脚本/工具已存在，防止模型重复创建
3. **提供具体命令**：给出可以直接复制粘贴的命令，减少模型猜测
4. **添加警告**：明确说明"不要做什么"（如不要创建新脚本）

### 检查方法

```markdown
# 技能文档检查清单
- [ ] 是否有明确的 "LLM 执行指令" 章节？
- [ ] 是否提供了可直接运行的命令？
- [ ] 是否说明了脚本/工具已存在？
- [ ] 是否警告了不要重复创建？
```

### 关键文件

| 文件 | 改动 |
|------|------|
| `~/.harness/skills/md-to-word/SKILL.md` | 添加 "⚡ 执行指令（LLM 必读）" 章节 |

---

## 2026-06-06: 客户端缺少 BashTool 导致技能无法执行

### 问题

用户触发 md-to-word 技能后，模型尝试执行 Python 脚本但失败，因为没有 shell 执行工具。

### 原因

客户端在初始化工具列表时，只注册了 ReadTool、WriteTool、EditTool、GlobTool、GrepTool，但没有注册 BashTool。

### 解决

在客户端默认工具集中添加 BashTool：

```python
# packages/client/src/harness_client/controllers/chat_controller.py
from harness.tools.builtins import (
    ReadTool,
    WriteTool,
    EditTool,
    GlobTool,
    GrepTool,
    BashTool,  # 新增
)

def _init_tools(self) -> list[Tool]:
    return [
        ReadTool(),
        WriteTool(),
        EditTool(),
        GlobTool(),
        GrepTool(),
        BashTool(),  # 新增
    ]
```

### 教训

1. **技能需要执行环境**：如果技能涉及运行脚本或命令，必须有 BashTool
2. **工具集要与能力匹配**：如果 SDK 支持某种能力（如执行命令），客户端应该暴露这个能力
3. **测试技能端到端流程**：不只是测试技能匹配，还要测试实际执行

### 关键文件

| 文件 | 改动 |
|------|------|
| `packages/client/src/harness_client/controllers/chat_controller.py` | 添加 BashTool 到默认工具集 |

---

## 2026-06-06: 统一配置目录便于跨目录使用

### 问题

配置文件（MCP 配置、技能、设置）分散在不同位置：
- MCP 配置在工作目录
- 技能在技能目录
- 设置在平台特定目录

当用户切换工作目录时，MCP 服务器配置"丢失"（实际是在原目录）。

### 解决

统一所有配置到 `~/.harness/` 目录：

```
~/.harness/
├── mcp.json          # MCP 服务器配置
├── settings.json     # 客户端设置
└── skills/           # 技能目录
    └── md-to-word/
        └── SKILL.md
```

### 教训

1. **全局配置 vs 项目配置**：MCP 服务器、技能是"用户级"配置，应该在用户目录
2. **预期行为**：用户期望 MCP 服务器在任何目录都可用
3. **迁移旧配置**：提供自动迁移机制，避免用户手动迁移

### 关键文件

| 文件 | 改动 |
|------|------|
| `packages/client/src/harness_client/utils/settings.py` | 统一配置目录到 `~/.harness/` |
| `packages/sdk/src/harness/security/sandbox.py` | 允许访问 `~/.harness/` 目录 |

---

## 2026-06-07: 达到迭代上限时返回空回复

### 问题

用户执行技能后，任务成功完成（Word 文档已生成），但 UI 显示空回复。

日志显示：
```
LLM response: content_len=0, stop_reason=StopReason.TOOL_USE, tool_calls=1
agent.run() returned, iterations=20
Response length: 0 chars
Response received: EMPTY...
```

### 原因

1. **模型行为**：模型在完成任务后继续尝试执行清理命令，没有给出最终文本回复
2. **循环终止**：达到 `max_iterations=20`，循环终止
3. **返回值缺失**：达到迭代上限时返回的 `LoopResult` 没有设置 `final_response`

```python
# agent_loop.py:754-761 (原始代码)
return LoopResult(
    status=LoopState.ERROR,
    session=session,
    messages=session.messages,
    iterations=iteration,
    error="Max iterations reached",  # 只设置了 error
    token_usage=total_usage,
    # final_response=None  ← 没有设置！
)
```

### 解决

在达到迭代上限时，从 session 中提取最后的助手消息作为回复：

```python
# 尝试从 session 中提取有意义的回复
final_response = None
for msg in reversed(session.messages):
    if msg.role == "assistant" and msg.content:
        final_response = msg.content
        break

return LoopResult(
    status=LoopState.ERROR,
    session=session,
    messages=session.messages,
    final_response=final_response,  # 新增
    iterations=iteration,
    error="Max iterations reached",
    token_usage=total_usage,
)
```

### 教训

1. **边界情况要考虑返回值**：错误终止时也应尽可能提供有意义的回复
2. **模型行为不可预测**：模型可能在完成任务后不停止，需要兜底机制
3. **从历史消息恢复**：session 中可能包含有用的助手消息，可以提取

### 可选改进

在接近迭代上限时注入提醒，让模型优雅收尾：

```python
remaining_steps = self.config.max_iterations - iteration
if remaining_steps <= 2 and iteration > 0:
    session.add_message(Message(
        role="user",
        content=f"[系统提示] 还有 {remaining_steps} 步达到迭代上限。请立即总结并给出最终回答。",
        metadata={"type": "remaining_steps_hint", "injected": True},
    ))
```

### 关键文件

| 文件 | 改动 |
|------|------|
| `packages/sdk/src/harness/core/agent_loop.py` | 达到迭代上限时提取最后的助手消息作为回复 |

---
## 2026-06-08: QTextBrowser 不支持 CSS flexbox

### 问题

客户端聊天面板使用 `display: inline-flex` 布局助手消息头像和内容，但头像 "A" 显示在消息气泡外面，内容显示异常。

### 原因

QTextBrowser 基于 QTextDocument，只支持有限的 CSS 属性：
- **不支持** `display: flex`, `display: inline-flex`, `display: grid` 等现代布局
- **不支持** `align-items`, `justify-content`, `gap` 等 flexbox 属性
- **支持** `display: block`, `display: inline`, `display: inline-block`（有限）

根据 Qt 官方文档 [Supported HTML Subset](https://doc.qt.io/qt-6/richtext-html-subset.html)，支持的 CSS 属性只有：
- `background-color`, `background-image`
- `color`, `font-*`, `text-decoration`
- `margin-*`, `padding-*`
- `border-*`（仅用于表格）
- `vertical-align`（仅用于表格单元格）
- `float`（仅用于表格和图片）

### 解决

使用 HTML `<table>` 布局替代 flexbox：

```html
<!-- ❌ 错误：flexbox 不被支持 -->
<div style="display: inline-flex; align-items: flex-start; gap: 12px;">
    <div>头像</div>
    <div>内容</div>
</div>

<!-- ✅ 正确：使用 table 布局 -->
<table style="border: none; border-spacing: 0;">
    <tr>
        <td width="40" valign="top">头像</td>
        <td valign="top" style="padding-left: 12px;">内容</td>
    </tr>
</table>
```

### 教训

1. **QTextBrowser 不是浏览器**：它是富文本编辑器，CSS 支持非常有限
2. **查阅 Qt 文档**：遇到 CSS 问题，先查 [Supported HTML Subset](https://doc.qt.io/qt-6/richtext-html-subset.html)
3. **使用传统布局**：flexbox/grid 不支持，用 `<table>` + `valign` 替代
4. **如果需要完整 CSS**：考虑使用 QWebEngineView（Chromium 内核）替代 QTextBrowser

### 参考

- [Supported HTML Subset | Qt 6.11.1](https://doc.qt.io/qt-6/richtext-html-subset.html)
- [How good is the HTML and CSS support in QTextBrowser - Qt Forum](https://forum.qt.io/topic/1864/how-good-is-the-html-and-css-support-in-qtextbrowser)

---
## 2026-06-08: 流式 HTML 更新破坏结构

### 问题

尝试实现流式输出（逐字显示）时，助手消息的头像和内容在更新过程中丢失，最后只显示 "A"。

### 原因

QTextBrowser 的 `insertHtml()` 方法会替换选中范围内的所有 HTML 内容，无法保持 HTML 结构：

```python
# 问题流程
1. start_streaming(): append 完整 HTML（包含头像 + 内容占位符）
2. append_streaming_chunk(): select 从占位符到末尾，insertHtml 更新内容
   → 但 insertHtml 替换了整个结构，头像被删除
3. finish_streaming(): 再次 insertHtml
   → 内容变成纯文本，头像丢失
```

### 解决

移除流式模拟功能，直接显示完整消息：

```python
# ❌ 流式更新会破坏 HTML 结构
self.chat_panel.start_streaming()
for chunk in text:
    self.chat_panel.append_streaming_chunk(chunk)
self.chat_panel.finish_streaming()

# ✅ 直接显示完整消息
self.chat_panel.append_assistant_message(response)
```

### 教训

1. **QTextBrowser 不适合流式 HTML**：HTML 结构无法在部分更新中保持
2. **如果需要流式输出**：考虑使用 QWebEngineView 或纯文本流式（不使用 HTML）
3. **先验证可行性**：在实现复杂功能前，先测试基础场景是否可行

### 关键文件

| 文件 | 改动 |
|------|------|
| `packages/client/src/harness_client/ui/chat_panel.py` | 移除流式方法 |
| `packages/client/src/harness_client/ui/main_window.py` | 移除流式模拟 |

---
## 2026-06-08: Unicode 字符作为图标渲染模糊

### 问题

使用 Unicode 字符 `▶` 和 `■` 作为按钮图标，在不同字体下渲染效果不一致，部分用户反映图标模糊。

### 原因

1. **字体依赖**：Unicode 字符的渲染效果取决于系统字体
2. **缩放问题**：在高 DPI 显示器上，字符图标可能模糊
3. **不一致性**：不同系统字体渲染同一字符效果不同

### 解决

使用 QPainter 绘制矢量图标：

```python
from PyQt6.QtGui import QPixmap, QPainter, QPen, QBrush, QColor, QPolygonF
from PyQt6.QtCore import QPointF, Qt, QSize

def create_play_icon(size: int = 24, color: QColor = QColor("white")) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(Qt.PenStyle.NoPen))
    painter.setBrush(QBrush(color))
    
    # 绘制三角形
    triangle = [
        QPointF(6, size // 2),        # 左中心
        QPointF(size - 4, 6),         # 右上
        QPointF(size - 4, size - 6),  # 右下
    ]
    painter.drawPolygon(QPolygonF(triangle))
    painter.end()
    return QIcon(pixmap)
```

### 教训

1. **矢量图标更可靠**：QPainter 绘制的图标在任何分辨率都清晰
2. **避免 Unicode 字符图标**：渲染效果依赖系统字体，不可控
3. **使用 Antialiasing**：`painter.setRenderHint(QPainter.RenderHint.Antialiasing)` 使边缘平滑

### 关键文件

| 文件 | 改动 |
|------|------|
| `packages/client/src/harness_client/ui/chat_panel.py` | 使用 QPainter 绘制图标 |

---

## 2026-06-09: aiohttp 默认超时导致 SSE 流断开

### 问题

FastMCP SSE session 在约 90 秒后过期，客户端 POST 请求返回 404 "Could not find session"。

服务器日志显示：
```
INFO: POST /messages/?session_id=xxx HTTP/1.1" 202 Accepted
# 约 90 秒后
WARNING: Could not find session for ID: xxx
INFO: POST /messages/?session_id=xxx HTTP/1.1" 404 Not Found
```

### 原因分析

最初怀疑是服务器端 session TTL，但 MCP SDK 的 `SseServerTransport` 源码显示 session 只在连接断开时删除，没有独立的 TTL。

**真正原因**：客户端 `aiohttp.ClientTimeout(total=30)` 导致 SSE 流在无活动时超时断开：
```python
# 原代码
self._session = aiohttp.ClientSession(
    timeout=aiohttp.ClientTimeout(total=self.timeout),  # total=30 秒
)
```

`total` 超时对 SSE 流的影响：
- 虽然 aiohttp 在每次收到数据时重置 `total` 超时
- 但如果连接在某个时刻断开（网络问题、代理超时等），session 会被服务器删除
- 下次 POST 请求时 session 已不存在，返回 404

### 解决

为 SSE 流设置无限读取超时：

```python
self._session = aiohttp.ClientSession(
    headers=self.headers,
    timeout=aiohttp.ClientTimeout(
        total=self.timeout,
        sock_read=None,  # 无限等待 SSE 数据
    ),
)
```

`sock_read=None` 允许 SSE 流无限期等待服务器数据。服务器每 15 秒发送 ping，保持连接活跃。

### 教训

1. **SSE 是长连接**：不能使用普通 HTTP 请求的超时配置
2. **`total` vs `sock_read`**：
   - `total`: 整个请求的总超时
   - `sock_read`: 每次读取的超时，对 SSE 更重要
3. **ping 不能解决所有问题**：服务器发送 ping 保持 TCP 连接，但如果客户端超时设置错误，连接仍会断开
4. **区分服务器端和客户端问题**：看到 session 过期，既要检查服务器端 TTL，也要检查客户端超时

### 参考

- [aiohttp ClientTimeout documentation](http://docs.aiohttp.org/en/stable/client_reference.html)
- [SSE best practices](https://medium.com/@jyotsna.a.choudhary/dealing-with-long-running-tasks-in-web-apps-the-sse-approach-ba8607638335)

### 关键文件

| 文件 | 改动 |
|------|------|
| `packages/sdk/src/harness/mcp/transport.py` | 设置 `sock_read=None` 防止 SSE 流超时 |