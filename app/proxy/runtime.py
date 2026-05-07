from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from app.db.repositories import UnifiedRepository
from app.proxy.features import FEATURE_NAMES


class ProxyRuntime:
    def __init__(self, repository: UnifiedRepository) -> None:
        self.repository = repository

    def predict(
        self,
        *,
        model_type: str,
        scene_key: str | None,
        features: dict[str, float],
    ) -> dict[str, Any] | None:
        model_row = self.repository.get_active_model(model_type, scene_key)
        if model_row is None or not model_row.get("artifact_path"):
            return None
        artifact = _load_artifact(model_row["artifact_path"])
        vector = np.array(
            [float(features.get(name, 0.0)) for name in artifact["feature_names"]],
            dtype=float,
        )
        means = np.array(artifact["means"], dtype=float)
        stds = np.array(artifact["stds"], dtype=float)
        stds = np.where(stds < 1e-9, 1.0, stds)  # 防止除零
        weights = np.array(artifact["weights"], dtype=float)
        normalized = (vector - means) / stds
        center = float(artifact["intercept"] + normalized @ weights)
        center = max(0.0, min(1.0, center))
        mae = float(
            artifact.get("metrics", {}).get(
                "val_mae", artifact.get("metrics", {}).get("mae", 0.08)
            )
        )
        margin = max(0.04, min(0.18, mae * 1.35))
        confidence = max(
            0.45,
            min(
                0.94, 0.88 - mae * 1.3 + min(0.08, artifact.get("train_count", 0) / 100)
            ),
        )
        return {
            "model_version": model_row["version"],
            "center": round(center, 4),
            "low": round(max(0.0, center - margin), 4),
            "high": round(min(1.0, center + margin), 4),
            "confidence": round(confidence, 4),
            "source": "trained_model",
        }


@lru_cache(maxsize=16)
def _load_artifact(path: str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("feature_names") != FEATURE_NAMES:
        raise ValueError("feature names mismatch")
    return payload
