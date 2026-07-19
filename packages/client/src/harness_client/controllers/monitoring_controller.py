"""
Monitoring Controller for Harness Client.

Manages session metrics and logs from SDK ProgressEvents.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal

if TYPE_CHECKING:
    from harness.types import ProgressEvent

logger = logging.getLogger(__name__)


@dataclass
class SessionMetrics:
    """当前会话的指标数据"""

    # Token 使用
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    # 执行统计
    iterations: int = 0
    tool_calls: int = 0
    tool_success: int = 0
    tool_errors: int = 0
    errors: int = 0

    # 时间
    start_time: datetime | None = None
    end_time: datetime | None = None
    last_update: datetime | None = None
    llm_call_start: float | None = None
    total_llm_duration_ms: float = 0.0

    # 成本估算 (美元)
    # Claude Sonnet 4: $3/$15 per 1M tokens (input/output)
    # GPT-4o: $2.50/$10 per 1M tokens
    cost_usd: float = 0.0

    # 历史记录 (最近 N 次请求的 token 总数)
    token_history: list[int] = field(default_factory=list)

    # 当前请求 token (用于历史记录)
    _current_request_tokens: int = 0

    def total_tokens(self) -> int:
        """总 token 数"""
        return self.input_tokens + self.output_tokens

    def cache_hit_rate(self) -> float:
        """缓存命中率"""
        total = self.input_tokens + self.cache_read_tokens
        if total == 0:
            return 0.0
        return self.cache_read_tokens / total

    def duration_seconds(self) -> float:
        """会话持续时间（秒）"""
        if not self.start_time:
            return 0.0
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()

    def reset(self):
        """重置指标"""
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_read_tokens = 0
        self.cache_write_tokens = 0
        self.iterations = 0
        self.tool_calls = 0
        self.tool_success = 0
        self.tool_errors = 0
        self.errors = 0
        self.start_time = None
        self.end_time = None
        self.last_update = None
        self.llm_call_start = None
        self.total_llm_duration_ms = 0.0
        self.cost_usd = 0.0
        self._current_request_tokens = 0

    def update_cost(self, input_cost_per_1m: float = 3.0, output_cost_per_1m: float = 15.0):
        """
        更新成本估算

        Args:
            input_cost_per_1m: 每 1M input token 的成本（美元）
            output_cost_per_1m: 每 1M output token 的成本（美元）
        """
        input_cost = (self.input_tokens / 1_000_000) * input_cost_per_1m
        output_cost = (self.output_tokens / 1_000_000) * output_cost_per_1m

        # 缓存读取成本更低（通常是正常的 10%）
        cache_cost = (self.cache_read_tokens / 1_000_000) * (input_cost_per_1m * 0.1)

        self.cost_usd = input_cost + output_cost + cache_cost


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: datetime
    event_type: str
    message: str
    duration_ms: float | None = None
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "message": self.message,
            "duration_ms": self.duration_ms,
            "data": self.data,
        }


class MonitoringController(QObject):
    """
    管理会话指标和执行日志。

    响应 SDK ProgressEvent，更新指标数据，通知 UI 更新。
    """

    # 信号
    metrics_updated = pyqtSignal()  # 指标更新
    log_entry_added = pyqtSignal(object)  # LogEntry 对象
    session_started = pyqtSignal()
    session_ended = pyqtSignal()

    # 日志图标映射
    LOG_ICONS = {
        "loop_start": "🚀",
        "loop_end": "✅",
        "iteration": "🔄",
        "llm_call": "🤖",
        "llm_response": "💬",
        "tool_call": "🔧",
        "tool_result": "⚙️",
        "state_change": "📍",
        "error": "❌",
    }

    def __init__(self, max_history: int = 10, max_log_entries: int = 100):
        super().__init__()
        self._metrics = SessionMetrics()
        self._log_entries: list[LogEntry] = []
        self._max_history = max_history
        self._max_log_entries = max_log_entries

        # 工具调用计时
        self._tool_call_start_times: dict[str, float] = {}

        # 模型信息
        self._current_model: str = ""

    @property
    def metrics(self) -> SessionMetrics:
        """获取当前指标"""
        return self._metrics

    @property
    def log_entries(self) -> list[LogEntry]:
        """获取日志条目列表"""
        return self._log_entries

    @property
    def current_model(self) -> str:
        """获取当前模型名称"""
        return self._current_model

    def set_model(self, model: str):
        """设置当前模型"""
        self._current_model = model

    def handle_progress_event(self, event: ProgressEvent):
        """
        处理 SDK ProgressEvent，更新指标和日志。

        Args:
            event: SDK 进度事件
        """
        event_type = event.type.value

        # 更新时间戳
        self._metrics.last_update = datetime.now()

        # 根据事件类型处理
        if event_type == "loop_start":
            self._on_loop_start(event)

        elif event_type == "loop_end":
            self._on_loop_end(event)

        elif event_type == "iteration":
            self._on_iteration(event)

        elif event_type == "llm_call":
            self._on_llm_call(event)

        elif event_type == "llm_response":
            self._on_llm_response(event)

        elif event_type == "tool_call":
            self._on_tool_call(event)

        elif event_type == "tool_result":
            self._on_tool_result(event)

        elif event_type == "error":
            self._on_error(event)

        # 添加日志条目
        self._add_log_entry(event)

        # 通知 UI 更新
        self.metrics_updated.emit()

    def _on_loop_start(self, event: ProgressEvent):
        """处理循环开始事件"""
        self._metrics.reset()
        self._metrics.start_time = datetime.now()
        self._log_entries.clear()
        self.session_started.emit()

    def _on_loop_end(self, event: ProgressEvent):
        """处理循环结束事件"""
        self._metrics.end_time = datetime.now()

        # 记录本次请求的 token 到历史
        if self._metrics._current_request_tokens > 0:
            self._metrics.token_history.append(self._metrics._current_request_tokens)
            if len(self._metrics.token_history) > self._max_history:
                self._metrics.token_history.pop(0)
            self._metrics._current_request_tokens = 0

        # 更新成本
        self._metrics.update_cost()
        self.session_ended.emit()

    def _on_iteration(self, event: ProgressEvent):
        """处理迭代事件"""
        self._metrics.iterations += 1

    def _on_llm_call(self, event: ProgressEvent):
        """处理 LLM 调用开始"""
        self._metrics.llm_call_start = time.time()

    def _on_llm_response(self, event: ProgressEvent):
        """处理 LLM 响应"""
        # 计算延迟
        if self._metrics.llm_call_start:
            duration_ms = (time.time() - self._metrics.llm_call_start) * 1000
            self._metrics.total_llm_duration_ms += duration_ms
            self._metrics.llm_call_start = None

        # 更新 token 使用
        # SDK 发送的格式: {input_tokens, output_tokens, ...} 直接在顶层
        # 也兼容旧格式: {token_usage: {input_tokens, output_tokens}}
        event_data = event.data or {}

        # 优先检查顶层字段（当前 SDK 格式）
        input_tokens = event_data.get("input_tokens", 0)
        output_tokens = event_data.get("output_tokens", 0)
        cache_read = event_data.get("cache_read_tokens", 0)
        cache_write = event_data.get("cache_write_tokens", 0)

        # 如果顶层没有，检查 token_usage 字段（兼容旧格式）
        if not input_tokens and not output_tokens:
            token_usage = event_data.get("token_usage", {})
            if isinstance(token_usage, dict):
                input_tokens = token_usage.get("input_tokens", 0)
                output_tokens = token_usage.get("output_tokens", 0)
                cache_read = token_usage.get("cache_read_tokens", 0)
                cache_write = token_usage.get("cache_write_tokens", 0)

        self._metrics.input_tokens += input_tokens
        self._metrics.output_tokens += output_tokens
        self._metrics.cache_read_tokens += cache_read
        self._metrics.cache_write_tokens += cache_write

        # 累计当前请求 token
        self._metrics._current_request_tokens += input_tokens + output_tokens

        # 更新成本
        self._metrics.update_cost()

    def _on_tool_call(self, event: ProgressEvent):
        """处理工具调用"""
        self._metrics.tool_calls += 1
        event_data = event.data or {}
        tool_name = event_data.get("tool", "unknown")
        self._tool_call_start_times[tool_name] = time.time()

    def _on_tool_result(self, event: ProgressEvent):
        """处理工具结果"""
        event_data = event.data or {}
        tool_name = event_data.get("tool", "unknown")
        success = event_data.get("success", True)

        if success:
            self._metrics.tool_success += 1
        else:
            self._metrics.tool_errors += 1

        # 清理计时
        if tool_name in self._tool_call_start_times:
            del self._tool_call_start_times[tool_name]

    def _on_error(self, event: ProgressEvent):
        """处理错误事件"""
        self._metrics.errors += 1

    def _add_log_entry(self, event: ProgressEvent):
        """添加日志条目"""
        event_type = event.type.value
        event_data = event.data or {}

        # 构建消息
        message = self._build_log_message(event)

        # 创建日志条目
        entry = LogEntry(
            timestamp=event.timestamp,
            event_type=event_type,
            message=message,
            duration_ms=event.duration_ms,
            data=event_data,
        )

        self._log_entries.append(entry)

        # 限制日志条目数量
        if len(self._log_entries) > self._max_log_entries:
            self._log_entries.pop(0)

        # 发送信号
        self.log_entry_added.emit(entry)

    def _build_log_message(self, event: ProgressEvent) -> str:
        """构建日志消息文本"""
        event_type = event.type.value
        event_data = event.data or {}
        message = event.message

        # 根据事件类型构建详细消息
        if event_type == "tool_call":
            tool_name = event_data.get("tool", "unknown")
            return f"调用工具: {tool_name}"

        elif event_type == "tool_result":
            tool_name = event_data.get("tool", "unknown")
            success = event_data.get("success", True)
            status = "成功" if success else "失败"
            return f"工具结果: {tool_name} ({status})"

        elif event_type == "llm_response":
            token_usage = event_data.get("token_usage", {})
            if isinstance(token_usage, dict):
                input_tokens = token_usage.get("input_tokens", 0)
                output_tokens = token_usage.get("output_tokens", 0)
                return f"LLM 响应 (输入: {input_tokens}, 输出: {output_tokens})"
            return "LLM 响应"

        elif event_type == "llm_call":
            model = event_data.get("model", self._current_model)
            return f"LLM 调用: {model}" if model else "LLM 调用"

        elif event_type == "iteration":
            iteration = event_data.get("iteration", 0)
            return f"第 {iteration} 轮迭代"

        elif event_type == "loop_start":
            return "开始执行"

        elif event_type == "loop_end":
            return "执行完成"

        elif event_type == "error":
            error_msg = event_data.get("error", str(event_data))
            return f"错误: {error_msg}"

        return message if message else event_type

    def get_log_icon(self, event_type: str) -> str:
        """获取日志类型的图标"""
        return self.LOG_ICONS.get(event_type, "•")

    def get_recent_latency_ms(self) -> float | None:
        """获取最近一次 LLM 调用的延迟（毫秒）"""
        # 查找最近的 llm_response
        for entry in reversed(self._log_entries):
            if entry.event_type == "llm_response":
                return entry.duration_ms
        return None

    def clear(self):
        """清空指标和日志"""
        self._metrics.reset()
        self._log_entries.clear()
        self._tool_call_start_times.clear()
        self.metrics_updated.emit()
