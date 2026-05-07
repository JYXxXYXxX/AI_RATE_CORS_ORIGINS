from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from app.proxy.features import FEATURE_NAMES


def train_proxy_model(
    *,
    model_type: str,
    rows: list[dict[str, Any]],
    artifact_dir: str,
    feature_version: str,
    scene_key: str | None,
) -> dict[str, Any]:
    if not rows:
        raise ValueError("no training rows")

    x = np.array(
        [
            [float(row["features"].get(name, 0.0)) for name in FEATURE_NAMES]
            for row in rows
        ],
        dtype=float,
    )
    y = np.array([float(row["label"]) for row in rows], dtype=float)

    means = x.mean(axis=0)
    stds = x.std(axis=0)
    stds = np.where(stds < 1e-6, 1.0, stds)
    x_norm = (x - means) / stds

    # 训练/验证集拆分（80/20），样本少于 10 条时不拆分
    if len(rows) >= 10:
        split_idx = int(len(rows) * 0.8)
        indices = np.random.default_rng(42).permutation(len(rows))
        train_idx, val_idx = indices[:split_idx], indices[split_idx:]
        x_train, x_val = x_norm[train_idx], x_norm[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]
    else:
        x_train, x_val = x_norm, x_norm
        y_train, y_val = y, y

    x_aug = np.concatenate(
        [np.ones((x_train.shape[0], 1), dtype=float), x_train], axis=1
    )
    ridge = 0.06
    penalty = np.eye(x_aug.shape[1], dtype=float) * ridge
    penalty[0, 0] = 0.0
    coeffs = np.linalg.solve(x_aug.T @ x_aug + penalty, x_aug.T @ y_train)

    # 训练集指标
    train_predictions = np.clip(x_aug @ coeffs, 0.0, 1.0)
    train_mae = float(np.mean(np.abs(train_predictions - y_train)))

    # 验证集指标
    x_val_aug = np.concatenate(
        [np.ones((x_val.shape[0], 1), dtype=float), x_val], axis=1
    )
    val_predictions = np.clip(x_val_aug @ coeffs, 0.0, 1.0)
    val_mae = float(np.mean(np.abs(val_predictions - y_val)))
    val_rmse = float(np.sqrt(np.mean((val_predictions - y_val) ** 2)))

    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    version = f"{model_type}-linear-{timestamp}"
    artifact = {
        "model_type": model_type,
        "version": version,
        "scene_key": scene_key,
        "feature_version": feature_version,
        "feature_names": FEATURE_NAMES,
        "means": means.tolist(),
        "stds": stds.tolist(),
        "intercept": float(coeffs[0]),
        "weights": coeffs[1:].tolist(),
        "train_count": len(rows),
        "metrics": {
            "mae": round(val_mae, 6),
            "rmse": round(val_rmse, 6),
            "train_mae": round(train_mae, 6),
            "val_mae": round(val_mae, 6),
            "val_rmse": round(val_rmse, 6),
            "train_count": len(y_train),
            "val_count": len(y_val),
        },
        "created_at": datetime.now(UTC).isoformat(),
    }

    artifact_path = Path(artifact_dir)
    artifact_path.mkdir(parents=True, exist_ok=True)
    file_path = artifact_path / f"{version}.json"
    file_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return {
        "artifact": artifact,
        "artifact_path": str(file_path.resolve()),
        "version": version,
        "metrics": artifact["metrics"],
    }
