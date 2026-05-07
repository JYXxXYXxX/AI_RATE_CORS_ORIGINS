import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any, Literal
from uuid import uuid4

from app.config import Settings
from app.schemas import AnalyzeResponse, JobStatusResponse


JobState = Literal["queued", "processing", "completed", "failed"]


@dataclass
class AnalysisJob:
    job_id: str
    status: JobState
    progress: int
    stage: str
    created_at: datetime
    updated_at: datetime
    title: str | None = None
    subject: str | None = None
    degree_level: str | None = None
    report: AnalyzeResponse | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "progress": self.progress,
            "stage": self.stage,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "title": self.title,
            "subject": self.subject,
            "degree_level": self.degree_level,
            "report": self.report.model_dump() if self.report else None,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnalysisJob":
        return cls(
            job_id=data["job_id"],
            status=data["status"],
            progress=data["progress"],
            stage=data["stage"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            title=data.get("title"),
            subject=data.get("subject"),
            degree_level=data.get("degree_level"),
            report=AnalyzeResponse.model_validate(data["report"]) if data.get("report") else None,
            error=data.get("error"),
        )


class JobStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._jobs: dict[str, AnalysisJob] = {}
        self._lock = Lock()
        self._persist_path = Path(settings.upload_storage_dir).parent / "job_store.json"
        self._load()

    def create(self, title: str | None, subject: str | None, degree_level: str | None) -> AnalysisJob:
        now = datetime.now(UTC)
        job = AnalysisJob(
            job_id=str(uuid4()),
            status="queued",
            progress=0,
            stage="queued",
            created_at=now,
            updated_at=now,
            title=title,
            subject=subject,
            degree_level=degree_level,
        )
        with self._lock:
            self._jobs[job.job_id] = job
            self._prune_locked()
            self._persist_locked()
        return job

    def update(
        self,
        job_id: str,
        *,
        status: JobState | None = None,
        progress: int | None = None,
        stage: str | None = None,
        report: AnalyzeResponse | None = None,
        error: str | None = None,
    ) -> AnalysisJob | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            if status is not None:
                job.status = status
            if progress is not None:
                job.progress = max(0, min(100, progress))
            if stage is not None:
                job.stage = stage
            if report is not None:
                job.report = report
            if error is not None:
                job.error = error
            job.updated_at = datetime.now(UTC)
            self._persist_locked()
            return job

    def get(self, job_id: str) -> AnalysisJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def get_report(self, job_id: str) -> AnalyzeResponse | None:
        job = self.get(job_id)
        if job is None:
            return None
        return job.report

    def to_status(self, job: AnalysisJob) -> JobStatusResponse:
        return JobStatusResponse(
            job_id=job.job_id,
            status=job.status,
            progress=job.progress,
            stage=job.stage,
            error=job.error,
            created_at=job.created_at,
            updated_at=job.updated_at,
            title=job.title,
            subject=job.subject,
            degree_level=job.degree_level,
        )

    def _prune_locked(self) -> None:
        if len(self._jobs) <= self.settings.max_jobs:
            return
        ordered = sorted(self._jobs.values(), key=lambda job: job.updated_at)
        for job in ordered[: len(self._jobs) - self.settings.max_jobs]:
            self._jobs.pop(job.job_id, None)

    def _persist_locked(self) -> None:
        try:
            data = {jid: job.to_dict() for jid, job in self._jobs.items()}
            self._persist_path.write_text(json.dumps(data, ensure_ascii=False, default=str), encoding="utf-8")
        except Exception:
            pass

    def _load(self) -> None:
        if not self._persist_path.exists():
            return
        try:
            raw = json.loads(self._persist_path.read_text(encoding="utf-8"))
            for jid, data in raw.items():
                self._jobs[jid] = AnalysisJob.from_dict(data)
        except Exception:
            pass
