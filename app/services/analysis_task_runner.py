from __future__ import annotations

from app.config import get_settings
from app.db import get_repository
from app.main_support import get_calibrator_runtime
from app.pipeline import UnifiedPipeline


def run_analysis_task_record(task_id: str, document_id: str, user_id: str | None, credit_cost: int = 0) -> None:
    repository = get_repository()
    settings = get_settings()
    pipeline = UnifiedPipeline(settings, repository, get_calibrator_runtime())
    repository.mark_analysis_task_processing(task_id, progress=45)
    try:
        result = pipeline.analyze_document(document_id)
        run = result["run"]
        repository.mark_analysis_task_completed(
            task_id,
            run_id=str(run["id"]),
            result_json={"run_id": str(run["id"]), "document_id": document_id},
        )
    except Exception as exc:  # noqa: BLE001 - background task needs durable failure state
        repository.mark_analysis_task_failed(task_id, error_message=str(exc))
        if user_id is not None and credit_cost > 0:
            try:
                repository.change_user_credits(
                    user_id=user_id,
                    delta=credit_cost,
                    source_type="async_analysis_refund",
                    source_id=task_id,
                    note=f"refund async analysis task {task_id}",
                )
            except ValueError:
                pass
