# Lessons Learned

开发过程中积累的经验教训，避免重复踩坑。

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