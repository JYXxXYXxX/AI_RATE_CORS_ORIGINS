"""知网反馈与 OCR 预览路由。"""

from __future__ import annotations

import json
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.db import get_repository
from app.pipeline import UnifiedPipeline
from app.routes.deps import (
    AuthContext,
    ensure_document_access,
    get_auth_context,
    get_proxy_training_service,
    get_unified_pipeline,
)
from app.schemas_unified import CnkiFeedbackOcrPreviewResponse, CnkiFeedbackResponse
from app.services.cnki_ocr import extract_cnki_feedback_preview
from app.training import ProxyTrainingService

router = APIRouter(prefix="/v1", tags=["feedback"])


@router.post(
    "/cnki-feedback/ocr-preview", response_model=CnkiFeedbackOcrPreviewResponse
)
async def preview_cnki_feedback_ocr(
    file: UploadFile = File(...),
) -> CnkiFeedbackOcrPreviewResponse:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="file is empty")
    try:
        preview = extract_cnki_feedback_preview(file.filename or "feedback", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CnkiFeedbackOcrPreviewResponse.model_validate(preview)


@router.post("/cnki-feedback", response_model=CnkiFeedbackResponse)
async def add_cnki_feedback(
    document_id: str = Form(...),
    predicted_run_id: str | None = Form(default=None),
    cnki_dup_percent: float | None = Form(default=None),
    cnki_aigc_percent: float | None = Form(default=None),
    report_date: str | None = Form(default=None),
    notes: str | None = Form(default=None),
    remove_reference_dup_percent: float | None = Form(default=None),
    single_max_dup_percent: float | None = Form(default=None),
    suspected_plagiarism_json: str | None = Form(default=None),
    fragments_json: str | None = Form(default=None),
    learning_consent: bool = Form(default=False),
    learning_scope: str = Form(default="none"),
    evidence_file: UploadFile | None = File(default=None),
    pipeline: UnifiedPipeline = Depends(get_unified_pipeline),
    training_service: ProxyTrainingService = Depends(get_proxy_training_service),
    auth: AuthContext = Depends(get_auth_context),
) -> CnkiFeedbackResponse:
    if cnki_dup_percent is None and cnki_aigc_percent is None:
        raise HTTPException(
            status_code=400, detail="cnki_dup_percent or cnki_aigc_percent is required"
        )
    ensure_document_access(
        document_id=document_id, auth=auth, repository=get_repository()
    )

    parsed_date: date | None = None
    if report_date:
        try:
            parsed_date = date.fromisoformat(report_date)
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail="report_date must be YYYY-MM-DD"
            ) from exc

    details: dict | None = None
    if (
        remove_reference_dup_percent is not None
        or single_max_dup_percent is not None
        or suspected_plagiarism_json
        or fragments_json
    ):
        details = {}
        if remove_reference_dup_percent is not None:
            details["remove_reference_dup_percent"] = remove_reference_dup_percent
        if single_max_dup_percent is not None:
            details["single_max_dup_percent"] = single_max_dup_percent
        if suspected_plagiarism_json:
            try:
                details["suspected_plagiarism"] = json.loads(suspected_plagiarism_json)
            except json.JSONDecodeError:
                pass
        if fragments_json:
            try:
                details["fragments"] = json.loads(fragments_json)
            except json.JSONDecodeError:
                pass

    try:
        result = pipeline.add_cnki_feedback(
            document_id=document_id,
            predicted_run_id=predicted_run_id,
            cnki_dup_percent=cnki_dup_percent,
            cnki_aigc_percent=cnki_aigc_percent,
            report_date=parsed_date,
            notes=notes,
            details=details,
            evidence_file=evidence_file,
            learning_consent=learning_consent,
            learning_scope=learning_scope,
            learning_user_id=auth.user_id if auth.authenticated else None,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc

    auto_train_versions: list[str] = []
    auto_train_triggered = False
    try:
        auto_trained = training_service.auto_train_if_due()
        if auto_trained:
            auto_train_triggered = True
            auto_train_versions = [item["version"] for item in auto_trained]
    except ValueError:
        auto_trained = []
        _ = auto_trained

    feedback = result["feedback"]
    return CnkiFeedbackResponse(
        feedback_id=str(feedback["id"]),
        document_id=str(feedback["document_id"]),
        predicted_run_id=str(feedback["predicted_run_id"])
        if feedback.get("predicted_run_id")
        else None,
        calibration_updated=result["calibration_updated"],
        calibration_version=result["calibration_version"],
        learning_sample_saved=result.get("learning_sample_saved", False),
        learning_skill_updated=result.get("learning_skill_updated", False),
        learning_scope=result.get("learning_scope", "none"),
        auto_train_triggered=auto_train_triggered,
        auto_train_versions=auto_train_versions,
        created_at=feedback["created_at"],
    )
