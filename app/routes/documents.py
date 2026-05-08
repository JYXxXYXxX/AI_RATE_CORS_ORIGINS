"""文档上传、分析、任务、报告相关路由。"""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import quote

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
)

from app.config import Settings, get_settings
from app.db import get_repository
from app.pipeline import UnifiedPipeline
from app.reporting import render_report_markdown
from app.routes.deps import (
    AuthContext,
    ensure_document_access,
    get_auth_context,
    get_llm_rewrite_service,
    get_unified_pipeline,
    stage_from_status,
)
from app.schemas_unified import (
    AnalysisRunStatusResponse,
    AnalysisTaskCreateResponse,
    AnalysisTaskStatusResponse,
    AnalyzeDocumentResponse,
    DocumentUploadResponse,
    RewriteAdviceResponse,
    UnifiedReportResponse,
)
from app.task_queue import dispatch_analysis_task

router = APIRouter(prefix="/v1", tags=["documents"])


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    subject: str | None = Form(default=None),
    degree_level: str | None = Form(default=None),
    pipeline: UnifiedPipeline = Depends(get_unified_pipeline),
    auth: AuthContext = Depends(get_auth_context),
) -> DocumentUploadResponse:
    try:
        result = await pipeline.upload_document(
            file=file,
            title=title,
            subject=subject,
            degree_level=degree_level,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    document = result.document
    if auth.user is not None:
        pipeline.repository.grant_document_access(
            user_id=str(auth.user["id"]), document_id=str(document["id"])
        )
    return DocumentUploadResponse(
        document_id=str(document["id"]),
        title=document.get("title"),
        filename=document["filename"],
        subject=document.get("subject"),
        degree_level=document.get("degree_level"),
        char_count=document["char_count"],
        status=document["status"],
        reused_existing=result.reused_existing,
        created_at=document["created_at"],
    )


@router.post("/documents/{document_id}/analyze", response_model=AnalyzeDocumentResponse)
async def analyze_uploaded_document(
    document_id: str,
    force: bool = False,
    pipeline: UnifiedPipeline = Depends(get_unified_pipeline),
    auth: AuthContext = Depends(get_auth_context),
) -> AnalyzeDocumentResponse:
    ensure_document_access(
        document_id=document_id, auth=auth, repository=get_repository()
    )
    try:
        result = await asyncio.to_thread(pipeline.analyze_document, document_id, force)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc

    run = result["run"]
    return AnalyzeDocumentResponse(
        run_id=str(run["id"]),
        document_id=str(run["document_id"]),
        status=run["status"],
        created_at=run["created_at"],
        finished_at=run.get("finished_at"),
    )


@router.post(
    "/documents/{document_id}/analyze-async", response_model=AnalysisTaskCreateResponse
)
def analyze_uploaded_document_async(
    document_id: str,
    background_tasks: BackgroundTasks,
    auth: AuthContext = Depends(get_auth_context),
    settings: Settings = Depends(get_settings),
) -> AnalysisTaskCreateResponse:
    repository = get_repository()
    ensure_document_access(document_id=document_id, auth=auth, repository=repository)
    user_id = str(auth.user["id"]) if auth.user is not None else None
    task = repository.create_analysis_task(user_id=user_id, document_id=document_id)
    try:
        dispatch_analysis_task(
            settings=settings,
            task_id=str(task["id"]),
            document_id=document_id,
            user_id=user_id,
            credit_cost=0,
            background_tasks=background_tasks,
        )
    except Exception as exc:  # noqa: BLE001
        repository.mark_analysis_task_failed(str(task["id"]), error_message=str(exc))
        raise HTTPException(
            status_code=500, detail="failed to dispatch async task"
        ) from exc
    return AnalysisTaskCreateResponse(
        task_id=str(task["id"]),
        document_id=str(task["document_id"]),
        status=task["status"],
        progress=int(task["progress"]),
        created_at=task["created_at"],
    )


@router.get("/runs/{run_id}", response_model=AnalysisRunStatusResponse)
def get_analysis_run(
    run_id: str,
    pipeline: UnifiedPipeline = Depends(get_unified_pipeline),
    auth: AuthContext = Depends(get_auth_context),
) -> AnalysisRunStatusResponse:
    run = get_repository().get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    ensure_document_access(
        document_id=str(run["document_id"]), auth=auth, repository=get_repository()
    )
    try:
        return pipeline.build_run_status(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/runs/{run_id}/report", response_model=UnifiedReportResponse)
def get_unified_report(
    run_id: str,
    pipeline: UnifiedPipeline = Depends(get_unified_pipeline),
    auth: AuthContext = Depends(get_auth_context),
) -> UnifiedReportResponse:
    run = get_repository().get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    ensure_document_access(
        document_id=str(run["document_id"]), auth=auth, repository=get_repository()
    )
    report = pipeline.get_report(run_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report not found")
    return UnifiedReportResponse.model_validate(report)


@router.get("/runs/{run_id}/report/markdown")
def get_unified_report_markdown(
    run_id: str,
    pipeline: UnifiedPipeline = Depends(get_unified_pipeline),
    auth: AuthContext = Depends(get_auth_context),
) -> Response:
    run = get_repository().get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    ensure_document_access(
        document_id=str(run["document_id"]), auth=auth, repository=get_repository()
    )
    report = pipeline.get_report(run_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report not found")
    filename = f"{_safe_download_name(report.get('title') or run_id)}-report.md"
    markdown = render_report_markdown(report)
    return Response(
        content=markdown,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
    )


@router.get("/tasks/{task_id}", response_model=AnalysisTaskStatusResponse)
def get_analysis_task_status(
    task_id: str,
    auth: AuthContext = Depends(get_auth_context),
) -> AnalysisTaskStatusResponse:
    repository = get_repository()
    task = repository.get_analysis_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    ensure_document_access(
        document_id=str(task["document_id"]), auth=auth, repository=repository
    )
    return AnalysisTaskStatusResponse(
        task_id=str(task["id"]),
        document_id=str(task["document_id"]),
        run_id=str(task["run_id"]) if task.get("run_id") else None,
        title=task.get("title"),
        filename=task.get("filename"),
        status=task["status"],
        stage=stage_from_status(task["status"]),
        progress=int(task.get("progress", 0)),
        created_at=task["created_at"],
        started_at=task.get("started_at"),
        finished_at=task.get("finished_at"),
        error_message=task.get("error_message"),
    )


@router.get("/runs/{run_id}/sections")
def get_run_sections(
    run_id: str,
    auth: AuthContext = Depends(get_auth_context),
) -> list[dict[str, Any]]:
    """获取论文全文段落（排除参考文献、目录、致谢），附带分数信息。"""
    repository = get_repository()
    run = repository.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    ensure_document_access(
        document_id=str(run["document_id"]), auth=auth, repository=repository
    )

    # 获取所有段落
    sections = repository.list_document_sections(str(run["document_id"]))

    # 获取分数
    scores = repository.list_section_scores(run_id)
    score_map: dict[int, dict[str, Any]] = {}
    for sc in scores:
        idx = sc.get("section_index")
        if idx is not None:
            score_map.setdefault(idx, {})[sc.get("score_type", "")] = sc

    # 组装结果，排除 references / acknowledgement
    skip_types = {"references", "acknowledgement"}
    result: list[dict[str, Any]] = []
    for sec in sections:
        if sec.get("section_type") in skip_types:
            continue
        idx = sec.get("section_index")
        aigc = score_map.get(idx, {}).get("aigc", {})
        dup = score_map.get(idx, {}).get("duplication", {})
        result.append(
            {
                "section_index": idx,
                "section_title": sec.get("section_title"),
                "section_type": sec.get("section_type"),
                "content": sec.get("content") or sec.get("text_preview") or "",
                "char_count": sec.get("char_count", 0),
                "aigc_score": float(aigc.get("normalized_score", 0)) if aigc else 0.0,
                "dup_score": float(dup.get("normalized_score", 0)) if dup else 0.0,
                "risk_level": aigc.get("risk_level", "low") if aigc else "low",
                "reasons": aigc.get("reasons", []) if aigc else [],
            }
        )

    return result


def _safe_download_name(value: str) -> str:
    cleaned = "".join(
        char if char.isascii() and (char.isalnum() or char in {"-", "_"}) else "_"
        for char in value
    )
    return cleaned.strip("_") or "report"


@router.post(
    "/runs/{run_id}/sections/{section_index}/rewrite-advice",
    response_model=RewriteAdviceResponse,
)
async def get_section_rewrite_advice(
    run_id: str,
    section_index: int,
    pipeline: UnifiedPipeline = Depends(get_unified_pipeline),
    llm_service=Depends(get_llm_rewrite_service),
    auth: AuthContext = Depends(get_auth_context),
) -> RewriteAdviceResponse:
    run = get_repository().get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    ensure_document_access(
        document_id=str(run["document_id"]), auth=auth, repository=get_repository()
    )

    report = pipeline.get_report(run_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report not found")

    # 从报告中找到对应段落的风险信息
    section_info = None
    for item in report.get("top_risk_sections", []):
        if item.get("section_index") == section_index:
            section_info = item
            break
    if section_info is None:
        # 也尝试从 chapter_heatmap 里的 section 找，或者直接允许对任意段落改写
        for item in report.get("chapter_heatmap", []):
            # chapter_heatmap 没有 section_index，跳过精确匹配
            pass
        # 如果没有找到，也允许继续，只是缺少风险信息

    # 获取完整段落文本
    sections = get_repository().list_document_sections(str(run["document_id"]))
    target_section = None
    for sec in sections:
        if sec.get("section_index") == section_index:
            target_section = sec
            break
    if target_section is None:
        raise HTTPException(status_code=404, detail="section not found")

    text = target_section.get("content") or target_section.get("text_preview") or ""
    if not text.strip():
        raise HTTPException(status_code=400, detail="section text is empty")

    # 判断风险类型
    aigc_score = float(section_info.get("aigc_score", 0)) if section_info else 0.0
    dup_score = float(section_info.get("duplication_score", 0)) if section_info else 0.0
    if aigc_score >= 0.65 and aigc_score > dup_score:
        risk_type = "aigc"
    elif dup_score >= 0.50 and dup_score >= aigc_score:
        risk_type = "duplication"
    else:
        risk_type = "mixed"

    reasons = section_info.get("reasons") if section_info else []
    subject = report.get("subject")
    degree_level = report.get("degree_level")
    section_title = (
        target_section.get("section_title") or section_info.get("title")
        if section_info
        else None
    )

    # 获取最新知网实测数据，注入 prompt 让建议更精准
    latest_cnki_dup = None
    latest_cnki_aigc = None
    feedback_timeline = report.get("feedback_timeline", [])
    if feedback_timeline:
        latest = feedback_timeline[0]
        latest_cnki_dup = latest.get("cnki_dup_percent")
        latest_cnki_aigc = latest.get("cnki_aigc_percent")

    # 获取该段落的本地分数，用于计算知网-本地差距
    local_aigc_score = float(section_info.get("aigc_score", 0)) if section_info else 0.0
    local_dup_score = (
        float(section_info.get("duplication_score", 0)) if section_info else 0.0
    )

    result = await llm_service.rewrite_paragraph(
        text=text,
        risk_type=risk_type,
        reasons=reasons,
        subject=subject,
        section_title=section_title,
        degree_level=degree_level,
        cnki_dup_percent=latest_cnki_dup,
        cnki_aigc_percent=latest_cnki_aigc,
        local_aigc_score=local_aigc_score,
        local_dup_score=local_dup_score,
    )

    if result.get("error"):
        return RewriteAdviceResponse(
            run_id=run_id,
            section_index=section_index,
            diagnosis="",
            sentences=[],
            rewritten_paragraph="",
            overall_advice="",
            error=result["error"],
        )

    sentences = [
        {
            "original": s.get("original", ""),
            "risk": s.get("risk", "medium"),
            "rewritten": s.get("rewritten", ""),
            "explanation": s.get("explanation", ""),
        }
        for s in result.get("sentences", [])
    ]

    return RewriteAdviceResponse(
        run_id=run_id,
        section_index=section_index,
        diagnosis=result.get("diagnosis", ""),
        sentences=sentences,
        rewritten_paragraph=result.get("rewritten_paragraph", ""),
        overall_advice=result.get("overall_advice", ""),
    )
