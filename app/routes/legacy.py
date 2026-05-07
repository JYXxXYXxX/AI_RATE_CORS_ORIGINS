"""旧版兼容路由（health, analyze-text, analyze-file, jobs, calibration-samples）。"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from app.config import Settings, get_settings
from app.routes.deps import get_analyzer, get_calibrator, get_job_store
from app.schemas import (
    AnalyzeResponse,
    AnalyzeTextRequest,
    CalibrationSampleRequest,
    CalibrationSampleResponse,
    JobCreateResponse,
    JobStatusResponse,
)
from app.services.analyzer import PaperAnalyzer
from app.services.calibration import CalibrationSample, CnkiCalibrator
from app.services.document_loader import extract_text
from app.services.jobs import JobStore

router = APIRouter(tags=["legacy"])


@router.get("/health")
def health(
    settings: Settings = Depends(get_settings),
    calibrator: CnkiCalibrator = Depends(get_calibrator),
) -> dict[str, str | int]:
    db_ok = True
    try:
        from app.db import get_repository
        get_repository().health_check()
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "unavailable",
        "version": settings.service_version,
        "calibration_version": calibrator.version,
        "calibration_samples": len(calibrator.samples),
        "queue_backend": settings.async_queue_backend,
    }


@router.post("/v1/analyze-text", response_model=AnalyzeResponse)
def analyze_text(payload: AnalyzeTextRequest, analyzer: PaperAnalyzer = Depends(get_analyzer)) -> AnalyzeResponse:
    return analyzer.analyze(payload.text, payload.title, payload.subject, payload.degree_level)


@router.post("/v1/analyze-file", response_model=AnalyzeResponse)
async def analyze_file(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    subject: str | None = Form(default=None),
    degree_level: str | None = Form(default=None),
    settings: Settings = Depends(get_settings),
    analyzer: PaperAnalyzer = Depends(get_analyzer),
) -> AnalyzeResponse:
    if file.size is not None and file.size > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="文件过大")
    content = await file.read()
    text = _extract_upload_text(file, content, settings)
    return analyzer.analyze(text, title or file.filename, subject, degree_level)


@router.post("/v1/jobs", response_model=JobCreateResponse)
async def create_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    subject: str | None = Form(default=None),
    degree_level: str | None = Form(default=None),
    settings: Settings = Depends(get_settings),
    jobs: JobStore = Depends(get_job_store),
) -> JobCreateResponse:
    if file.size is not None and file.size > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="文件过大")
    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="文件过大")
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")

    job = jobs.create(title or file.filename, subject, degree_level)
    background_tasks.add_task(
        _run_analysis_job,
        job.job_id,
        file.filename or "",
        content,
        title or file.filename,
        subject,
        degree_level,
    )
    return JobCreateResponse(job_id=job.job_id, status="queued", progress=0, stage="queued")


@router.get("/v1/jobs/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str, jobs: JobStore = Depends(get_job_store)) -> JobStatusResponse:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return jobs.to_status(job)


@router.get("/v1/jobs/{job_id}/report", response_model=AnalyzeResponse)
def get_job_report(job_id: str, jobs: JobStore = Depends(get_job_store)) -> AnalyzeResponse:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if job.status == "failed":
        raise HTTPException(status_code=409, detail=job.error or "任务失败")
    if job.report is None:
        raise HTTPException(status_code=202, detail="报告尚未生成")
    return job.report


@router.post("/v1/calibration-samples", response_model=CalibrationSampleResponse)
def add_calibration_sample(
    payload: CalibrationSampleRequest,
    jobs: JobStore = Depends(get_job_store),
    calibrator: CnkiCalibrator = Depends(get_calibrator),
) -> CalibrationSampleResponse:
    ai_like_score = payload.ai_like_score
    subject = payload.subject
    degree_level = payload.degree_level
    if payload.job_id:
        job = jobs.get(payload.job_id)
        if job is None or job.report is None:
            raise HTTPException(status_code=404, detail="找不到可用于校准的报告")
        ai_like_score = job.report.ai_like_score
        subject = subject or job.report.subject
        degree_level = degree_level or job.report.degree_level

    if ai_like_score is None:
        raise HTTPException(status_code=400, detail="缺少本系统 AI-like 分数")

    cnki_rate = payload.cnki_ai_rate
    if cnki_rate is None and payload.cnki_ai_rate_percent is not None:
        cnki_rate = payload.cnki_ai_rate_percent / 100
    if cnki_rate is None:
        raise HTTPException(status_code=400, detail="缺少知网 AIGC 分数")

    sample_count = calibrator.append_sample(
        CalibrationSample(
            ai_like_score=ai_like_score,
            cnki_ai_rate=cnki_rate,
            subject=subject,
            degree_level=degree_level,
        )
    )
    return CalibrationSampleResponse(
        calibration_version=calibrator.version,
        sample_count=sample_count,
        accepted=True,
    )


def _run_analysis_job(
    job_id: str,
    filename: str,
    content: bytes,
    title: str | None,
    subject: str | None,
    degree_level: str | None,
) -> None:
    jobs = get_job_store()
    settings = get_settings()
    calibrator = get_calibrator()
    analyzer = PaperAnalyzer(settings, calibrator=calibrator)
    try:
        jobs.update(job_id, status="processing", progress=12, stage="extracting_text")
        text = _extract_upload_text_by_name(filename, content, settings)
        jobs.update(job_id, progress=38, stage="segmenting_and_scoring")
        report = analyzer.analyze(text, title or filename, subject, degree_level)
        jobs.update(job_id, status="completed", progress=100, stage="completed", report=report)
    except Exception as exc:  # noqa: BLE001
        jobs.update(job_id, status="failed", progress=100, stage="failed", error=str(exc))
    finally:
        content = b""
        _ = content


def _extract_upload_text(file: UploadFile, content: bytes, settings: Settings) -> str:
    if file.filename and len(file.filename) > 255:
        raise HTTPException(status_code=400, detail="文件名过长（最大 255 字符）")
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="文件过大")
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")
    try:
        return _extract_upload_text_by_name(file.filename or "", content, settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _extract_upload_text_by_name(filename: str, content: bytes, settings: Settings) -> str:
    if len(content) > settings.max_upload_bytes:
        raise ValueError("文件过大")
    text = extract_text(filename, content)
    if not text.strip():
        raise ValueError("未能从文件中提取正文")
    return text
