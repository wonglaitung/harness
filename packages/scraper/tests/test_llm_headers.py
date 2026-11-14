"""scraper 的 LLM 配置：环境变量里的额外请求头要传到 AgentHarness。

opencode zen/go 端点要求会话标识头（`x-opencode-session`），缺失会返回
400 MissingSessionID。
"""

from __future__ import annotations

from harness_scraper.config import _merge_llm_config


def test_merge_llm_config_reads_session_id(monkeypatch):
    monkeypatch.setenv("HARNESS_LLM_SESSION_ID", "scraper-7")
    monkeypatch.delenv("HARNESS_LLM_EXTRA_HEADERS", raising=False)

    config = _merge_llm_config({})

    assert config.extra_headers["x-opencode-session"] == "scraper-7"


def test_merge_llm_config_merges_yaml_and_env(monkeypatch):
    monkeypatch.setenv("HARNESS_LLM_EXTRA_HEADERS", '{"x-tenant": "hk"}')
    monkeypatch.delenv("HARNESS_LLM_SESSION_ID", raising=False)

    config = _merge_llm_config({"extra_headers": {"x-region": "hk"}})

    assert config.extra_headers == {"x-region": "hk", "x-tenant": "hk"}


def test_merge_llm_config_without_headers(monkeypatch):
    monkeypatch.delenv("HARNESS_LLM_EXTRA_HEADERS", raising=False)
    monkeypatch.delenv("HARNESS_LLM_SESSION_ID", raising=False)

    config = _merge_llm_config({})

    assert config.extra_headers == {}
