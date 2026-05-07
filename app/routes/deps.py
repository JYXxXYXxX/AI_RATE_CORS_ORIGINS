"""共享依赖注入函数，供所有路由模块使用。"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from fastapi import Depends, HTTPException, Request

from app.config import Settings, get_settings
from app.db import get_repository
from app.integrations import ConfiguredProviderFetchService, ManualProviderImportService, ProviderRegistryService
from app.main_support import get_calibrator_runtime
from app.pipeline import UnifiedPipeline
from app.services.account import AccountService
from app.services.analyzer import PaperAnalyzer
from app.services.calibration import CnkiCalibrator
from app.services.jobs import JobStore
from app.services.llm_rewrite import LLMRewriteService
from app.training import ProxyTrainingService


@lru_cache
def get_calibrator() -> CnkiCalibrator:
    return get_calibrator_runtime()


@lru_cache
def get_job_store() -> JobStore:
    return JobStore(get_settings())


def get_analyzer(
    settings: Settings = Depends(get_settings),
    calibrator: CnkiCalibrator = Depends(get_calibrator),
) -> PaperAnalyzer:
    return PaperAnalyzer(settings, calibrator=calibrator)


def get_unified_pipeline(
    settings: Settings = Depends(get_settings),
    calibrator: CnkiCalibrator = Depends(get_calibrator),
) -> UnifiedPipeline:
    return UnifiedPipeline(settings, get_repository(), calibrator)


def get_manual_import_service() -> ManualProviderImportService:
    return ManualProviderImportService(get_repository())


def get_provider_registry(settings: Settings = Depends(get_settings)) -> ProviderRegistryService:
    return ProviderRegistryService(settings)


def get_configured_provider_fetch_service(
    settings: Settings = Depends(get_settings),
    registry: ProviderRegistryService = Depends(get_provider_registry),
) -> ConfiguredProviderFetchService:
    return ConfiguredProviderFetchService(settings, get_repository(), registry=registry)


def get_proxy_training_service(settings: Settings = Depends(get_settings)) -> ProxyTrainingService:
    return ProxyTrainingService(settings, get_repository())


def get_account_service(settings: Settings = Depends(get_settings)) -> AccountService:
    return AccountService(settings, get_repository())


def get_llm_rewrite_service(settings: Settings = Depends(get_settings)) -> LLMRewriteService:
    return LLMRewriteService(settings)


@dataclass(frozen=True)
class AuthContext:
    token: str | None
    user: dict[str, Any] | None


def get_auth_context(
    request: Request,
    account_service: AccountService = Depends(get_account_service),
) -> AuthContext:
    # 显式 Authorization Header 优先于 Cookie（便于测试和 API 调用显式指定身份）
    authorization = request.headers.get("Authorization", "")
    token = authorization[7:].strip() if authorization.lower().startswith("bearer ") else None
    if not token:
        token = request.cookies.get("session")
    user = account_service.get_user_by_token(token)
    return AuthContext(token=token, user=user)


def get_current_user(auth: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    if auth.user is None:
        raise HTTPException(status_code=401, detail="authentication required")
    return auth.user


def ensure_document_access(document_id: str, auth: AuthContext, repository: Any) -> None:
    user_id = str(auth.user["id"]) if auth.user is not None else None
    if not repository.can_user_access_document(user_id=user_id, document_id=document_id):
        raise HTTPException(status_code=403, detail="document access denied")


def charge_analysis_credit(*, user_id: str, settings: Settings, source_type: str, source_id: str, note: str) -> bool:
    try:
        get_repository().change_user_credits(
            user_id=user_id,
            delta=-settings.analysis_credit_cost,
            source_type=source_type,
            source_id=source_id,
            note=note,
        )
    except ValueError as exc:
        detail = str(exc)
        if "credits not enough" in detail:
            raise HTTPException(status_code=402, detail="credits not enough") from exc
        if "user not found" in detail:
            raise HTTPException(status_code=404, detail="user not found") from exc
        raise
    return True


def refund_analysis_credit(*, user_id: str, settings: Settings, source_type: str, source_id: str, note: str) -> None:
    get_repository().change_user_credits(
        user_id=user_id,
        delta=settings.analysis_credit_cost,
        source_type=source_type,
        source_id=source_id,
        note=note,
    )


def stage_from_status(status: str) -> str:
    mapping = {
        "queued": "queued",
        "processing": "analyzing",
        "completed": "completed",
        "failed": "failed",
    }
    return mapping.get(status, status)
