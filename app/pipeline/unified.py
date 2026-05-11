from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import UploadFile

from app.config import Settings
from app.db.repositories import UnifiedRepository
from app.plagiarism.scoring import build_embedding_vectors_batch, score_duplication
from app.proxy.features import build_feature_dict_from_runtime
from app.proxy.runtime import ProxyRuntime
from app.reporting.composer import compose_report
from app.schemas_unified import AnalysisRunStatusResponse
from app.services.analyzer import PaperAnalyzer, risk_level
from app.services.calibration import CalibrationSample, CnkiCalibrator
from app.services.document_blocks import parse_document_to_blocks
from app.services.document_loader import convert_doc_to_docx, extract_text
from app.services.text_processing import clean_body_text, preview_text, segment_document


SECTION_TYPE_MAP: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"摘要|abstract", re.IGNORECASE), "abstract"),
    (re.compile(r"引言|绪论|introduction", re.IGNORECASE), "introduction"),
    (re.compile(r"综述|文献回顾|review", re.IGNORECASE), "review"),
    (re.compile(r"方法|研究设计|method", re.IGNORECASE), "method"),
    (re.compile(r"结果|实验|result", re.IGNORECASE), "result"),
    (re.compile(r"讨论|discussion", re.IGNORECASE), "discussion"),
    (re.compile(r"结论|总结|conclusion", re.IGNORECASE), "conclusion"),
    (re.compile(r"参考文献|references", re.IGNORECASE), "references"),
    (re.compile(r"致谢|acknowledg", re.IGNORECASE), "acknowledgement"),
]


@dataclass(frozen=True)
class UploadResult:
    document: dict[str, Any]
    reused_existing: bool


class UnifiedPipeline:
    def __init__(
        self,
        settings: Settings,
        repository: UnifiedRepository,
        calibrator: CnkiCalibrator,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.calibrator = calibrator
        self.proxy_runtime = ProxyRuntime(repository)

    async def upload_document(
        self,
        *,
        file: UploadFile,
        title: str | None,
        subject: str | None,
        degree_level: str | None,
        user_id: str | None = None,
    ) -> UploadResult:
        # 优先通过 Content-Length 预检，避免一次性读取大文件耗尽内存
        if file.size is not None and file.size > self.settings.max_upload_bytes:
            raise ValueError("文件过大")
        content = await file.read()
        if len(content) > self.settings.max_upload_bytes:
            raise ValueError("文件过大")
        if not content:
            raise ValueError("文件为空")

        filename = file.filename or "paper.txt"
        if len(filename) > 255:
            raise ValueError("文件名过长（最大 255 字符）")
        raw_text = extract_text(filename, content)
        cleaned_text = clean_body_text(raw_text)
        if not cleaned_text.strip():
            raise ValueError("未能从文件中提取可分析正文")

        doc_hash = hashlib.sha256(cleaned_text.encode("utf-8")).hexdigest()
        # 匿名用户不启用 hash 去重，避免复用到带权限限制的已有文档
        existing = None if user_id is None else self.repository.get_document_by_hash(doc_hash)

        # doc 文件尝试转换为 docx
        if filename.lower().endswith(".doc"):
            converted = convert_doc_to_docx(content, self.settings.upload_storage_dir)
            if converted:
                original_path = converted
                filename = Path(converted).name
            else:
                original_path = self._write_binary(
                    self.settings.upload_storage_dir, filename, content
                )
        else:
            original_path = self._write_binary(
                self.settings.upload_storage_dir, filename, content
            )

        cleaned_path = self._write_text(
            self.settings.cleaned_storage_dir, filename, cleaned_text
        )

        document = self.repository.upsert_document(
            title=title or Path(filename).stem,
            filename=filename,
            subject=subject,
            degree_level=degree_level,
            language=_detect_language(cleaned_text),
            doc_hash=doc_hash,
            char_count=len(cleaned_text),
            source_type="upload",
            original_file_path=original_path,
            cleaned_text_path=cleaned_path,
        )

        # 解析并持久化 document blocks（ graceful fallback ）
        try:
            source_type = Path(filename).suffix.lower().lstrip(".")
            if source_type not in ("docx", "pdf", "doc", "txt", "md"):
                source_type = "txt"
            blocks = parse_document_to_blocks(original_path, source_type)
            if blocks and not existing:
                self.repository.insert_document_blocks(
                    str(document["id"]),
                    [b.__dict__ for b in blocks],
                )
        except Exception:
            # 如果 blocks 表不存在或解析失败，不影响主流程
            import logging
            logging.getLogger(__name__).warning(
                "Failed to parse blocks for document %s", document["id"], exc_info=True
            )

        return UploadResult(document=document, reused_existing=existing is not None)

    def analyze_document(self, document_id: str, force: bool = False) -> dict[str, Any]:
        document = self.repository.get_document(document_id)
        if document is None:
            raise ValueError("document not found")

        # 检查是否已有完成的分析结果，避免重复推理（force=true 时跳过缓存）
        if not force:
            existing_runs = self.repository.list_completed_runs(document_id)
            if existing_runs:
                latest_run = existing_runs[0]
                report = self.repository.get_report_snapshot(str(latest_run["id"]))
                if report is not None:
                    return {"run": latest_run, "report": report["report_json"]}
            # 检查是否已有正在处理中的分析，防止并发重复分析
            processing_runs = self.repository.list_processing_runs(document_id)
            if processing_runs:
                raise ValueError("该文档已有分析任务正在处理中，请勿重复提交")

        cleaned_text_path = document.get("cleaned_text_path")
        if not cleaned_text_path:
            raise ValueError("document text path missing")
        cleaned_text = Path(cleaned_text_path).read_text(encoding="utf-8")

        run = self.repository.create_analysis_run(
            document_id=document_id,
            run_type="full_analysis",
            provider="local",
            provider_version=self.settings.unified_proxy_model_version,
        )
        self.repository.mark_document_status(document_id, "processing")
        self.repository.mark_run_processing(run["id"])

        try:
            stored_sections = self.repository.list_document_sections(document_id)
            if stored_sections:
                sections = stored_sections
            else:
                raw_sections = segment_document(cleaned_text, self.settings)
                # 批量生成 embedding 向量（比逐条快 3-5x）
                section_texts = [item.text for item in raw_sections]
                embeddings = build_embedding_vectors_batch(section_texts)
                sections = self.repository.insert_document_sections(
                    document_id,
                    [
                        {
                            "section_index": item.index,
                            "paragraph_index": item.paragraph_index,
                            "section_type": _infer_section_type(item.section_title),
                            "section_title": item.section_title,
                            "text_preview": preview_text(item.text, limit=160),
                            "content": item.text,
                            "char_count": len(item.text),
                            "embedding": emb,
                        }
                        for item, emb in zip(raw_sections, embeddings)
                    ],
                )
            self.repository.mark_document_status(
                document_id, "processing", section_count=len(sections)
            )

            analyzer = PaperAnalyzer(self.settings, calibrator=self.calibrator)
            ai_report = analyzer.analyze(
                cleaned_text,
                document.get("title") or document.get("filename"),
                document.get("subject"),
                document.get("degree_level"),
            )

            # 跨文档语义查重：用 pgvector 检索其他文档中的相似段落
            cross_doc_matches: list[dict[str, Any]] = []
            for section in sections:
                embedding = section.get("embedding")
                if not embedding:
                    continue
                try:
                    hits = self.repository.find_similar_sections(
                        embedding_str=embedding,
                        exclude_document_id=document_id,
                        limit=3,
                        distance_threshold=0.45,
                    )
                    for hit in hits:
                        hit["section_index"] = section["section_index"]
                    cross_doc_matches.extend(hits)
                except Exception as exc:  # noqa: BLE001 - 跨文档检索失败不应中断分析
                    logging.getLogger(__name__).warning(
                        "跨文档语义检索失败 (section_index=%s): %s",
                        section.get("section_index"),
                        exc,
                    )

            duplication = score_duplication(
                sections, cross_doc_matches=cross_doc_matches or None
            )

            section_id_by_index = {
                section["section_index"]: section["id"] for section in sections
            }
            ai_scores = [
                {
                    "document_section_id": section_id_by_index[item.index],
                    "score_type": "aigc",
                    "raw_score": item.raw_ai_score,
                    "normalized_score": item.ai_like_score,
                    "risk_level": item.risk_level,
                    "reasons": item.reasons,
                    "signals": [signal.model_dump() for signal in item.signals],
                }
                for item in ai_report.segment_reports
                if item.index in section_id_by_index
            ]
            duplication_scores = [
                {
                    "document_section_id": section_id_by_index[item.section_index],
                    "score_type": "duplication",
                    "raw_score": item.raw_score,
                    "normalized_score": item.normalized_score,
                    "risk_level": item.risk_level,
                    "reasons": item.reasons,
                    "signals": [
                        {
                            "name": "local_duplication_proxy",
                            "score": item.normalized_score,
                            "weight": 1.0,
                            "reasons": item.reasons,
                        }
                    ],
                }
                for item in duplication.section_scores
                if item.section_index in section_id_by_index
            ]
            self.repository.insert_section_scores(
                run["id"], ai_scores + duplication_scores
            )

            # 将 AIGC 分数同步写回 document_blocks（新架构）
            try:
                doc_blocks = self.repository.list_document_blocks(document_id)
                if doc_blocks:
                    block_by_para_idx = {
                        b.get("paragraph_index"): b
                        for b in doc_blocks
                        if b.get("paragraph_index") is not None
                    }
                    for item in ai_report.segment_reports:
                        if item.paragraph_index is not None and item.paragraph_index in block_by_para_idx:
                            block = block_by_para_idx[item.paragraph_index]
                            self.repository.update_block_risk_score(
                                document_id, block["block_id"], item.ai_like_score * 100
                            )
            except Exception:
                import logging
                logging.getLogger(__name__).warning(
                    "Failed to update block risk scores for document %s", document_id, exc_info=True
                )

            similarity_matches = [
                {
                    "document_section_id": section_id_by_index[item.section_index],
                    "matched_source": item.matched_source,
                    "matched_title": item.matched_title,
                    "matched_snippet": item.matched_snippet,
                    "similarity_score": item.similarity_score,
                    "overlap_chars": item.overlap_chars,
                    "match_type": item.match_type,
                    "source_url": item.source_url,
                }
                for item in duplication.matches
                if item.section_index in section_id_by_index
            ]
            self.repository.insert_similarity_matches(run["id"], similarity_matches)

            proxy_prediction = self._build_proxy_prediction(
                document, run, ai_report, duplication
            )
            self.repository.insert_provider_payload(
                run["id"],
                "local",
                "normalized",
                {
                    "ai_like_score": ai_report.ai_like_score,
                    "duplication_score": duplication.overall_score,
                    "template_density": duplication.template_density,
                    "duplicate_sentence_ratio": duplication.duplicate_sentence_ratio,
                    "high_risk_segments": ai_report.high_risk_segments,
                    "segment_count": ai_report.segment_count,
                },
            )
            prediction_row = self.repository.insert_proxy_prediction(**proxy_prediction)
            self.repository.mark_run_completed(run["id"])
            final_run = self.repository.get_run(run["id"])
            if final_run is None:
                raise ValueError("run not found after completion")

            report_json = compose_report(
                document=document,
                run=final_run,
                ai_report=ai_report,
                duplication=duplication,
                proxy_prediction=prediction_row,
            )
            self.repository.save_report_snapshot(
                document_id=document_id, run_id=run["id"], report_json=report_json
            )
            self.repository.mark_document_status(
                document_id, "completed", section_count=len(sections)
            )
            return {"run": final_run, "report": report_json}
        except Exception as exc:
            self.repository.mark_run_failed(run["id"], str(exc))
            self.repository.mark_document_status(
                document_id, "failed", section_count=document.get("section_count", 0)
            )
            raise

    def add_cnki_feedback(
        self,
        *,
        document_id: str,
        predicted_run_id: str | None,
        cnki_dup_percent: float | None,
        cnki_aigc_percent: float | None,
        report_date: date | None,
        notes: str | None,
        details: dict[str, Any] | None = None,
        evidence_file: UploadFile | None = None,
    ) -> dict[str, Any]:
        document = self.repository.get_document(document_id)
        if document is None:
            raise ValueError("document not found")

        evidence_path: str | None = None
        if evidence_file is not None:
            content = evidence_file.file.read()
            if content:
                evidence_path = self._write_binary(
                    self.settings.feedback_storage_dir,
                    evidence_file.filename or "feedback.bin",
                    content,
                )

        # 如果有片段，尝试与原文段落匹配
        if details and details.get("fragments"):
            from app.services.cnki_ocr import match_fragments_to_sections

            sections = self.repository.list_document_sections(document_id)
            matched = match_fragments_to_sections(details["fragments"], sections)
            details["fragments"] = matched

        feedback = self.repository.create_cnki_feedback(
            document_id=document_id,
            predicted_run_id=predicted_run_id,
            cnki_dup_percent=cnki_dup_percent,
            cnki_aigc_percent=cnki_aigc_percent,
            report_date=report_date,
            evidence_path=evidence_path,
            notes=notes,
            details=details,
            verified=False,
        )

        calibration_updated = False
        if predicted_run_id and cnki_aigc_percent is not None:
            snapshot = self.repository.get_report_snapshot(predicted_run_id)
            local_metrics = (
                (snapshot or {}).get("report_json", {}).get("local_metrics", {})
            )
            ai_like_score = local_metrics.get("ai_like_score")
            if ai_like_score is not None:
                self.calibrator.append_sample(
                    CalibrationSample(
                        ai_like_score=float(ai_like_score),
                        cnki_ai_rate=float(cnki_aigc_percent) / 100,
                        subject=document.get("subject"),
                        degree_level=document.get("degree_level"),
                    )
                )
                calibration_updated = True

        return {
            "feedback": feedback,
            "calibration_updated": calibration_updated,
            "calibration_version": self.calibrator.version,
        }

    def build_run_status(self, run_id: str) -> AnalysisRunStatusResponse:
        run = self.repository.get_run(run_id)
        if run is None:
            raise ValueError("run not found")
        stage = _stage_from_status(run["status"])
        return AnalysisRunStatusResponse(
            run_id=str(run["id"]),
            document_id=str(run["document_id"]),
            title=run.get("title"),
            filename=run["filename"],
            subject=run.get("subject"),
            degree_level=run.get("degree_level"),
            status=run["status"],
            stage=stage,
            progress=_progress_from_status(run["status"]),
            created_at=run["created_at"],
            started_at=run.get("started_at"),
            finished_at=run.get("finished_at"),
            error_message=run.get("error_message"),
        )

    def get_report(self, run_id: str) -> dict[str, Any] | None:
        snapshot = self.repository.get_report_snapshot(run_id)
        if snapshot is None:
            return None
        report = dict(snapshot["report_json"])
        provider_payloads = self.repository.list_provider_payloads(run_id)
        provider_results = _serialize_provider_results(provider_payloads)
        feedback_rows = self.repository.list_cnki_feedback_for_document(
            str(report["document_id"]), limit=12
        )
        feedback_timeline = _serialize_feedback_timeline(feedback_rows)
        report["provider_results"] = provider_results
        report["feedback_timeline"] = feedback_timeline
        report["workflow_overview"] = _build_workflow_overview(
            summary=report.get("summary", {}),
            provider_results=provider_results,
            feedback_timeline=feedback_timeline,
        )
        report["calibration_insight"] = _build_calibration_insight(
            summary=report.get("summary", {}),
            feedback_timeline=feedback_timeline,
        )
        # 构建知网报告详情：取最新 feedback 的 details
        report["cnki_report_details"] = _build_cnki_report_details(feedback_rows)
        return report

    def _build_proxy_prediction(
        self,
        document: dict[str, Any],
        run: dict[str, Any],
        ai_report: Any,
        duplication: Any,
    ) -> dict[str, Any]:
        aigc_low = ai_report.predicted_cnki_range.lower
        aigc_high = ai_report.predicted_cnki_range.upper
        aigc_center = round((aigc_low + aigc_high) / 2, 4)

        dup_center = max(
            0.02,
            min(
                0.95,
                0.035
                + duplication.overall_score * 0.74
                + duplication.template_density * 0.08
                + duplication.duplicate_sentence_ratio * 0.09,
            ),
        )
        dispersion = abs(duplication.max_section_score - duplication.overall_score)
        dup_margin = max(0.05, min(0.18, 0.07 + dispersion * 0.32))
        dup_low = max(0.0, round(dup_center - dup_margin, 4))
        dup_high = min(1.0, round(dup_center + dup_margin, 4))
        heuristic_confidence = max(
            0.42,
            min(
                0.9,
                0.46
                + min(0.18, ai_report.segment_count / 20 * 0.18)
                + min(0.12, duplication.evidence_count / 10 * 0.12)
                - min(0.14, dispersion * 0.22),
            ),
        )

        scene_key = _scene_key(document.get("subject"), document.get("degree_level"))
        preview_risks = _build_preview_risk_sections(ai_report, duplication)
        preview_chapters = _build_preview_chapters(preview_risks)
        comfort_score = _estimate_comfort_score(
            dup_high, aigc_high, len(ai_report.high_risk_segments)
        )
        provider_payloads = self.repository.list_provider_payloads(str(run["id"]))
        features = build_feature_dict_from_runtime(
            ai_like_score=ai_report.ai_like_score,
            duplication_score=duplication.overall_score,
            segment_count=ai_report.segment_count,
            high_risk_segment_count=len(ai_report.high_risk_segments),
            comfort_score=comfort_score,
            top_risk_sections=preview_risks,
            chapter_heatmap=preview_chapters,
            provider_payloads=provider_payloads,
        )

        trained_dup = self.proxy_runtime.predict(
            model_type="cnki_dup_proxy", scene_key=scene_key, features=features
        )
        trained_aigc = self.proxy_runtime.predict(
            model_type="cnki_aigc_proxy", scene_key=scene_key, features=features
        )
        final_dup = trained_dup or {
            "model_version": self.settings.unified_proxy_model_version,
            "center": round(dup_center, 4),
            "low": dup_low,
            "high": dup_high,
            "confidence": round(heuristic_confidence, 4),
            "source": "heuristic",
        }
        final_aigc = trained_aigc or {
            "model_version": self.calibrator.version,
            "center": aigc_center,
            "low": aigc_low,
            "high": aigc_high,
            "confidence": round(heuristic_confidence, 4),
            "source": "heuristic",
        }
        confidence = round(min(final_dup["confidence"], final_aigc["confidence"]), 4)
        model_version = (
            f"dup={final_dup['model_version']}|aigc={final_aigc['model_version']}"
            if trained_dup or trained_aigc
            else self.settings.unified_proxy_model_version
        )
        return {
            "document_id": str(document["id"]),
            "run_id": str(run["id"]),
            "model_version": model_version,
            "scene_key": scene_key,
            "predicted_cnki_dup": final_dup["center"],
            "predicted_cnki_dup_low": final_dup["low"],
            "predicted_cnki_dup_high": final_dup["high"],
            "predicted_cnki_aigc": final_aigc["center"],
            "predicted_cnki_aigc_low": final_aigc["low"],
            "predicted_cnki_aigc_high": final_aigc["high"],
            "confidence": confidence,
            "summary": {
                "scene_key": scene_key,
                "risk_level": risk_level(
                    max(ai_report.ai_like_score, duplication.overall_score)
                ),
                "ai_like_score": round(ai_report.ai_like_score, 4),
                "duplication_score": round(duplication.overall_score, 4),
                "high_risk_segments": len(ai_report.high_risk_segments),
                "feature_vector": features,
                "dup_source": final_dup["source"],
                "aigc_source": final_aigc["source"],
            },
        }

    def _write_binary(self, directory: str, filename: str, content: bytes) -> str:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        target = path / f"{uuid4().hex}_{_safe_name(filename)}"
        target.write_bytes(content)
        return str(target.resolve())

    def _write_text(self, directory: str, filename: str, text: str) -> str:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        stem = Path(filename).stem or "paper"
        target = path / f"{uuid4().hex}_{_safe_name(stem)}.txt"
        target.write_text(text, encoding="utf-8")
        return str(target.resolve())


def _safe_name(filename: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff._-]+", "_", filename).strip("_") or "paper"


def _detect_language(text: str) -> str:
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    if chinese_chars >= max(80, len(text) * 0.15):
        return "zh-CN"
    return "mixed"


def _infer_section_type(section_title: str | None) -> str:
    if not section_title:
        return "body"
    for pattern, label in SECTION_TYPE_MAP:
        if pattern.search(section_title):
            return label
    return "other"


def _scene_key(subject: str | None, degree_level: str | None) -> str:
    subject_key = subject or "general"
    degree_key = degree_level or "general"
    return f"{subject_key}:{degree_key}"


def _stage_from_status(status: str) -> str:
    mapping = {
        "queued": "queued",
        "processing": "analyzing",
        "completed": "completed",
        "failed": "failed",
    }
    return mapping.get(status, status)


def _progress_from_status(status: str) -> int:
    mapping = {"queued": 8, "processing": 66, "completed": 100, "failed": 100}
    return mapping.get(status, 0)


def _estimate_comfort_score(
    dup_high: float, aigc_high: float, high_risk_segments: int
) -> int:
    score = 100 - dup_high * 42 - aigc_high * 38 - high_risk_segments * 3.5
    return max(18, min(96, round(score)))


def _build_preview_risk_sections(
    ai_report: Any, duplication: Any
) -> list[dict[str, Any]]:
    duplication_map = {
        item.section_index: item.normalized_score for item in duplication.section_scores
    }
    risks: list[dict[str, Any]] = []
    for item in ai_report.segment_reports:
        risks.append(
            {
                "combined_score": round(
                    item.ai_like_score * 0.58
                    + duplication_map.get(item.index, 0.0) * 0.42,
                    4,
                ),
                "section_title": item.section_title,
            }
        )
    return risks


def _build_preview_chapters(risks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[float]] = {}
    for item in risks:
        title = item.get("section_title") or "正文主体"
        grouped.setdefault(title, []).append(float(item["combined_score"]))
    return [
        {"combined_score": sum(scores) / len(scores)} for scores in grouped.values()
    ]


def _serialize_provider_results(
    payload_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    normalized_rows = [
        row for row in payload_rows if row.get("payload_type") == "normalized"
    ]
    normalized_rows.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    results: list[dict[str, Any]] = []
    for row in normalized_rows:
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        raw_payload = (
            payload.get("raw_payload")
            if isinstance(payload.get("raw_payload"), dict)
            else {}
        )
        source_type = (
            "manual_import" if raw_payload.get("imported_from_ui") else "auto_fetch"
        )
        provider = str(row.get("provider") or payload.get("provider") or "manual")
        results.append(
            {
                "payload_id": str(row["id"]),
                "provider": provider,
                "provider_label": _provider_label(provider),
                "source_type": source_type,
                "duplication_percent": payload.get("duplication_percent"),
                "aigc_percent": payload.get("aigc_percent"),
                "confidence": payload.get("confidence"),
                "version": payload.get("version"),
                "notes": payload.get("notes"),
                "created_at": row.get("created_at"),
            }
        )
    return results[:12]


def _serialize_feedback_timeline(
    feedback_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    for row in feedback_rows:
        item: dict[str, Any] = {
            "feedback_id": str(row["id"]),
            "predicted_run_id": str(row["predicted_run_id"])
            if row.get("predicted_run_id")
            else None,
            "cnki_dup_percent": row.get("cnki_dup_percent"),
            "cnki_aigc_percent": row.get("cnki_aigc_percent"),
            "report_date": row.get("report_date"),
            "notes": row.get("notes"),
            "verified": bool(row.get("verified", False)),
            "created_at": row.get("created_at"),
        }
        details = row.get("details")
        if details and isinstance(details, dict) and details != {}:
            item["details"] = details
        timeline.append(item)
    return timeline[:12]


def _build_cnki_report_details(
    feedback_rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """从最新 feedback 的 details 构建知网报告详情。"""
    if not feedback_rows:
        return None
    latest = feedback_rows[0]
    details = latest.get("details")
    if not details or not isinstance(details, dict) or details == {}:
        return None
    result: dict[str, Any] = {}
    if "remove_reference_dup_percent" in details:
        result["remove_reference_dup_percent"] = details["remove_reference_dup_percent"]
    if "single_max_dup_percent" in details:
        result["single_max_dup_percent"] = details["single_max_dup_percent"]
    if "suspected_plagiarism" in details:
        result["suspected_plagiarism"] = details["suspected_plagiarism"]
    if "fragments" in details:
        result["fragments"] = details["fragments"]
    return result if result else None


def _build_workflow_overview(
    *,
    summary: dict[str, Any],
    provider_results: list[dict[str, Any]],
    feedback_timeline: list[dict[str, Any]],
) -> dict[str, Any]:
    provider_count = len(provider_results)
    feedback_count = len(feedback_timeline)
    confidence = float(summary.get("confidence", 0.0) or 0.0)
    closure_score = 32
    closure_score += min(28, provider_count * 14)
    closure_score += min(28, feedback_count * 18)
    closure_score += round(min(12, confidence * 12))
    if summary.get("overall_risk") != "high":
        closure_score += 8
    closure_score = max(18, min(100, closure_score))

    if summary.get("overall_risk") == "high":
        next_step = "优先处理高风险段落，修改后可再次上传知网报告验证效果。"
    elif provider_count == 0:
        next_step = "建议补充外部检测结果，让分析维度更全面。"
    elif feedback_count == 0:
        next_step = "建议上传知网检测报告，系统会结合官方数据优化改写策略。"
    else:
        next_step = "分析已结合知网官方数据，继续积累报告会让改写建议更精准。"

    if closure_score >= 85:
        closure_label = "分析完整"
    elif closure_score >= 60:
        closure_label = "分析较完整"
    else:
        closure_label = "建议补充知网报告"

    return {
        "closure_score": closure_score,
        "closure_label": closure_label,
        "provider_result_count": provider_count,
        "feedback_count": feedback_count,
        "latest_feedback_at": feedback_timeline[0]["created_at"]
        if feedback_timeline
        else None,
        "next_step": next_step,
    }


def _build_calibration_insight(
    summary: dict[str, Any], feedback_timeline: list[dict[str, Any]]
) -> dict[str, Any] | None:
    if not feedback_timeline:
        return {
            "latest_cnki_dup_percent": None,
            "latest_cnki_aigc_percent": None,
            "predicted_dup_delta": None,
            "predicted_aigc_delta": None,
            "message": "上传知网检测报告后，系统会结合官方实测数据优化改写建议策略。",
        }

    latest = feedback_timeline[0]
    predicted_dup = summary.get("predicted_cnki_dup", {}).get("center_percent")
    predicted_aigc = summary.get("predicted_cnki_aigc", {}).get("center_percent")
    latest_dup = latest.get("cnki_dup_percent")
    latest_aigc = latest.get("cnki_aigc_percent")
    dup_delta = (
        round(float(predicted_dup) - float(latest_dup), 2)
        if predicted_dup is not None and latest_dup is not None
        else None
    )
    aigc_delta = (
        round(float(predicted_aigc) - float(latest_aigc), 2)
        if predicted_aigc is not None and latest_aigc is not None
        else None
    )

    # 构建友好的提示，不强调偏差，而是强调已结合知网数据优化
    if latest_dup is not None and latest_aigc is not None:
        message = f"已接入知网官方数据：查重 {latest_dup:.1f}%，AIGC {latest_aigc:.1f}%。当前改写建议已按知网实测标准优化。"
    elif latest_dup is not None:
        message = f"已接入知网官方数据：查重 {latest_dup:.1f}%。当前改写建议已结合查重数据优化。"
    elif latest_aigc is not None:
        message = f"已接入知网官方数据：AIGC {latest_aigc:.1f}%。当前改写建议已结合 AIGC 数据优化。"
    else:
        message = "已收到知网报告，当前改写建议已结合官方数据优化。"

    return {
        "latest_cnki_dup_percent": latest_dup,
        "latest_cnki_aigc_percent": latest_aigc,
        "predicted_dup_delta": dup_delta,
        "predicted_aigc_delta": aigc_delta,
        "message": message,
    }


def _provider_label(provider: str) -> str:
    mapping = {
        "wanfang": "万方",
        "vip": "维普",
        "turnitin": "Turnitin",
        "manual": "手工结果",
        "local": "本地引擎",
    }
    return mapping.get(provider, provider)
