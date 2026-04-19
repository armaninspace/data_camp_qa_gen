
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class LLMClient:
    api_key: str | None
    model: str

    def complete_json(self, prompt: str, schema_name: str) -> dict[str, Any]:
        """Placeholder adapter for real OpenAI structured output calls.

        Replace this with the OpenAI SDK implementation the team wants to use.
        Keep the interface thin so stages remain testable without network calls.
        """
        raise NotImplementedError(
            f"Implement structured call for schema={schema_name} model={self.model}"
        )
