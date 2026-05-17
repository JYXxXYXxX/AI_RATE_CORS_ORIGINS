from types import SimpleNamespace

from app.detectors.heuristics import ReportLearnedStyleDetector
from app.reporting.composer import compose_report
from app.services.rewrite_strategy import apply_learned_rewrite_style


def test_learned_style_detector_flags_report_like_ai_register() -> None:
    detector = ReportLearnedStyleDetector()
    high_style = (
        "数字金融生态的持续发展让个人交易渠道趋于多元，系统通过智能体机制"
        "为财务管理体系提供坚实基础，并进一步支撑后续落地与优化完善。"
    )
    concrete_style = (
        "本系统使用SpringBoot 3.1.5、Vue 3和MySQL 8.0实现账号登录、"
        "收支记录和预算提醒，接口测试平均响应时间为180ms。"
    )

    high = detector.score(high_style, [high_style])
    concrete = detector.score(concrete_style, [concrete_style])

    assert high.score > concrete.score
    assert high.reasons


def test_learned_rewrite_style_humanizes_formal_terms() -> None:
    text = "该机制能够支撑系统持续迭代，并提供了新的技术解决路径。"

    assert apply_learned_rewrite_style(text) == "该做法能够支持系统不断更新，并提供了新的解决思路。"


def test_report_omits_non_actionable_normal_sections() -> None:
    ai_report = SimpleNamespace(
        segment_reports=[
            SimpleNamespace(
                index=0,
                section_title="正文",
                paragraph_index=0,
                text_preview="正常段落",
                char_count=120,
                ai_like_score=0.08,
                reasons=[],
                sub_scores=None,
            )
        ],
        ai_like_score=0.08,
        segment_count=1,
        high_risk_segments=[],
        disclaimer="",
        retained_content_policy="",
    )
    duplication = SimpleNamespace(
        overall_score=0.03,
        template_density=0.0,
        duplicate_sentence_ratio=0.0,
        max_section_score=0.03,
        section_scores=[
            SimpleNamespace(section_index=0, normalized_score=0.03, reasons=[])
        ],
        matches=[],
    )
    proxy_prediction = {
        "predicted_cnki_dup": 0.03,
        "predicted_cnki_dup_low": 0.0,
        "predicted_cnki_dup_high": 0.08,
        "predicted_cnki_aigc": 0.08,
        "predicted_cnki_aigc_low": 0.02,
        "predicted_cnki_aigc_high": 0.14,
        "confidence": 0.7,
    }

    report = compose_report(
        document={"id": "doc-1", "title": "demo"},
        run={"id": "run-1", "created_at": None, "finished_at": None},
        ai_report=ai_report,
        duplication=duplication,
        proxy_prediction=proxy_prediction,
    )

    assert report["top_risk_sections"] == []
    assert report["priority_sections"] == []
