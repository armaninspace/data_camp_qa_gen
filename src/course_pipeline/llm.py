from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any

from openai import OpenAI
from pydantic import RootModel


class JsonObjectResponse(RootModel[dict[str, Any]]):
    pass


@dataclass
class LLMClient:
    api_key: str | None
    model: str
    client: Any | None = field(default=None, repr=False)

    def complete_json(self, prompt: str, schema_name: str) -> dict[str, Any]:
        """Run a structured Responses API call and return a plain JSON object."""
        response = self._client().responses.parse(
            model=self.model,
            input=prompt,
            text_format=JsonObjectResponse,
            metadata={"schema_name": schema_name},
        )

        parsed = getattr(response, "output_parsed", None)
        if parsed is not None:
            payload = parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
            if isinstance(payload, dict):
                return payload

        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text.strip():
            payload = json.loads(output_text)
            if isinstance(payload, dict):
                return payload

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
