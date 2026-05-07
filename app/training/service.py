from __future__ import annotations

from typing import Any

from app.config import Settings
from app.db.repositories import UnifiedRepository
from app.training.dataset import TrainingDatasetBuilder
from app.training.proxy import train_proxy_model


class ProxyTrainingService:
    def __init__(self, settings: Settings, repository: UnifiedRepository) -> None:
        self.settings = settings
        self.repository = repository
        self.builder = TrainingDatasetBuilder(repository)

    def train(
        self,
        *,
        model_type: str,
        scene_key: str | None,
        activate: bool,
        min_samples: int | None,
    ) -> dict[str, Any]:
        required_samples = min_samples or self.settings.proxy_training_min_samples
        model_types = (
            ["cnki_dup_proxy", "cnki_aigc_proxy"]
            if model_type == "both"
            else [model_type]
        )
        trained_models: list[dict[str, Any]] = []
        dataset_rows = 0

        for current_model_type in model_types:
            rows = self.builder.build_rows(current_model_type, scene_key)
            dataset_rows = max(dataset_rows, len(rows))
            if len(rows) < required_samples:
                raise ValueError(
                    f"{current_model_type} training rows not enough: {len(rows)} < {required_samples}"
                )
            trained = train_proxy_model(
                model_type=current_model_type,
                rows=rows,
                artifact_dir=self.settings.model_artifact_dir,
                feature_version=self.settings.proxy_feature_version,
                scene_key=scene_key,
            )
            self.repository.register_model(
                model_name="cnki_proxy_linear",
                model_type=current_model_type,
                version=trained["version"],
                scene_key=scene_key,
                metrics=trained["metrics"],
                artifact_path=trained["artifact_path"],
                activate=activate,
            )
            trained_models.append(
                {
                    "model_type": current_model_type,
                    "version": trained["version"],
                    "train_count": trained["artifact"]["train_count"],
                    "mae": trained["metrics"]["mae"],
                    "rmse": trained["metrics"]["rmse"],
                    "artifact_path": trained["artifact_path"],
                    "scene_key": scene_key,
                    "activated": activate,
                }
            )

        return {"trained_models": trained_models, "dataset_rows": dataset_rows}

    def auto_train_if_due(self) -> list[dict[str, Any]]:
        if not self.settings.auto_train_enabled:
            return []
        feedback_count = self.repository.count_feedback_records()
        if feedback_count < self.settings.proxy_training_min_samples:
            return []
        if feedback_count % self.settings.auto_train_every_feedbacks != 0:
            return []
        result = self.train(
            model_type="both",
            scene_key=None,
            activate=True,
            min_samples=self.settings.proxy_training_min_samples,
        )
        return list(result["trained_models"])
