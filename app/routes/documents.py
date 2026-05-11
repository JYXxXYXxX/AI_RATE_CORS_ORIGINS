"""文档上传、分析、任务、报告相关路由。"""

from __future__ import annotations

import asyncio
from pathlib import Path
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
from fastapi.responses import FileResponse

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
from app.plagiarism.scoring import score_duplication
from app.schemas_unified import (
    AnalysisRunStatusResponse,
    AnalysisTaskCreateResponse,
    AnalysisTaskStatusResponse,
    AnalyzeDocumentResponse,
    DocumentBlockResponse,
    DocumentPatchRequest,
    DocumentPatchResponse,
    DocumentUploadResponse,
    ExportRequest,
    ReanalyzeRequest,
    ReanalyzeResponse,
    ReanalyzeSectionResult,
    RewriteAdviceResponse,
    UnifiedReportResponse,
)
from app.services.analyzer import PaperAnalyzer, risk_level
from app.services.text_processing import preview_text, segment_document
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
            user_id=str(auth.user["id"]) if auth.user is not None else None,
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
                "paragraph_index": sec.get("paragraph_index"),
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


@router.post("/runs/{run_id}/reanalyze", response_model=ReanalyzeResponse)
async def reanalyze_run(
    run_id: str,
    payload: ReanalyzeRequest,
    auth: AuthContext = Depends(get_auth_context),
) -> ReanalyzeResponse:
    """接收改写后的段落，重新计算 AIGC 和查重分数，保持 section_index 不变。"""
    repository = get_repository()
    run = repository.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    ensure_document_access(
        document_id=str(run["document_id"]), auth=auth, repository=repository
    )

    original_sections = repository.list_document_sections(str(run["document_id"]))
    rewritten_map = {s.section_index: s.content for s in payload.sections}

    # 按原始顺序组装当前文本（优先使用改写后内容）
    text_parts: list[str] = []
    for sec in sorted(original_sections, key=lambda s: s.get("section_index", 0)):
        idx = sec.get("section_index", 0)
        text = rewritten_map.get(idx, sec.get("content") or sec.get("text_preview") or "")
        text_parts.append(text)
    full_text = "\n\n".join(text_parts)

    if not full_text.strip():
        raise HTTPException(status_code=400, detail="text is empty after assembly")

    settings = get_settings()

    # 为了保持 section_index 一致，直接对输入的每个 section 评分，而不是重新 segment
    from app.services.text_processing import TextSegment

    input_segments: list[TextSegment] = []
    for sec in payload.sections:
        input_segments.append(
            TextSegment(
                index=sec.section_index,
                text=sec.content,
                section_title=None,
                paragraph_index=sec.section_index,
            )
        )

    # AIGC 重算（在线程池中执行，避免阻塞事件循环）
    analyzer = PaperAnalyzer(settings)
    scored_reports = await asyncio.to_thread(
        lambda: [analyzer._score_segment(seg, input_segments) for seg in input_segments]
    )

    total_chars = sum(r.char_count for r in scored_reports)
    scored_chars = total_chars
    if scored_chars == 0:
        ai_like_score = 0.0
    else:
        weighted = sum(r.ai_like_score * r.char_count for r in scored_reports)
        ai_like_score = weighted / scored_chars

    dispersion = PaperAnalyzer._segment_dispersion(scored_reports)
    predicted_range = analyzer.calibrator.predict_range(
        ai_like_score, dispersion, run.get("subject")
    )
    confidence = analyzer.calibrator.confidence(len(scored_reports), dispersion)

    # 查重重算（本地段落间相似度 + 模板检测，无需 embedding）
    dup_sections: list[dict[str, Any]] = []
    for sec in payload.sections:
        dup_sections.append(
            {
                "section_index": sec.section_index,
                "content": sec.content,
                "text_preview": preview_text(sec.content),
                "char_count": len(sec.content),
                "section_title": None,
            }
        )
    duplication = await asyncio.to_thread(score_duplication, dup_sections)

    dup_map = {s.section_index: s for s in duplication.section_scores}
    sections_result: list[ReanalyzeSectionResult] = []
    for rep in scored_reports:
        dup_sec = dup_map.get(rep.index)
        dup_score = dup_sec.normalized_score if dup_sec else 0.0
        combined_risk = risk_level(max(rep.ai_like_score, dup_score))
        sections_result.append(
            ReanalyzeSectionResult(
                section_index=rep.index,
                section_title=rep.section_title,
                aigc_score=rep.ai_like_score,
                duplication_score=dup_score,
                risk_level=combined_risk,
            )
        )

    return ReanalyzeResponse(
        ai_like_score=round(ai_like_score, 4),
        ai_like_percent=round(ai_like_score * 100, 2),
        duplication_score=duplication.overall_score,
        duplication_percent=round(duplication.overall_score * 100, 2),
        risk_level=risk_level(max(ai_like_score, duplication.overall_score)),
        predicted_cnki_range=f"{predicted_range.label} ({predicted_range.lower_percent:.1f}%-{predicted_range.upper_percent:.1f}%)",
        confidence=f"{confidence:.2f}",
        segment_count=len(scored_reports),
        total_chars=total_chars,
        sections=sections_result,
        disclaimer="本报告为改写后重新计算的 AIGC 疑似风险与知网结果区间预测，不等同于知网、维普、万方或 Turnitin 官方结果。",
    )


@router.get("/documents/{document_id}/original")
async def download_original_document(
    document_id: str,
    auth: AuthContext = Depends(get_auth_context),
):
    """下载用户上传的原始文档文件（docx/pdf/txt等）。"""
    repository = get_repository()
    document = repository.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")
    ensure_document_access(
        document_id=document_id, auth=auth, repository=repository
    )

    original_path = document.get("original_file_path")
    if not original_path:
        raise HTTPException(status_code=404, detail="original file not found")

    file_path = Path(original_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="original file missing on disk")

    suffix = file_path.suffix.lower()
    media_type_map = {
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".pdf": "application/pdf",
        ".txt": "text/plain; charset=utf-8",
        ".md": "text/plain; charset=utf-8",
    }
    media_type = media_type_map.get(suffix, "application/octet-stream")
    filename = document.get("filename") or f"original{suffix}"

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename,
    )


@router.post("/runs/{run_id}/export")
async def export_rewritten_document(
    run_id: str,
    payload: ExportRequest,
    auth: AuthContext = Depends(get_auth_context),
):
    """导出改写后的文档（.docx 或 .txt）。"""
    repository = get_repository()
    db_run = repository.get_run(run_id)
    if db_run is None:
        raise HTTPException(status_code=404, detail="run not found")
    ensure_document_access(
        document_id=str(db_run["document_id"]), auth=auth, repository=repository
    )

    original_sections = repository.list_document_sections(str(db_run["document_id"]))
    rewritten_map = {s.section_index: s.content for s in payload.sections}

    # 组装全文，保持原有顺序
    assembled: list[tuple[int, str | None, str]] = []
    for sec in sorted(original_sections, key=lambda s: s.get("section_index", 0)):
        idx = sec.get("section_index", 0)
        title = sec.get("section_title")
        text = rewritten_map.get(idx, sec.get("content") or sec.get("text_preview") or "")
        assembled.append((idx, title, text))

    doc_title = db_run.get("title") or "rewritten"
    safe_title = _safe_download_name(doc_title) or "rewritten"

    if payload.format == "txt":
        lines: list[str] = []
        if doc_title:
            lines.append(doc_title)
            lines.append("=" * 40)
            lines.append("")
        for _idx, sec_title, text in assembled:
            if sec_title:
                lines.append(sec_title)
                lines.append("-" * 20)
            lines.append(text)
            lines.append("")
        content = "\n".join(lines)
        return Response(
            content=content,
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_title}.txt"'
            },
        )

    # docx
    try:
        from docx import Document
        from docx.shared import Pt
        from docx.oxml.ns import qn
        from docx.oxml import parse_xml
    except ImportError as exc:
        raise HTTPException(status_code=501, detail="docx export not available") from exc

    # 风险颜色映射（浅色背景，适合 Word 文档）
    RISK_COLORS = {
        "high": "FFCDD2",
        "medium": "FFE0B2",
        "low": "E1BEE7",
        "normal": "C8E6C9",
    }

    def _set_para_shading(paragraph, color_hex: str):
        pPr = paragraph._element.get_or_add_pPr()
        shading = parse_xml(
            f'<w:shd xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            f'w:fill="{color_hex}" w:val="clear"/>'
        )
        pPr.append(shading)

    # 尝试基于原始 docx + blocks + patches 导出（新架构）
    original_path = None
    document = repository.get_document(str(db_run["document_id"]))
    if document:
        original_path = document.get("original_file_path")

    # 优先使用 blocks + patches 模式导出
    try:
        blocks = repository.list_document_blocks(str(db_run["document_id"]))
        patches = repository.list_latest_patches_by_run(
            str(db_run["document_id"]), run_id
        )
    except Exception:
        blocks = []
        patches = []

    if blocks and original_path and Path(original_path).suffix.lower() == ".docx" and Path(original_path).exists():
        try:
            from app.services.docx_patch import export_docx_with_patches
            docx_bytes = export_docx_with_patches(original_path, blocks, patches)
            return Response(
                content=docx_bytes,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={
                    "Content-Disposition": f'attachment; filename="{safe_title}.docx"'
                },
            )
        except Exception:
            # 回退到旧逻辑
            pass

    # 回退：基于 sections 的导出（兼容旧数据）
    risk_map = {s.section_index: s.risk_level for s in payload.sections}
    doc = Document()
    if doc_title:
        heading = doc.add_heading(doc_title, level=0)
        heading.alignment = 1  # center

    for idx, sec_title, text in assembled:
        if sec_title:
            doc.add_heading(sec_title, level=1)
        p = doc.add_paragraph(text)
        p.paragraph_format.line_spacing = 1.5
        for run in p.runs:
            run.font.size = Pt(12)
            run.font.name = "宋体"
        # 添加风险背景色
        risk = risk_map.get(idx, "normal")
        _set_para_shading(p, RISK_COLORS.get(risk, "C8E6C9"))

    import io
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_title}.docx"'
        },
    )


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


# ------------------------------------------------------------------
# Document Blocks
# ------------------------------------------------------------------

@router.get("/runs/{run_id}/blocks")
async def get_run_blocks(
    run_id: str,
    auth: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    """获取某个 run 下的所有 blocks（含最新 patch 后的 effective_text）。"""
    repository = get_repository()
    db_run = repository.get_run(run_id)
    if db_run is None:
        raise HTTPException(status_code=404, detail="run not found")
    ensure_document_access(
        document_id=str(db_run["document_id"]), auth=auth, repository=repository
    )

    blocks = repository.list_document_blocks(str(db_run["document_id"]))
    patches = repository.list_latest_patches_by_run(
        str(db_run["document_id"]), run_id
    )
    patch_map = {p["block_id"]: p for p in patches}

    result = []
    for b in blocks:
        patch = patch_map.get(b["block_id"])
        effective_text = patch["new_text"] if patch else b["text"]
        result.append(
            DocumentBlockResponse(
                block_id=b["block_id"],
                block_type=b["block_type"],
                text=b["text"],
                effective_text=effective_text,
                risk_score=b.get("risk_score"),
                rewrite_status="rewritten" if patch else "none",
                source_type=b["source_type"],
                source_map=b.get("source_map"),
                section_title=b.get("section_title"),
                section_type=b.get("section_type"),
                char_count=b.get("char_count", 0),
                display_order=b["display_order"],
            )
        )

    return {"blocks": result}


# ------------------------------------------------------------------
# Document Patches
# ------------------------------------------------------------------

@router.post("/runs/{run_id}/patches")
async def create_patch(
    run_id: str,
    payload: DocumentPatchRequest,
    auth: AuthContext = Depends(get_auth_context),
) -> DocumentPatchResponse:
    """为某个 block 创建改写 patch。"""
    repository = get_repository()
    db_run = repository.get_run(run_id)
    if db_run is None:
        raise HTTPException(status_code=404, detail="run not found")
    ensure_document_access(
        document_id=str(db_run["document_id"]), auth=auth, repository=repository
    )

    patch = repository.insert_document_patch(
        document_id=str(db_run["document_id"]),
        run_id=run_id,
        block_id=payload.block_id,
        old_text=payload.old_text,
        new_text=payload.new_text,
        source_map=payload.source_map,
        created_by=auth.user_id if auth.authenticated else None,
    )

    return DocumentPatchResponse(
        id=str(patch["id"]),
        document_id=str(patch["document_id"]),
        run_id=str(patch["run_id"]) if patch.get("run_id") else None,
        block_id=patch["block_id"],
        old_text=patch["old_text"],
        new_text=patch["new_text"],
        created_at=patch["created_at"].isoformat() if patch.get("created_at") else "",
    )


@router.get("/runs/{run_id}/patches")
async def list_patches(
    run_id: str,
    auth: AuthContext = Depends(get_auth_context),
) -> list[DocumentPatchResponse]:
    """列出某个 run 下的所有 patches。"""
    repository = get_repository()
    db_run = repository.get_run(run_id)
    if db_run is None:
        raise HTTPException(status_code=404, detail="run not found")
    ensure_document_access(
        document_id=str(db_run["document_id"]), auth=auth, repository=repository
    )

    patches = repository.list_document_patches(str(db_run["document_id"]), run_id)
    return [
        DocumentPatchResponse(
            id=str(p["id"]),
            document_id=str(p["document_id"]),
            run_id=str(p["run_id"]) if p.get("run_id") else None,
            block_id=p["block_id"],
            old_text=p["old_text"],
            new_text=p["new_text"],
            created_at=p["created_at"].isoformat() if p.get("created_at") else "",
        )
        for p in patches
    ]
