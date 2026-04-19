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


def test_complete_json_requires_api_key_without_injected_client() -> None:
    client = LLMClient(api_key=None, model="gpt-5.4")

    with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
        client.complete_json("Return JSON.", "answer")
