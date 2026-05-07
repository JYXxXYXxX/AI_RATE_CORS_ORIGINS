from __future__ import annotations

from app.config import get_settings
from app.services.analysis_task_runner import run_analysis_task_record

try:
    from celery import Celery
except ImportError as exc:  # pragma: no cover - only exercised when celery backend is enabled without dependency
    raise RuntimeError(
        "Celery is not installed. Run `pip install -r requirements.txt` before using AI_RATE_ASYNC_QUEUE_BACKEND=celery."
    ) from exc


settings = get_settings()

celery_app = Celery(
    "ai_rate_detector_service",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.update(
    task_default_queue=settings.celery_queue_name,
    task_ignore_result=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=False,
)


@celery_app.task(name="analysis.run_analysis_task")
def run_analysis_task_celery(
    task_id: str,
    document_id: str,
    user_id: str | None,
    credit_cost: int = 0,
) -> None:
    run_analysis_task_record(
        task_id=task_id,
        document_id=document_id,
        user_id=user_id,
        credit_cost=credit_cost,
    )


def enqueue_analysis_task(
    *, task_id: str, document_id: str, user_id: str | None, credit_cost: int = 0
) -> None:
    run_analysis_task_celery.apply_async(
        args=[task_id, document_id, user_id, credit_cost],
        queue=settings.celery_queue_name,
    )
