from __future__ import annotations

from datetime import UTC, datetime
from html import unescape
from pathlib import Path
import json
import re
from typing import Any
from urllib.request import Request, urlopen


PRICING_URL = "https://openai.com/api/pricing/"
_TOKEN_DENOMINATOR = 1_000_000
_KNOWN_MODEL_ALIASES = (
    ("gpt-5.4-mini", "gpt-5.4-mini"),
    ("gpt-5.4-nano", "gpt-5.4-nano"),
    ("gpt-5.4", "gpt-5.4"),
)


def fetch_live_pricing_snapshot(
    *,
    fetch_text: Any | None = None,
    fetched_at: str | None = None,
) -> dict[str, Any]:
    html = (
        fetch_text(PRICING_URL)
        if fetch_text is not None
        else _fetch_pricing_page_text(PRICING_URL)
    )
    snapshot = parse_pricing_snapshot(html)
    snapshot["fetched_at"] = fetched_at or datetime.now(UTC).isoformat()
    snapshot["source_url"] = PRICING_URL
    snapshot["source_kind"] = "live_openai_pricing_page"
    return snapshot


def parse_pricing_snapshot(html: str) -> dict[str, Any]:
    text = _html_to_text(html)
    models: dict[str, Any] = {}
    for model_key, display_name in (
        ("gpt-5.4", "GPT-5.4"),
        ("gpt-5.4-mini", "GPT-5.4 mini"),
        ("gpt-5.4-nano", "GPT-5.4 nano"),
    ):
        rates = _parse_model_rates(text, display_name)
        if rates is not None:
            models[model_key] = {
                "display_name": display_name,
                **rates,
            }
    if not models:
        raise ValueError("failed to parse any supported model pricing from live pricing page")
    return {"models": models}


def persist_pricing_snapshot(path: str | Path, snapshot: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")


def load_pricing_snapshot(path: str | Path) -> dict[str, Any] | None:
    target = Path(path)
    if not target.exists():
        return None
    return json.loads(target.read_text(encoding="utf-8"))


def compute_llm_call_cost(
    *,
    pricing_snapshot: dict[str, Any] | None,
    actual_model: str | None,
    tokens_in: int | None,
    cached_tokens_in: int | None,
    tokens_out: int | None,
) -> dict[str, Any]:
    if pricing_snapshot is None:
        return _empty_cost_payload("pricing_unavailable")
    if tokens_in is None or tokens_out is None:
        return _empty_cost_payload("missing_usage")
    resolved_model = resolve_pricing_model(actual_model)
    if resolved_model is None:
        return _empty_cost_payload("unknown_model")
    model_rates = pricing_snapshot.get("models", {}).get(resolved_model)
    if not isinstance(model_rates, dict):
        return _empty_cost_payload("unknown_model")

    safe_cached_tokens = max(0, min(cached_tokens_in or 0, tokens_in))
    billable_tokens_in = max(tokens_in - safe_cached_tokens, 0)
    billable_tokens_out = max(tokens_out, 0)

    cost_input = billable_tokens_in * float(model_rates["input_per_1m_usd"]) / _TOKEN_DENOMINATOR
    cost_cached_input = (
        safe_cached_tokens * float(model_rates["cached_input_per_1m_usd"]) / _TOKEN_DENOMINATOR
    )
    cost_output = billable_tokens_out * float(model_rates["output_per_1m_usd"]) / _TOKEN_DENOMINATOR
    cost_total = cost_input + cost_cached_input + cost_output

    return {
        "resolved_pricing_model": resolved_model,
        "billable_tokens_in": billable_tokens_in,
        "billable_tokens_out": billable_tokens_out,
        "cost_input_usd": cost_input,
        "cost_cached_input_usd": cost_cached_input,
        "cost_output_usd": cost_output,
        "cost_total_usd": cost_total,
        "pricing_version": pricing_snapshot.get("fetched_at"),
        "pricing_source": pricing_snapshot.get("source_url"),
        "cost_status": "ok",
    }


def resolve_pricing_model(model_name: str | None) -> str | None:
    normalized = str(model_name or "").strip().lower()
    for prefix, resolved in _KNOWN_MODEL_ALIASES:
        if normalized == prefix or normalized.startswith(f"{prefix}-"):
            return resolved
    return None


def _fetch_pricing_page_text(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", "ignore")


def _html_to_text(html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", "\n", text)
    text = unescape(text)
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text


def _parse_model_rates(text: str, display_name: str) -> dict[str, float] | None:
    pattern = re.compile(
        rf"{re.escape(display_name)}\s+.*?Input:\s+\$([0-9.]+)\s*/\s*1M tokens\s+"
        rf"Cached input:\s+\$([0-9.]+)\s*/\s*1M tokens\s+"
        rf"Output:\s+\$([0-9.]+)\s*/\s*1M tokens",
        flags=re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(text)
    if match is None:
        return None
    return {
        "input_per_1m_usd": float(match.group(1)),
        "cached_input_per_1m_usd": float(match.group(2)),
        "output_per_1m_usd": float(match.group(3)),
    }


def _empty_cost_payload(cost_status: str) -> dict[str, Any]:
    return {
        "resolved_pricing_model": None,
        "billable_tokens_in": None,
        "billable_tokens_out": None,
        "cost_input_usd": None,
        "cost_cached_input_usd": None,
        "cost_output_usd": None,
        "cost_total_usd": None,
        "pricing_version": None,
        "pricing_source": None,
        "cost_status": cost_status,
    }
