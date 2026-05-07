"""模型状态与训练路由。"""

from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings
from app.db import get_repository
from app.routes.admin import require_admin
from app.routes.deps import get_calibrator, get_proxy_training_service
from app.schemas_unified import (
    ModelStatusItem,
    ModelStatusResponse,
    ProxyModelTrainRequest,
    ProxyModelTrainResponse,
    TrainedModelSummary,
)
from app.services.calibration import CnkiCalibrator
from app.training import ProxyTrainingService

router = APIRouter(prefix="/v1", tags=["models"])


@router.get("/models/status", response_model=ModelStatusResponse)
def get_model_status(
    settings: Settings = Depends(get_settings),
    calibrator: CnkiCalibrator = Depends(get_calibrator),
) -> ModelStatusResponse:
    repository = get_repository()
    active_models = repository.list_active_models()
    recent_models = repository.list_recent_models(limit=8)
    return ModelStatusResponse(
        feedback_count=repository.count_feedback_records(),
        calibration_version=calibrator.version,
        auto_train_enabled=settings.auto_train_enabled,
        auto_train_every_feedbacks=settings.auto_train_every_feedbacks,
        active_models=[ModelStatusItem(**item) for item in active_models],
        recent_models=[ModelStatusItem(**item) for item in recent_models],
    )


@router.post(
    "/models/train-proxy",
    response_model=ProxyModelTrainResponse,
    dependencies=[Depends(require_admin)],
)
def train_proxy_models(
    payload: ProxyModelTrainRequest,
    trainer: ProxyTrainingService = Depends(get_proxy_training_service),
) -> ProxyModelTrainResponse:
    try:
        result = trainer.train(
            model_type=payload.model_type,
            scene_key=payload.scene_key,
            activate=payload.activate,
            min_samples=payload.min_samples,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ProxyModelTrainResponse(
        trained_models=[
            TrainedModelSummary(**item) for item in result["trained_models"]
        ],
        dataset_rows=result["dataset_rows"],
    )
