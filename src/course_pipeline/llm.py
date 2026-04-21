from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any

from openai import OpenAI


@dataclass(frozen=True)
class LLMUsage:
    tokens_in: int | None
    tokens_out: int | None
    cached_tokens_in: int | None = None


@dataclass(frozen=True)
class JSONCompletionResult:
    payload: dict[str, Any]
    response_id: str | None
    actual_model: str | None
    usage: LLMUsage


@dataclass
class LLMClient:
    api_key: str | None
    model: str
    client: Any | None = field(default=None, repr=False)

    def complete_json(self, prompt: str, schema_name: str) -> dict[str, Any]:
        return self.complete_json_result(prompt, schema_name).payload

    def complete_json_result(self, prompt: str, schema_name: str) -> JSONCompletionResult:
        """Run a Responses API call in JSON-object mode and return a plain object."""
        response = self._client().responses.create(
            model=self.model,
            input=prompt,
            text={"format": {"type": "json_object"}},
            metadata={"schema_name": schema_name},
        )

        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text.strip():
            payload = json.loads(output_text)
            if isinstance(payload, dict):
                return JSONCompletionResult(
                    payload=payload,
                    response_id=getattr(response, "id", None),
                    actual_model=getattr(response, "model", None),
                    usage=_extract_usage(response),
                )

        raise ValueError(
            f"OpenAI response did not contain a JSON object for schema={schema_name}"
        )

    def _client(self) -> Any:
        if self.client is not None:
            return self.client
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required when no client is injected")
        self.client = OpenAI(api_key=self.api_key)
        return self.client


def _extract_usage(response: Any) -> LLMUsage:
    usage = getattr(response, "usage", None)
    if usage is None:
        return LLMUsage(tokens_in=None, tokens_out=None, cached_tokens_in=None)
    return LLMUsage(
        tokens_in=_coerce_optional_int(
            getattr(usage, "input_tokens", None) or getattr(usage, "prompt_tokens", None)
        ),
        tokens_out=_coerce_optional_int(
            getattr(usage, "output_tokens", None)
            or getattr(usage, "completion_tokens", None)
        ),
        cached_tokens_in=_extract_cached_tokens(usage),
    )


def _extract_cached_tokens(usage: Any) -> int | None:
    input_details = getattr(usage, "input_tokens_details", None)
    if input_details is not None:
        cached_tokens = _coerce_optional_int(getattr(input_details, "cached_tokens", None))
        if cached_tokens is not None:
            return cached_tokens
    prompt_details = getattr(usage, "prompt_tokens_details", None)
    if prompt_details is not None:
        cached_tokens = _coerce_optional_int(getattr(prompt_details, "cached_tokens", None))
        if cached_tokens is not None:
            return cached_tokens
    return None


def _coerce_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
