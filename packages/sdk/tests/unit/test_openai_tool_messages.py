"""OpenAI 协议回放：tool 结果必须带 tool_call_id，assistant 必须带 tool_calls。

CI 实测报错：``400 ... messages[3]: missing field `tool_call_id```。
根因是内部消息把 id 放在 metadata 里，OpenAI 兼容端点要求顶层字段。
"""

from __future__ import annotations

from typing import Any

import pytest

from harness.llm.openai import OpenAIClient
from harness.sdk.config import HarnessConfig
from harness.sdk.harness import AgentHarness
from harness.tools.base import Tool
from harness.types import LLMResponse, StopReason, ToolCall, ToolResult


def _client() -> OpenAIClient:
    return OpenAIClient(api_key="sk-test", model="test-model")


def test_tool_result_gets_top_level_tool_call_id():
    messages = [
        {"role": "user", "content": "read a"},
        {
            "role": "assistant",
            "content": "",
            "metadata": {
                "tool_calls": [
                    {"id": "call_1", "name": "read", "arguments": {"file_path": "a"}}
                ]
            },
        },
        {
            "role": "tool",
            "content": "data",
            "metadata": {"tool_call_id": "call_1", "tool_name": "read"},
        },
    ]

    converted = _client()._convert_messages(messages)

    assert converted[1] == {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "read", "arguments": '{"file_path": "a"}'},
            }
        ],
    }
    assert converted[2] == {
        "role": "tool",
        "tool_call_id": "call_1",
        "content": "data",
    }
    assert all("metadata" not in message for message in converted)


def test_plain_messages_drop_internal_metadata():
    messages = [
        {"role": "system", "content": "s"},
        {"role": "user", "content": "u"},
        {"role": "assistant", "content": "a", "metadata": {"anything": 1}},
    ]

    converted = _client()._convert_messages(messages)

    assert converted == [
        {"role": "system", "content": "s"},
        {"role": "user", "content": "u"},
        {"role": "assistant", "content": "a"},
    ]


class _EchoTool(Tool):
    capability = "read"
    idempotent = True

    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "echo"

    async def execute(self, arguments: dict[str, Any], context: Any) -> ToolResult:
        return ToolResult(tool_call_id="", success=True, content="ok")


class _ScriptedLLM:
    """第一次返回工具调用，第二次返回最终答案。"""

    model_name = "scripted"

    def __init__(self) -> None:
        self.calls = 0

    async def call(
        self,
        messages: list[dict[str, Any]],
        tools: Any = None,
        system: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        self.calls += 1
        if self.calls == 1:
            return LLMResponse(
                content="",
                tool_calls=[
                    ToolCall(id="call_1", name="echo", arguments={"text": "hi"})
                ],
                stop_reason=StopReason.TOOL_USE,
            )
        return LLMResponse(content="done", stop_reason=StopReason.END_TURN)


@pytest.mark.asyncio
async def test_agent_loop_records_tool_calls_on_assistant_message(tmp_path):
    harness = AgentHarness(
        config=HarnessConfig(
            api_key="sk-test",
            model="scripted",
            memory_dir=str(tmp_path / "memory"),
        ),
        llm_client=_ScriptedLLM(),
    )
    harness.register_tool(_EchoTool())

    result = await harness.run("please echo")

    messages = result.session.messages
    assistant = [
        m for m in messages if m.role == "assistant" and m.metadata.get("tool_calls")
    ]
    tool_message = [m for m in messages if m.role == "tool"]
    assert assistant, "assistant 消息必须记录 tool_calls，供 OpenAI 协议回放"
    assert assistant[0].metadata["tool_calls"][0]["id"] == "call_1"
    assert tool_message and tool_message[0].metadata["tool_call_id"] == "call_1"
