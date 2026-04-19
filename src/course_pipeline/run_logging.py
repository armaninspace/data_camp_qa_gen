from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import json
import time


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _append_line(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


@dataclass
class RunLogger:
    run_id: str
    root_dir: Path

    @property
    def logs_dir(self) -> Path:
        return self.root_dir / "logs"

    @property
    def pipeline_log_path(self) -> Path:
        return self.logs_dir / "pipeline.log"

    @property
    def llm_calls_path(self) -> Path:
        return self.logs_dir / "llm_calls.jsonl"

    @property
    def stage_metrics_path(self) -> Path:
        return self.logs_dir / "stage_metrics.jsonl"

    @property
    def publish_log_path(self) -> Path:
        return self.logs_dir / "publish.log"

    @property
    def inspection_log_path(self) -> Path:
        return self.logs_dir / "inspectgion_bundle.log"

    def ensure_files(self) -> None:
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        for path in (
            self.pipeline_log_path,
            self.llm_calls_path,
            self.stage_metrics_path,
            self.publish_log_path,
            self.inspection_log_path,
        ):
            path.touch(exist_ok=True)

    def log_pipeline(self, message: str, *, level: str = "INFO") -> None:
        _append_line(
            self.pipeline_log_path,
            f"{_now_iso()} [{level}] run_id={self.run_id} {message}",
        )

    def log_publish(self, message: str, *, level: str = "INFO") -> None:
        _append_line(
            self.publish_log_path,
            f"{_now_iso()} [{level}] run_id={self.run_id} {message}",
        )

    def log_inspection(self, message: str, *, level: str = "INFO") -> None:
        _append_line(
            self.inspection_log_path,
            f"{_now_iso()} [{level}] run_id={self.run_id} {message}",
        )

    def log_stage_metric(
        self,
        *,
        course_id: str,
        stage: str,
        event: str,
        duration_ms: int,
        input_row_count: int,
        output_row_count: int,
        warning_count: int = 0,
        error_count: int = 0,
    ) -> None:
        payload = {
            "timestamp": _now_iso(),
            "run_id": self.run_id,
            "course_id": course_id,
            "stage": stage,
            "event": event,
            "duration_ms": duration_ms,
            "input_row_count": input_row_count,
            "output_row_count": output_row_count,
            "warning_count": warning_count,
            "error_count": error_count,
        }
        _append_line(
            self.stage_metrics_path,
            json.dumps(payload, ensure_ascii=False),
        )

    def log_llm_call(
        self,
        *,
        course_id: str,
        stage: str,
        prompt_family: str,
        configured_model: str,
        requested_model: str,
        actual_model: str,
        actual_model_source: str,
        provider_request_id: str | None,
        latency_ms: int | None,
        tokens_in: int | None,
        tokens_out: int | None,
        retry_count: int,
        status: str,
    ) -> None:
        payload = {
            "timestamp": _now_iso(),
            "run_id": self.run_id,
            "course_id": course_id,
            "stage": stage,
            "prompt_family": prompt_family,
            "configured_model": configured_model,
            "requested_model": requested_model,
            "actual_model": actual_model,
            "actual_model_source": actual_model_source,
            "provider_request_id": provider_request_id,
            "latency_ms": latency_ms,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "retry_count": retry_count,
            "status": status,
        }
        _append_line(self.llm_calls_path, json.dumps(payload, ensure_ascii=False))


class StageTimer:
    def __init__(
        self,
        logger: RunLogger,
        *,
        course_id: str,
        stage: str,
        input_row_count: int,
    ) -> None:
        self.logger = logger
        self.course_id = course_id
        self.stage = stage
        self.input_row_count = input_row_count
        self.started = time.perf_counter()

    def finish(
        self,
        *,
        output_row_count: int,
        warning_count: int = 0,
        error_count: int = 0,
    ) -> None:
        duration_ms = int((time.perf_counter() - self.started) * 1000)
        self.logger.log_stage_metric(
            course_id=self.course_id,
            stage=self.stage,
            event="completed",
            duration_ms=duration_ms,
            input_row_count=self.input_row_count,
            output_row_count=output_row_count,
            warning_count=warning_count,
            error_count=error_count,
        )
