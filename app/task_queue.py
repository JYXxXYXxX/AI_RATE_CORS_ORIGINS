from __future__ import annotations

from fastapi import BackgroundTasks

from app.config import Settings
from app.services.analysis_task_runner import run_analysis_task_record


def dispatch_analysis_task(
    *,
    settings: Settings,
    task_id: str,
    document_id: str,
    user_id: str | None,
    credit_cost: int = 0,
    background_tasks: BackgroundTasks | None = None,
) -> str:
    if settings.service_env == "prod" and settings.async_queue_backend == "local":
        raise RuntimeError(
            "local background task backend is disabled in production; use celery"
        )

    if settings.async_queue_backend == "local":
        if background_tasks is None:
            raise ValueError("background_tasks is required for local queue backend")
        background_tasks.add_task(
            run_analysis_task_record, task_id, document_id, user_id, credit_cost
        )
        return "local"

    if settings.async_queue_backend == "celery":
        from app.worker import enqueue_analysis_task

        enqueue_analysis_task(
            task_id=task_id,
            document_id=document_id,
            user_id=user_id,
            credit_cost=credit_cost,
        )
        return "celery"

    raise ValueError(f"unsupported async queue backend: {settings.async_queue_backend}")
