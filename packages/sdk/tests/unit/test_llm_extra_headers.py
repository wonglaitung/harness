"""LLM 额外请求头（opencode zen/go 的 `x-opencode-session` 等）的支持。

参考 /data/fortune 的连通性测试：opencode zen/go 端点缺少会话标识头会返回
400 MissingSessionID，因此请求头必须能注入到 LLM 客户端。
"""

from __future__ import annotations

import pytest

from harness.llm.anthropic import AnthropicClient
from harness.llm.openai import OpenAIClient
from harness.sdk.config import HarnessConfig, extra_headers_from_env


def test_extra_headers_from_env_reads_json(monkeypatch):
    monkeypatch.setenv(
        "HARNESS_LLM_EXTRA_HEADERS", '{"x-tenant": "hk", "x-trace": "1"}'
    )
    monkeypatch.delenv("HARNESS_LLM_SESSION_ID", raising=False)

    assert extra_headers_from_env() == {"x-tenant": "hk", "x-trace": "1"}


def test_extra_headers_from_env_session_id(monkeypatch):
    monkeypatch.delenv("HARNESS_LLM_EXTRA_HEADERS", raising=False)
    monkeypatch.setenv("HARNESS_LLM_SESSION_ID", "scraper-42")

    assert extra_headers_from_env() == {"x-opencode-session": "scraper-42"}


def test_extra_headers_from_env_invalid_json_raises(monkeypatch):
    monkeypatch.setenv("HARNESS_LLM_EXTRA_HEADERS", "not-json")

    with pytest.raises(ValueError, match="HARNESS_LLM_EXTRA_HEADERS"):
        extra_headers_from_env()


def test_extra_headers_from_env_empty(monkeypatch):
    monkeypatch.delenv("HARNESS_LLM_EXTRA_HEADERS", raising=False)
    monkeypatch.delenv("HARNESS_LLM_SESSION_ID", raising=False)

    assert extra_headers_from_env() == {}


def test_harness_config_from_env_carries_headers(monkeypatch):
    monkeypatch.setenv("HARNESS_LLM_SESSION_ID", "ci-run")
    monkeypatch.setenv("HARNESS_LLM_EXTRA_HEADERS", '{"x-tenant": "hk"}')

    config = HarnessConfig.from_env()

    assert config.extra_headers == {
        "x-tenant": "hk",
        "x-opencode-session": "ci-run",
    }


def test_openai_client_passes_default_headers(monkeypatch):
    captured: dict[str, object] = {}

    class FakeOpenAI:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setattr("openai.OpenAI", FakeOpenAI)

    client = OpenAIClient(
        api_key="sk-test",
        model="gpt-4o",
        extra_headers={"x-opencode-session": "s1"},
    )
    client._get_client()

    assert captured["default_headers"] == {"x-opencode-session": "s1"}


def test_anthropic_client_passes_default_headers(monkeypatch):
    captured: dict[str, object] = {}

    class FakeAnthropic:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setattr("anthropic.AsyncAnthropic", FakeAnthropic)

    client = AnthropicClient(
        api_key="sk-test",
        model="claude-sonnet-4-6",
        extra_headers={"x-opencode-session": "s1"},
    )
    client._get_client()

    assert captured["default_headers"] == {"x-opencode-session": "s1"}


def test_agent_harness_propagates_extra_headers():
    from harness.sdk.harness import AgentHarness

    agent = AgentHarness(
        model="gpt-4o",
        api_key="sk-test",
        provider="openai",
        extra_headers={"x-opencode-session": "s1"},
    )

    assert agent._llm._extra_headers == {"x-opencode-session": "s1"}
