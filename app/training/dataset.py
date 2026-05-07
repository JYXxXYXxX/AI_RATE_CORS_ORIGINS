from __future__ import annotations

from typing import Any

from app.db.repositories import UnifiedRepository
from app.proxy.features import build_feature_dict_from_snapshot


class TrainingDatasetBuilder:
    def __init__(self, repository: UnifiedRepository) -> None:
        self.repository = repository

    def build_rows(
        self, model_type: str, scene_key: str | None = None
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for record in self.repository.list_feedback_records():
            if scene_key and record.get("scene_key") != scene_key:
                continue
            run_id = record.get("predicted_run_id")
            if not run_id:
                continue
            if model_type == "cnki_dup_proxy":
                label_percent = record.get("cnki_dup_percent")
            else:
                label_percent = record.get("cnki_aigc_percent")
            if label_percent is None:
                continue
            snapshot = self.repository.get_report_snapshot(str(run_id))
            if snapshot is None:
                continue
            provider_payloads = self.repository.list_provider_payloads(str(run_id))
            features = build_feature_dict_from_snapshot(
                snapshot.get("report_json") or {}, provider_payloads
            )
            rows.append(
                {
                    "document_id": str(record["document_id"]),
                    "run_id": str(run_id),
                    "scene_key": record.get("scene_key"),
                    "label_percent": float(label_percent),
                    "label": float(label_percent) / 100.0,
                    "features": features,
                }
            )
        return rows
