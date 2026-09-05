"""
Recording harness for capturing real LLM interactions.

Records real interactions for later playback testing.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from harness.sdk.harness import AgentHarness
    from harness.types import LLMResponse, LoopResult, ToolCall

logger = logging.getLogger(__name__)


@dataclass
class RecordingConfig:
    """Configuration for recording."""

    recording_dir: Path = field(default_factory=lambda: Path(".harness_recordings"))
    auto_save: bool = True
    include_metadata: bool = True
    max_recording_size: int = 100  # Max interactions per recording


class RecordingHarness:
    """
    Wraps AgentHarness to record all interactions.

    Records:
    - LLM requests and responses
    - Tool calls and results
    - Agent loop iterations
    - Token usage

    Useful for:
    - Creating test fixtures from real interactions
    - Debugging agent behavior
    - Analyzing costs

    Example:
        >>> from harness import AgentHarness
        >>> harness = AgentHarness(model="claude-sonnet-4-6")
        >>> recorder = RecordingHarness(harness)
        >>>
        >>> # Run and record
        >>> result = await recorder.run("Read the main.py file")
        >>> recorder.save_recording("test_fixture.json")
        >>>
        >>> # Playback
        >>> mock = MockHarness()
        >>> mock.load_recording("test_fixture.json")
    """

    def __init__(
        self,
        harness: AgentHarness,
        config: RecordingConfig | None = None,
    ):
        self.harness = harness
        self.config = config or RecordingConfig()
        self._interactions: list[dict[str, Any]] = []
        self._current_session_id: str | None = None

    def start_recording(self, session_id: str | None = None) -> None:
        """Start recording."""
        self._current_session_id = session_id or "recording"
        self._interactions.clear()

    def record_llm_request(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        system: str | None,
    ) -> None:
        """Record an LLM request."""
        self._interactions.append(
            {
                "type": "llm_request",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "messages": messages,
                    "tools": tools,
                    "system": system,
                },
            }
        )

    def record_llm_response(self, response: LLMResponse) -> None:
        """Record an LLM response."""
        self._interactions.append(
            {
                "type": "llm_response",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "content": response.content,
                    "tool_calls": [tc.to_dict() for tc in response.tool_calls],
                    "stop_reason": response.stop_reason.value,
                    "usage": {
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens,
                    },
                },
            }
        )

    def record_tool_call(self, tool_call: ToolCall) -> None:
        """Record a tool call."""
        self._interactions.append(
            {
                "type": "tool_call",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "id": tool_call.id,
                    "name": tool_call.name,
                    "arguments": tool_call.arguments,
                },
            }
        )

    def record_tool_result(
        self,
        tool_call_id: str,
        tool_name: str,
        result: str,
        success: bool,
    ) -> None:
        """Record a tool result."""
        self._interactions.append(
            {
                "type": "tool_result",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "tool_call_id": tool_call_id,
                    "tool_name": tool_name,
                    "result": result[:5000],  # Truncate large results
                    "success": success,
                },
            }
        )

    def record_loop_result(self, result: LoopResult) -> None:
        """Record final loop result."""
        self._interactions.append(
            {
                "type": "loop_result",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "status": result.status.value,
                    "iterations": result.iterations,
                    "final_response": result.final_response,
                    "token_usage": {
                        "input_tokens": result.token_usage.input_tokens,
                        "output_tokens": result.token_usage.output_tokens,
                    },
                },
            }
        )

    def save_recording(self, name: str) -> Path:
        """
        Save recording to file.

        Args:
            name: Recording name (without extension)

        Returns:
            Path to saved recording
        """
        if not self._interactions:
            logger.warning("No interactions to save")
            return Path()

        # Create recording directory
        self.config.recording_dir.mkdir(parents=True, exist_ok=True)

        # Save
        path = self.config.recording_dir / f"{name}.json"

        recording_data = {
            "version": "1.0",
            "session_id": self._current_session_id,
            "created_at": datetime.now().isoformat(),
            "interactions": self._interactions,
            "metadata": {
                "total_interactions": len(self._interactions),
                "harness_model": self.harness.config.model
                if hasattr(self.harness, "config")
                else "unknown",
            },
        }

        with open(path, "w") as f:
            json.dump(recording_data, f, indent=2)

        logger.info(f"Saved recording to {path}")
        return path

    def get_recording_summary(self) -> dict[str, Any]:
        """Get summary of current recording."""
        if not self._interactions:
            return {"total_interactions": 0}

        llm_requests = sum(1 for i in self._interactions if i["type"] == "llm_request")
        tool_calls = sum(1 for i in self._interactions if i["type"] == "tool_call")

        total_input = 0
        total_output = 0
        for i in self._interactions:
            if i["type"] == "llm_response":
                usage = i["data"].get("usage", {})
                total_input += usage.get("input_tokens", 0)
                total_output += usage.get("output_tokens", 0)

        return {
            "total_interactions": len(self._interactions),
            "llm_requests": llm_requests,
            "tool_calls": tool_calls,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
        }

    def clear_recording(self) -> None:
        """Clear current recording."""
        self._interactions.clear()
        self._current_session_id = None
