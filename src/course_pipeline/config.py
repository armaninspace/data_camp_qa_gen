
from __future__ import annotations

from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseModel):
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    model_extract: str = os.getenv("OPENAI_MODEL_EXTRACT", "gpt-5.4")
    model_generate: str = os.getenv("OPENAI_MODEL_GENERATE", "gpt-5.4-mini")
    model_repair: str = os.getenv("OPENAI_MODEL_REPAIR", "gpt-5.4")
    model_answer: str = os.getenv("OPENAI_MODEL_ANSWER", "gpt-5.4")
    model_semantic_primary: str = os.getenv("OPENAI_MODEL_SEMANTIC_PRIMARY", "gpt-5.4")
    model_semantic_review: str = os.getenv("OPENAI_MODEL_SEMANTIC_REVIEW", "gpt-5.4")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    @staticmethod
    def ensure_dir(path: str | Path) -> Path:
        out = Path(path)
        out.mkdir(parents=True, exist_ok=True)
        return out
