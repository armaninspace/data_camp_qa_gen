from __future__ import annotations

from types import SimpleNamespace

import pytest

from course_pipeline.llm import LLMClient


class FakeResponsesAPI:
    def __init__(self, response: object) -> None:
        self.response = response
        self.calls: list[dict] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return self.response


def test_complete_json_returns_output_text_payload() -> None:
    fake_response = SimpleNamespace(
        output_text='{"items": [1, 2], "status": "ok"}',
    )
    fake_client = SimpleNamespace(responses=FakeResponsesAPI(fake_response))
    client = LLMClient(api_key=None, model="gpt-5.4", client=fake_client)

    payload = client.complete_json("Return JSON.", "topic_extract")

    assert payload == {"items": [1, 2], "status": "ok"}
    assert fake_client.responses.calls[0]["model"] == "gpt-5.4"
    assert fake_client.responses.calls[0]["metadata"] == {"schema_name": "topic_extract"}
    assert fake_client.responses.calls[0]["text"] == {"format": {"type": "json_object"}}


def test_complete_json_falls_back_to_output_text() -> None:
    fake_response = SimpleNamespace(
        output_text='{"result": {"ok": true}}',
    )
    fake_client = SimpleNamespace(responses=FakeResponsesAPI(fake_response))
    client = LLMClient(api_key=None, model="gpt-5.4-mini", client=fake_client)

    payload = client.complete_json("Return JSON.", "answer")

    assert payload == {"result": {"ok": True}}


def test_complete_json_result_extracts_response_metadata_and_usage() -> None:
    fake_response = SimpleNamespace(
        id="resp_123",
        model="gpt-5.4-2026-04-20",
        output_text='{"answer": "ok"}',
        usage=SimpleNamespace(
            input_tokens=120,
            output_tokens=33,
            input_tokens_details=SimpleNamespace(cached_tokens=48),
        ),
    )
    fake_client = SimpleNamespace(responses=FakeResponsesAPI(fake_response))
    client = LLMClient(api_key=None, model="gpt-5.4", client=fake_client)

    result = client.complete_json_result("Return JSON.", "answer")

    assert result.payload == {"answer": "ok"}
    assert result.response_id == "resp_123"
    assert result.actual_model == "gpt-5.4-2026-04-20"
    assert result.usage.tokens_in == 120
    assert result.usage.tokens_out == 33
    assert result.usage.cached_tokens_in == 48


def test_complete_json_result_handles_missing_usage() -> None:
    fake_response = SimpleNamespace(
        output_text='{"answer": "ok"}',
    )
    fake_client = SimpleNamespace(responses=FakeResponsesAPI(fake_response))
    client = LLMClient(api_key=None, model="gpt-5.4", client=fake_client)

    result = client.complete_json_result("Return JSON.", "answer")

    assert result.usage.tokens_in is None
    assert result.usage.tokens_out is None
    assert result.usage.cached_tokens_in is None


def test_complete_json_requires_api_key_without_injected_client() -> None:
    client = LLMClient(api_key=None, model="gpt-5.4")

    with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
        client.complete_json("Return JSON.", "answer")
