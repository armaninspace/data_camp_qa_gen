
from __future__ import annotations

from pathlib import Path
import json
import yaml
from pydantic import BaseModel


def append_jsonl(path: str | Path, obj: BaseModel | dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = obj.model_dump() if hasattr(obj, "model_dump") else obj
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def write_yaml(path: str | Path, obj: BaseModel | dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = obj.model_dump() if hasattr(obj, "model_dump") else obj
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            payload,
            f,
            allow_unicode=True,
            sort_keys=False,
            width=80,
        )
