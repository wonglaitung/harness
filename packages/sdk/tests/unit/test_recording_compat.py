from __future__ import annotations

import json
from pathlib import Path

from harness.gate.reconciliation import Reconciler
from harness.testing.mock_harness import MockHarness


def test_redact_keeps_content_when_no_unsourced_claims() -> None:
    assert Reconciler.redact("hello", {"unsourced_claims": []}) == "hello"


def test_mock_harness_loads_interactions_recording(tmp_path: Path) -> None:
    recording = tmp_path / "recording.json"
    recording.write_text(
        json.dumps(
            {
                "interactions": [
                    {
                        "type": "llm_response",
                        "data": {
                            "content": "ok",
                            "tool_calls": [],
                            "stop_reason": "end_turn",
                        },
                    },
                    {
                        "type": "tool_result",
                        "data": {
                            "tool_name": "query_balance",
                            "result": "1200",
                            "success": True,
                        },
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    mock = MockHarness()
    mock.load_recording(recording)

    assert len(mock.config.responses) == 1
    assert mock._tool_results["query_balance"] == "1200"
