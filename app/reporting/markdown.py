from __future__ import annotations

import html
from datetime import date, datetime
from typing import Any


def _h(text: str | None) -> str:
    """对可能包含 HTML 的文本进行转义，防止 Markdown 输出中的 XSS。"""
    if text is None:
        return ""
    return html.escape(str(text))


def render_report_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    local_metrics = report["local_metrics"]
    mentor_brief = report["mentor_brief"]
    workflow_overview = report.get("workflow_overview") or {}
    calibration_insight = report.get("calibration_insight") or {}

    lines: list[str] = [
        f"# {_h(report['title'])}",
        "",
        "## 目录",
        "",
        "- [报告概览](#报告概览)",
        "- [本地检测指标](#本地检测指标)",
        "- [章节热力图](#章节热力图)",
        "- [高风险段落](#高风险段落)",
        "- [相似匹配证据](#相似匹配证据)",
        "- [修改优先计划](#修改优先计划)",
        "- [导师沟通摘要](#导师沟通摘要)",
        "- [送检前检查清单](#送检前检查清单)",
        "",
        "---",
        "",
        "## 报告概览",
        "",
        f"- 生成时间：{_format_datetime(report.get('generated_at'))}",
        f"- 学科：{_h(report.get('subject')) or '未填写'}",
        f"- 层级：{_h(report.get('degree_level')) or '未填写'}",
        f"- 风险指数：{summary['risk_score']}/100",
        f"- 综合风险：{_risk_text(summary['overall_risk'])}",
        f"- 预测知网查重：{_band_text(summary['predicted_cnki_dup'])}",
        f"- 预测知网 AIGC：{_band_text(summary['predicted_cnki_aigc'])}",
        f"- 模型置信度：{round(float(summary['confidence']) * 100)}%",
        "",
        f"> {_h(summary['one_line_judgement'])}",
        "",
        "## 本地检测指标",
        "",
        f"- 本地 AIGC 分：{_percent(local_metrics['ai_like_score'])}",
        f"- 本地重复风险分：{_percent(local_metrics['duplication_score'])}",
        f"- 分析片段数：{local_metrics['segment_count']}",
        f"- 高风险片段数：{local_metrics['high_risk_segment_count']}",
        "",
        "## 本次最该先改的 3 个地方",
        "",
    ]
    for item in summary.get("first_fix_targets", []):
        lines.append(f"- {_h(item)}")

    if workflow_overview:
        lines.extend(
            [
                "",
                "## 闭环进展",
                "",
                f"- 闭环完成度：{workflow_overview.get('closure_score', 0)}/100（{workflow_overview.get('closure_label', '未评估')}）",
                f"- 外部结果数：{workflow_overview.get('provider_result_count', 0)}",
                f"- 真实回填数：{workflow_overview.get('feedback_count', 0)}",
                f"- 最近回填时间：{_format_datetime(workflow_overview.get('latest_feedback_at'))}",
                f"- 下一步建议：{_h(workflow_overview.get('next_step')) or '-'}",
            ]
        )

    if calibration_insight:
        lines.extend(
            [
                "",
                "## 拟合偏差观察",
                "",
                f"- 最新真实知网查重：{_optional_percent(calibration_insight.get('latest_cnki_dup_percent'))}",
                f"- 最新真实知网 AIGC：{_optional_percent(calibration_insight.get('latest_cnki_aigc_percent'))}",
                f"- 查重偏差：{_delta_text(calibration_insight.get('predicted_dup_delta'))}",
                f"- AIGC 偏差：{_delta_text(calibration_insight.get('predicted_aigc_delta'))}",
                "",
                _h(calibration_insight.get("message")) or "-",
            ]
        )

    lines.extend(["", "## 章节风险热力图", ""])
    for chapter in report.get("chapter_heatmap", []):
        lines.extend(
            [
                f"### {_h(chapter['chapter_title'])}",
                "",
                f"- 风险等级：{_risk_text(chapter['risk_level'])}",
                f"- AIGC 均值：{_percent(chapter['avg_aigc_score'])}",
                f"- 查重均值：{_percent(chapter['avg_duplication_score'])}",
                f"- 综合风险：{_percent(chapter['combined_score'])}",
                f"- 建议：{_h(chapter['advice'])}",
                "",
            ]
        )

    lines.extend(["## Top 风险段落", ""])
    for index, section in enumerate(report.get("top_risk_sections", []), start=1):
        lines.extend(
            [
                f"### {index}. {_h(section['title'])}",
                "",
                f"- 风险等级：{_risk_text(section['risk_level'])}",
                f"- AIGC：{_percent(section['aigc_score'])}",
                f"- 查重：{_percent(section['duplication_score'])}",
                f"- 综合：{_percent(section['combined_score'])}",
                f"- 原因标签：{_join(section.get('reasons') or ['未提取原因'])}",
                f"- 文本预览：{_h(section['text_preview'])}",
                "",
            ]
        )

    lines.extend(["## 相似证据", ""])
    for index, match in enumerate(report.get("top_similarity_matches", []), start=1):
        lines.extend(
            [
                f"### {index}. {_h(match['section_title'])}",
                "",
                f"- 匹配来源：{_h(match['matched_source'])}",
                f"- 匹配标题：{_h(match['matched_title'])}",
                f"- 匹配类型：{_h(match['match_type'])}",
                f"- 相似度：{match['similarity_percent']:.1f}%",
                f"- 重合字符：{_h(str(match['overlap_chars']))}",
                f"- 证据摘要：{_h(match['matched_snippet'])}",
                "",
            ]
        )

    if report.get("provider_results"):
        lines.extend(["## 外部结果时间线", ""])
        for item in report.get("provider_results", []):
            lines.extend(
                [
                    f"### {_h(item['provider_label'])} / {_h(item['source_type'])}",
                    "",
                    f"- 时间：{_format_datetime(item.get('created_at'))}",
                    f"- 查重：{_optional_percent(item.get('duplication_percent'))}",
                    f"- AIGC：{_optional_percent(item.get('aigc_percent'))}",
                    f"- 置信度：{_optional_confidence(item.get('confidence'))}",
                    f"- 版本：{_h(item.get('version')) or '-'}",
                    f"- 备注：{_h(item.get('notes')) or '-'}",
                    "",
                ]
            )

    if report.get("feedback_timeline"):
        lines.extend(["## 真实知网回填历史", ""])
        for item in report.get("feedback_timeline", []):
            lines.extend(
                [
                    f"### 回填于 {_format_datetime(item.get('created_at'))}",
                    "",
                    f"- 知网查重：{_optional_percent(item.get('cnki_dup_percent'))}",
                    f"- 知网 AIGC：{_optional_percent(item.get('cnki_aigc_percent'))}",
                    f"- 报告日期：{_format_date(item.get('report_date'))}",
                    f"- 备注：{item.get('notes') or '-'}",
                    f"- 是否人工核验：{'是' if item.get('verified') else '否'}",
                    "",
                ]
            )

    lines.extend(["## 三步提交计划", ""])
    for plan in report.get("revision_plan", []):
        lines.extend(
            [
                f"### Step {plan['priority']}：{_h(plan['title'])}",
                "",
                f"- 为什么先改：{_h(plan['why'])}",
                f"- 怎么改：{_h(plan['how_to_fix'])}",
                f"- 预期收益：{_h(plan['expected_gain'])}",
                "",
            ]
        )

    lines.extend(
        [
            "## 导师沟通摘要",
            "",
            f"### {mentor_brief['headline']}",
            "",
            mentor_brief["summary"],
            "",
            "建议沟通话术：",
            "",
            f"> {mentor_brief['suggested_message']}",
            "",
            "## 送检前检查清单",
            "",
        ]
    )
    for item in report.get("submission_checklist", []):
        marker = "x" if item.get("done") else " "
        lines.append(f"- [{marker}] {_h(item['label'])}")

    lines.extend(
        [
            "",
            "## 风险说明",
            "",
            _h(report.get("disclaimer")) or "",
            "",
            _h(report.get("retained_content_policy")) or "",
            "",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _risk_text(level: str) -> str:
    mapping = {"high": "高风险", "medium": "中风险", "low": "低风险"}
    return mapping.get(level, level)


def _percent(value: float) -> str:
    return f"{float(value) * 100:.1f}%"


def _optional_percent(value: Any) -> str:
    if value is None:
        return "-"
    if float(value) <= 1:
        return f"{float(value) * 100:.1f}%"
    return f"{float(value):.1f}%"


def _optional_confidence(value: Any) -> str:
    if value is None:
        return "-"
    return f"{float(value) * 100:.0f}%"


def _delta_text(value: Any) -> str:
    if value is None:
        return "-"
    return f"{float(value):+.2f} 个百分点"


def _band_text(band: dict[str, Any]) -> str:
    return f"{band['low_percent']:.1f}% - {band['high_percent']:.1f}%（中心值 {band['center_percent']:.1f}%）"


def _format_datetime(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value) if value is not None else "-"


def _format_date(value: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return str(value) if value is not None else "-"


def _join(values: list[str]) -> str:
    return "、".join(values)
