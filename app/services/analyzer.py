import re
from datetime import UTC, datetime
from statistics import pstdev
from typing import Any
from uuid import uuid4

from app.config import Settings
from app.detectors import Detector, build_production_detectors
from app.schemas import AnalyzeResponse, DetectorSignal, SegmentReport, SubScores
from app.services.calibration import CnkiCalibrator
from app.services.text_processing import TextSegment, preview_text, segment_document


# 探测器 → 子分数类别映射
_DETECTOR_CATEGORY_MAP: dict[str, str] = {
    "LocalTransformerDetector": "ai_likelihood",
    "PerplexityDetector": "ai_likelihood",
    "TemplatePhraseDetector": "template_score",
    "ConnectorDensityDetector": "template_score",
    "ReportLearnedStyleDetector": "template_score",
    "TokenRankStyleDetector": "template_score",
    "VagueAbstractionDetector": "semantic_empty_score",
    "LexicalDiversityDetector": "repetition_score",
    "CrossSegmentRepetitionDetector": "repetition_score",
    "SentenceUniformityDetector": "repetition_score",
}

_CATEGORY_WEIGHTS: dict[str, float] = {
    "ai_likelihood": 0.35,
    "template_score": 0.25,
    "semantic_empty_score": 0.20,
    "repetition_score": 0.15,
    "citation_risk": 0.05,
}

_CITATION_PATTERNS = [
    re.compile(r"\[\d+(?:\s*[-–—,]\s*\d+)*\]"),  # [1], [1-3], [1,2,3]
    re.compile(r"[（(][\u4e00-\u9fa5]{2,20}\s*et\s*al\.?\s*,?\s*\d{4}[）)]"),  # (张三 et al, 2020)
    re.compile(r"[（(][\u4e00-\u9fa5]{2,20}[,，]\s*\d{4}[）)]"),  # (张三, 2020)
    re.compile(r"[（(]\d{4}[）)]"),  # (2020)
]


DISCLAIMER = (
    "本报告为 AIGC 疑似风险与知网结果区间预测，不等同于知网、维普、万方或 Turnitin 官方结果；"
    "低分不能证明未使用 AI，高分也不能单独作为学术不端结论，建议结合人工复核和写作过程材料判断。"
)

RETAINED_CONTENT_POLICY = (
    "检测完成后不持久化保存论文原文，仅保留匿名特征、分数、模型版本与报告摘要。"
)

_SKIP_SECTION_PATTERNS = [
    re.compile(r"参考文献|references", re.IGNORECASE),
    re.compile(r"目录|contents|table\s+of\s+contents", re.IGNORECASE),
    re.compile(r"致谢|acknowledg", re.IGNORECASE),
]


def _should_skip_section(section_title: str | None) -> bool:
    if not section_title:
        return False
    return any(p.search(section_title) for p in _SKIP_SECTION_PATTERNS)


def _citation_risk(text: str) -> float:
    """计算引用风险：学术段落中缺少引用标记的风险分数（0-100）。"""
    # 粗略统计句子数
    sentences = [s for s in re.split(r"[。！？.!?]", text) if s.strip()]
    if len(sentences) <= 1:
        return 0.0  # 太短的片段不评估引用

    citation_count = 0
    for pattern in _CITATION_PATTERNS:
        citation_count += len(pattern.findall(text))

    # 引用密度：每句平均引用数
    density = citation_count / len(sentences)
    # 密度 < 0.1 → 高风险（学术段落应该有引用）
    # 密度 >= 0.5 → 低风险
    risk = max(0.0, min(100.0, (0.3 - density) / 0.3 * 100))
    return round(risk, 2)


def _compute_sub_scores(text: str, active_results: list[Any]) -> SubScores:
    """根据探测器结果计算加权子分数。"""
    category_scores: dict[str, list[tuple[float, float]]] = {
        "ai_likelihood": [],
        "template_score": [],
        "semantic_empty_score": [],
        "repetition_score": [],
    }

    for result in active_results:
        category = _DETECTOR_CATEGORY_MAP.get(result.name)
        if category:
            category_scores[category].append((result.score, result.weight))

    def _weighted_avg(items: list[tuple[float, float]]) -> float:
        if not items:
            return 0.0
        total_w = sum(w for _, w in items) or 1.0
        return sum(s * w for s, w in items) / total_w

    ai_likelihood = _weighted_avg(category_scores["ai_likelihood"]) * 100
    template_score = _weighted_avg(category_scores["template_score"]) * 100
    semantic_empty_score = _weighted_avg(category_scores["semantic_empty_score"]) * 100
    repetition_score = _weighted_avg(category_scores["repetition_score"]) * 100
    citation_risk_val = _citation_risk(text)

    overall = (
        ai_likelihood * _CATEGORY_WEIGHTS["ai_likelihood"]
        + template_score * _CATEGORY_WEIGHTS["template_score"]
        + semantic_empty_score * _CATEGORY_WEIGHTS["semantic_empty_score"]
        + repetition_score * _CATEGORY_WEIGHTS["repetition_score"]
        + citation_risk_val * _CATEGORY_WEIGHTS["citation_risk"]
    )

    return SubScores(
        ai_likelihood=round(ai_likelihood, 2),
        template_score=round(template_score, 2),
        semantic_empty_score=round(semantic_empty_score, 2),
        repetition_score=round(repetition_score, 2),
        citation_risk=round(citation_risk_val, 2),
        overall_risk=round(overall, 2),
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
        self.model_version = "ensemble-cn-academic-0.2.1"

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

        scored_segments: list[TextSegment] = []
        skipped_segments: list[TextSegment] = []
        for seg in segments:
            if _should_skip_section(seg.section_title):
                skipped_segments.append(seg)
            else:
                scored_segments.append(seg)

        scored_reports = [
            self._score_segment(segment, scored_segments) for segment in scored_segments
        ]
        skipped_reports = [
            SegmentReport(
                index=segment.index,
                section_title=segment.section_title,
                paragraph_index=segment.paragraph_index,
                text_preview=preview_text(segment.text),
                char_count=len(segment.text),
                raw_ai_score=0.0,
                ai_probability=0.0,
                ai_like_score=0.0,
                risk_level="low",
                reasons=["该片段属于参考文献/目录/致谢部分，不参与 AIGC 评分"],
                signals=[],
            )
            for segment in skipped_segments
        ]

        segment_reports = scored_reports + skipped_reports
        segment_reports.sort(key=lambda r: r.index)

        total_chars = sum(report.char_count for report in segment_reports)

        scored_chars = sum(report.char_count for report in scored_reports)
        if scored_chars == 0:
            ai_like_score = 0.0
        else:
            weighted = sum(
                report.ai_like_score * report.char_count for report in scored_reports
            )
            ai_like_score = weighted / scored_chars

        dispersion = self._segment_dispersion(scored_reports)
        predicted_range = self.calibrator.predict_range(
            ai_like_score, dispersion, subject
        )
        confidence = self.calibrator.confidence(len(scored_reports), dispersion)
        high_risk_segments = [
            report.index for report in scored_reports if report.ai_like_score >= 0.70
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

        sub_scores = _compute_sub_scores(segment.text, active_results)

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
            sub_scores=sub_scores,
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
