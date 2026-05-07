"""提供商配置与结果相关路由。"""

from fastapi import APIRouter, Depends, HTTPException

from app.db import get_repository
from app.integrations import (
    ConfiguredProviderFetchService,
    ManualProviderImportService,
    ProviderRegistryService,
)
from app.routes.admin import require_admin
from app.routes.deps import (
    AuthContext,
    ensure_document_access,
    get_auth_context,
    get_configured_provider_fetch_service,
    get_manual_import_service,
    get_provider_registry,
)
from app.schemas_unified import (
    ProviderCatalogResponse,
    ProviderConfigDetail,
    ProviderConfigListResponse,
    ProviderConfigSummary,
    ProviderConfigUpdateRequest,
    ProviderFetchRequest,
    ProviderFetchResponse,
    ProviderResultImportRequest,
    ProviderResultImportResponse,
)

router = APIRouter(prefix="/v1", tags=["providers"])


@router.get("/providers", response_model=ProviderCatalogResponse)
def get_provider_catalog(
    registry: ProviderRegistryService = Depends(get_provider_registry),
) -> ProviderCatalogResponse:
    items: list[ProviderConfigSummary] = []
    for detail in registry.list_public_configs():
        items.append(
            ProviderConfigSummary(
                provider=detail["provider"],
                configured=bool(detail["configured"]),
                mode=detail["mode"],
                version=detail["version"],
            )
        )
    return ProviderCatalogResponse(providers=items)


@router.get("/providers/config", response_model=ProviderConfigListResponse)
def get_provider_configs(
    registry: ProviderRegistryService = Depends(get_provider_registry),
) -> ProviderConfigListResponse:
    return ProviderConfigListResponse(
        providers=[
            ProviderConfigDetail.model_validate(item)
            for item in registry.list_public_configs()
        ]
    )


@router.put(
    "/providers/config/{provider}",
    response_model=ProviderConfigDetail,
    dependencies=[Depends(require_admin)],
)
def update_provider_config(
    provider: str,
    payload: ProviderConfigUpdateRequest,
    registry: ProviderRegistryService = Depends(get_provider_registry),
) -> ProviderConfigDetail:
    try:
        config = registry.update_provider_config(provider, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ProviderConfigDetail.model_validate(config)


@router.delete(
    "/providers/config/{provider}",
    response_model=ProviderConfigDetail,
    dependencies=[Depends(require_admin)],
)
def reset_provider_config(
    provider: str,
    registry: ProviderRegistryService = Depends(get_provider_registry),
) -> ProviderConfigDetail:
    try:
        config = registry.reset_provider_config(provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ProviderConfigDetail.model_validate(config)


@router.post("/provider-results/manual", response_model=ProviderResultImportResponse)
def import_manual_provider_result(
    payload: ProviderResultImportRequest,
    importer: ManualProviderImportService = Depends(get_manual_import_service),
    auth: AuthContext = Depends(get_auth_context),
) -> ProviderResultImportResponse:
    ensure_document_access(
        document_id=payload.document_id, auth=auth, repository=get_repository()
    )
    try:
        result = importer.import_result(
            document_id=payload.document_id,
            run_id=payload.run_id,
            provider=payload.provider,
            duplication_percent=payload.duplication_percent,
            aigc_percent=payload.aigc_percent,
            confidence=payload.confidence,
            version=payload.version,
            notes=payload.notes,
            raw_payload=payload.raw_payload,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc

    row = result["payload"]
    return ProviderResultImportResponse(
        payload_id=str(row["id"]),
        document_id=payload.document_id,
        run_id=payload.run_id,
        provider=payload.provider,
        accepted=True,
        created_at=row["created_at"],
    )


@router.post("/provider-results/fetch", response_model=ProviderFetchResponse)
def fetch_provider_result(
    payload: ProviderFetchRequest,
    fetcher: ConfiguredProviderFetchService = Depends(
        get_configured_provider_fetch_service
    ),
    auth: AuthContext = Depends(get_auth_context),
) -> ProviderFetchResponse:
    ensure_document_access(
        document_id=payload.document_id, auth=auth, repository=get_repository()
    )
    try:
        result = fetcher.fetch_and_import(
            document_id=payload.document_id,
            run_id=payload.run_id,
            provider=payload.provider,
            extra_payload=payload.extra_payload,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail="upstream provider error") from exc

    row = result["payload"]
    return ProviderFetchResponse(
        payload_id=str(row["id"]),
        document_id=payload.document_id,
        run_id=payload.run_id,
        provider=payload.provider,
        accepted=True,
        created_at=row["created_at"],
    )
