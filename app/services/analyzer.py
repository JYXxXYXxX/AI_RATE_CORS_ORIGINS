from datetime import UTC, datetime
from statistics import pstdev
from uuid import uuid4

from app.config import Settings
from app.detectors import Detector, build_production_detectors
from app.schemas import AnalyzeResponse, DetectorSignal, SegmentReport
from app.services.calibration import CnkiCalibrator
from app.services.text_processing import TextSegment, preview_text, segment_document


DISCLAIMER = (
    "本报告为 AIGC 疑似风险与知网结果区间预测，不等同于知网、维普、万方或 Turnitin 官方结果；"
    "低分不能证明未使用 AI，高分也不能单独作为学术不端结论，建议结合人工复核和写作过程材料判断。"
)

RETAINED_CONTENT_POLICY = (
    "检测完成后不持久化保存论文原文，仅保留匿名特征、分数、模型版本与报告摘要。"
)


class PaperAnalyzer:
    def __init__(
        self,
        settings: Settings,
        detectors: list[Detector] | None = None,
        calibrator: CnkiCalibrator | None = None,
    ) -> None:
        self.settings = settings
        self.detectors = detectors or build_production_detectors()
        self.calibrator = calibrator or CnkiCalibrator(settings)
        self.model_version = "ensemble-cn-academic-0.2.0"

    def analyze(
        self,
        text: str,
        title: str | None = None,
        subject: str | None = None,
        degree_level: str | None = None,
    ) -> AnalyzeResponse:
        if len(text) > self.settings.max_text_chars:
            text = text[: self.settings.max_text_chars]

        segments = segment_document(text, self.settings)
        segment_reports = [
            self._score_segment(segment, segments) for segment in segments
        ]
        total_chars = sum(report.char_count for report in segment_reports)

        if total_chars == 0:
            ai_like_score = 0.0
        else:
            weighted = sum(
                report.ai_like_score * report.char_count for report in segment_reports
            )
            ai_like_score = weighted / total_chars

        dispersion = self._segment_dispersion(segment_reports)
        predicted_range = self.calibrator.predict_range(
            ai_like_score, dispersion, subject
        )
        confidence = self.calibrator.confidence(len(segment_reports), dispersion)
        high_risk_segments = [
            report.index for report in segment_reports if report.ai_like_score >= 0.70
        ]

        return AnalyzeResponse(
            report_id=str(uuid4()),
            title=title,
            subject=subject,
            degree_level=degree_level,
            ai_like_score=round(ai_like_score, 4),
            ai_like_percent=round(ai_like_score * 100, 2),
            predicted_cnki_range=predicted_range,
            confidence=confidence,
            risk_level=risk_level(ai_like_score),
            segment_count=len(segment_reports),
            total_chars=total_chars,
            high_risk_segments=high_risk_segments,
            segment_reports=segment_reports,
            model_version=self.model_version,
            calibration_version=self.calibrator.version,
            disclaimer=DISCLAIMER,
            generated_at=datetime.now(UTC),
            retained_content_policy=RETAINED_CONTENT_POLICY,
        )

    def _score_segment(
        self, segment: TextSegment, all_segments: list[TextSegment]
    ) -> SegmentReport:
        raw_texts = [item.text for item in all_segments]
        results = [
            detector.score(segment.text, raw_texts) for detector in self.detectors
        ]
        active_results = [result for result in results if result.weight > 0]
        total_weight = sum(result.weight for result in active_results) or 1.0
        raw_score = (
            sum(result.score * result.weight for result in active_results)
            / total_weight
        )
        calibrated = calibrate_score(raw_score)

        reasons: list[str] = []
        for result in active_results:
            reasons.extend(result.reasons)
        reasons = _dedupe(reasons)

        return SegmentReport(
            index=segment.index,
            section_title=segment.section_title,
            paragraph_index=segment.paragraph_index,
            text_preview=preview_text(segment.text),
            char_count=len(segment.text),
            raw_ai_score=round(raw_score, 4),
            ai_probability=round(calibrated, 4),
            ai_like_score=round(calibrated, 4),
            risk_level=risk_level(calibrated),
            reasons=reasons[:8],
            signals=[
                DetectorSignal(
                    name=result.name,
                    score=round(result.score, 4),
                    weight=result.weight,
                    reasons=result.reasons,
                )
                for result in active_results
            ],
        )

    @staticmethod
    def _segment_dispersion(reports: list[SegmentReport]) -> float:
        if len(reports) < 2:
            return 0.24
        return min(0.50, pstdev(report.ai_like_score for report in reports))


def calibrate_score(raw_score: float) -> float:
    import math

    centered = (raw_score - 0.47) * 4.0
    probability = 1 / (1 + math.exp(-centered))
    return max(0.04, min(0.94, probability))


def risk_level(score: float) -> str:
    if score >= 0.70:
        return "high"
    if score >= 0.42:
        return "medium"
    return "low"


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped
