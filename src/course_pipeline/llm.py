from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any

from openai import OpenAI


@dataclass
class LLMClient:
    api_key: str | None
    model: str
    client: Any | None = field(default=None, repr=False)

    def complete_json(self, prompt: str, schema_name: str) -> dict[str, Any]:
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
