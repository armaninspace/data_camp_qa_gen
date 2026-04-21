from __future__ import annotations

from pathlib import Path
import json

from course_pipeline.pricing import (
    compute_llm_call_cost,
    fetch_live_pricing_snapshot,
    load_pricing_snapshot,
    persist_pricing_snapshot,
    resolve_pricing_model,
)


_PRICING_HTML = """
<html>
  <body>
    <h2>GPT-5.4</h2>
    <p>Input:</p>
    <p>$2.50 / 1M tokens</p>
    <p>Cached input:</p>
    <p>$0.25 / 1M tokens</p>
    <p>Output:</p>
    <p>$15.00 / 1M tokens</p>
    <h2>GPT-5.4 mini</h2>
    <p>Input:</p>
    <p>$0.75 / 1M tokens</p>
    <p>Cached input:</p>
    <p>$0.075 / 1M tokens</p>
    <p>Output:</p>
    <p>$4.50 / 1M tokens</p>
  </body>
</html>
"""


def test_fetch_live_pricing_snapshot_parses_supported_models() -> None:
    snapshot = fetch_live_pricing_snapshot(
        fetch_text=lambda url: _PRICING_HTML,
        fetched_at="2026-04-21T00:00:00+00:00",
    )

    assert snapshot["source_url"] == "https://openai.com/api/pricing/"
    assert snapshot["models"]["gpt-5.4"]["input_per_1m_usd"] == 2.5
    assert snapshot["models"]["gpt-5.4-mini"]["cached_input_per_1m_usd"] == 0.075
    assert snapshot["models"]["gpt-5.4-mini"]["output_per_1m_usd"] == 4.5


def test_compute_llm_call_cost_handles_cached_tokens_and_snapshot_models() -> None:
    snapshot = fetch_live_pricing_snapshot(
        fetch_text=lambda url: _PRICING_HTML,
        fetched_at="2026-04-21T00:00:00+00:00",
    )

    payload = compute_llm_call_cost(
        pricing_snapshot=snapshot,
        actual_model="gpt-5.4-mini-2026-04-20",
        tokens_in=1000,
        cached_tokens_in=400,
        tokens_out=200,
    )

    assert payload["resolved_pricing_model"] == "gpt-5.4-mini"
    assert payload["billable_tokens_in"] == 600
    assert payload["billable_tokens_out"] == 200
    assert payload["cost_status"] == "ok"
    assert round(payload["cost_input_usd"], 9) == round(600 * 0.75 / 1_000_000, 9)
    assert round(payload["cost_cached_input_usd"], 9) == round(
        400 * 0.075 / 1_000_000, 9
    )
    assert round(payload["cost_output_usd"], 9) == round(200 * 4.5 / 1_000_000, 9)


def test_pricing_snapshot_round_trip(tmp_path: Path) -> None:
    snapshot = fetch_live_pricing_snapshot(
        fetch_text=lambda url: _PRICING_HTML,
        fetched_at="2026-04-21T00:00:00+00:00",
    )
    path = tmp_path / "logs" / "pricing_snapshot.json"

    persist_pricing_snapshot(path, snapshot)
    loaded = load_pricing_snapshot(path)

    assert loaded == snapshot
    assert json.loads(path.read_text(encoding="utf-8"))["models"]["gpt-5.4"]["output_per_1m_usd"] == 15.0


def test_resolve_pricing_model_matches_snapshot_aliases() -> None:
    assert resolve_pricing_model("gpt-5.4-2026-04-20") == "gpt-5.4"
    assert resolve_pricing_model("gpt-5.4-mini") == "gpt-5.4-mini"
    assert resolve_pricing_model("unknown-model") is None
