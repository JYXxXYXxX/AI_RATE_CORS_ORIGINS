from __future__ import annotations

from collections import defaultdict
from typing import Any


def compose_report(
    *,
    document: dict[str, Any],
    run: dict[str, Any],
    ai_report: Any,
    duplication: Any,
    proxy_prediction: dict[str, Any],
) -> dict[str, Any]:
    section_reports = _merge_section_reports(
        ai_report.segment_reports, duplication.section_scores
    )
    chapter_heatmap = _build_chapter_heatmap(section_reports)
    top_risk_sections = sorted(
        section_reports, key=lambda item: item["combined_score"], reverse=True
    )[:8]
    top_similarity_matches = _serialize_matches(duplication.matches, section_reports)[
        :10
    ]
    revision_plan = _build_revision_plan(top_risk_sections, top_similarity_matches)
    mentor_brief = _build_mentor_brief(document, proxy_prediction, top_risk_sections)
    submission_checklist = _build_submission_checklist(
        top_risk_sections, top_similarity_matches
    )
    first_fix_targets = [item["title"] for item in revision_plan[:3]]
    comfort_score = _comfort_score(proxy_prediction, top_risk_sections)
    overall_risk = _overall_risk(proxy_prediction, top_risk_sections)

    summary = {
        "comfort_score": comfort_score,
        "overall_risk": overall_risk,
        "one_line_judgement": _one_line_judgement(overall_risk, comfort_score),
        "predicted_cnki_dup": _score_band(
            proxy_prediction["predicted_cnki_dup"],
            proxy_prediction["predicted_cnki_dup_low"],
            proxy_prediction["predicted_cnki_dup_high"],
            "查重预估",
        ),
        "predicted_cnki_aigc": _score_band(
            proxy_prediction["predicted_cnki_aigc"],
            proxy_prediction["predicted_cnki_aigc_low"],
            proxy_prediction["predicted_cnki_aigc_high"],
            "AIGC 预估",
        ),
        "confidence": round(float(proxy_prediction["confidence"]), 4),
        "first_fix_targets": first_fix_targets,
    }

    return {
        "run_id": str(run["id"]),
        "document_id": str(document["id"]),
        "title": document.get("title") or document.get("filename"),
        "subject": document.get("subject"),
        "degree_level": document.get("degree_level"),
        "generated_at": run.get("finished_at") or run.get("created_at"),
        "summary": summary,
        "local_metrics": {
            "ai_like_score": round(ai_report.ai_like_score, 4),
            "duplication_score": round(duplication.overall_score, 4),
            "segment_count": ai_report.segment_count,
            "high_risk_segment_count": len(ai_report.high_risk_segments),
        },
        "chapter_heatmap": chapter_heatmap,
        "top_risk_sections": [_strip_combined(item) for item in top_risk_sections],
        "top_similarity_matches": top_similarity_matches,
        "revision_plan": revision_plan,
        "mentor_brief": mentor_brief,
        "submission_checklist": submission_checklist,
        "disclaimer": ai_report.disclaimer,
        "retained_content_policy": ai_report.retained_content_policy,
    }


def _merge_section_reports(
    ai_segments: list[Any], duplication_sections: list[Any]
) -> list[dict[str, Any]]:
    duplication_by_index = {item.section_index: item for item in duplication_sections}
    merged: list[dict[str, Any]] = []
    for ai_segment in ai_segments:
        duplication = duplication_by_index.get(ai_segment.index)
        duplication_score = duplication.normalized_score if duplication else 0.0
        combined_score = round(
            ai_segment.ai_like_score * 0.58 + duplication_score * 0.42, 4
        )
        merged.append(
            {
                "section_index": ai_segment.index,
                "title": ai_segment.section_title
                or f"正文段落 {ai_segment.paragraph_index or ai_segment.index + 1}",
                "section_title": ai_segment.section_title,
                "paragraph_index": ai_segment.paragraph_index,
                "text_preview": ai_segment.text_preview,
                "char_count": ai_segment.char_count,
                "aigc_score": round(ai_segment.ai_like_score, 4),
                "duplication_score": round(duplication_score, 4),
                "combined_score": combined_score,
                "risk_level": _level_from_score(combined_score),
                "reasons": (
                    ai_segment.reasons[:2]
                    + (duplication.reasons[:2] if duplication else [])
                )[:4],
            }
        )
    return merged


def _build_chapter_heatmap(
    section_reports: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in section_reports:
        grouped[item["section_title"] or "正文主体"].append(item)

    heatmap: list[dict[str, Any]] = []
    for title, items in grouped.items():
        avg_aigc = sum(item["aigc_score"] for item in items) / len(items)
        avg_dup = sum(item["duplication_score"] for item in items) / len(items)
        combined = sum(item["combined_score"] for item in items) / len(items)
        heatmap.append(
            {
                "chapter_title": title,
                "section_count": len(items),
                "avg_aigc_score": round(avg_aigc, 4),
                "avg_duplication_score": round(avg_dup, 4),
                "combined_score": round(combined, 4),
                "risk_level": _level_from_score(combined),
                "advice": _chapter_advice(title, combined),
            }
        )

    heatmap.sort(key=lambda item: item["combined_score"], reverse=True)
    return heatmap


def _serialize_matches(
    matches: list[Any], section_reports: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    titles = {item["section_index"]: item["title"] for item in section_reports}
    return [
        {
            "section_index": item.section_index,
            "section_title": titles.get(
                item.section_index, f"正文段落 {item.section_index + 1}"
            ),
            "matched_source": item.matched_source,
            "matched_title": item.matched_title,
            "matched_snippet": item.matched_snippet,
            "similarity_score": item.similarity_score,
            "similarity_percent": round(item.similarity_score * 100, 2),
            "overlap_chars": item.overlap_chars,
            "match_type": item.match_type,
            "source_url": item.source_url,
        }
        for item in matches
    ]


def _build_revision_plan(
    top_risk_sections: list[dict[str, Any]],
    top_similarity_matches: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    plans: list[dict[str, Any]] = []
    for index, section in enumerate(top_risk_sections[:3], start=1):
        why, how = _targeted_advice(section)
        plans.append(
            {
                "priority": index,
                "title": f"优先处理「{section['title']}」",
                "why": why,
                "how_to_fix": how,
                "expected_gain": _expected_gain(section),
            }
        )

    if top_similarity_matches:
        top_match = top_similarity_matches[0]
        plans.append(
            {
                "priority": len(plans) + 1,
                "title": f"处理与「{top_match.get('matched_title', '外部文档')}」高度相似的段落",
                "why": (
                    f"「{top_match.get('section_title', '该段')}」与已有文献相似度达 "
                    f"{top_match.get('similarity_percent', 0):.0f}%，"
                    "正式送检系统大概率也会标记。"
                ),
                "how_to_fix": "保留核心论点，重写句子骨架，把概括性空话替换为你的数据细节，并补充引用出处。",
                "expected_gain": "直接消除最明确的重合证据，避免改了很多但没动到关键段。",
            }
        )

    plans.append(
        {
            "priority": len(plans) + 1,
            "title": "正式送检前做一次定向复检",
            "why": "很多论文不是改得不够，而是改错了顺序，先改关键段会更省时间。",
            "how_to_fix": "只复检改动最大的章节，对比前后高风险段数量和区间变化，再决定是否继续深改。",
            "expected_gain": "能把时间花在最影响最终结果的地方。",
        }
    )
    return plans[:5]


def _targeted_advice(section: dict[str, Any]) -> tuple[str, str]:
    """根据段落的具体信号生成针对性修改建议。"""
    aigc_score = section.get("aigc_score", 0)
    dup_score = section.get("duplication_score", 0)
    reasons = section.get("reasons", [])
    title = section.get("title", "该段")
    reasons_text = "；".join(reasons[:2]) if reasons else ""

    # 主要问题是 AIGC 风险
    if aigc_score >= 0.65 and aigc_score > dup_score:
        why = f"「{title}」AIGC 风险 {aigc_score:.0%}"
        if reasons_text:
            why += f"，检测信号显示：{reasons_text}"
        else:
            why += "，表达方式较接近AI生成模式。"
        how = (
            "用你自己的研究经历重述这段内容：加入具体的数据编号、时间地点、访谈对象代号、"
            "实验步骤的细节描述，把'研究表明…具有重要意义'这类泛化表述换成你实际观察到的现象。"
        )
        return why, how

    # 主要问题是重复
    if dup_score >= 0.50 and dup_score >= aigc_score:
        why = f"「{title}」重复风险 {dup_score:.0%}"
        if reasons_text:
            why += f"，检测信号显示：{reasons_text}"
        else:
            why += "，与文内或库内其他段落存在较高重合。"
        how = (
            "保留你的核心论点，但重写句子结构：拆长句为短句（或反之），"
            "用同义替换关键动词和形容词，把引用内容用自己的话转述并标注出处。"
        )
        return why, how

    # 综合风险
    why = f"「{title}」综合风险 {section.get('combined_score', 0):.0%}"
    if reasons_text:
        why += f"，信号包括：{reasons_text}"
    how = (
        "先定位这段中最'模板化'的句子（通常是开头和结尾），"
        "用你研究的具体细节替换掉它们，中间论述保留但调整句式顺序。"
    )
    return why, how


def _expected_gain(section: dict[str, Any]) -> str:
    combined = section.get("combined_score", 0)
    if combined >= 0.70:
        return "这是当前拖分最严重的段落之一，改好后全文风险预计明显下降。"
    if combined >= 0.50:
        return "修改这段能有效拉低中高风险区间，减少后续返工量。"
    return "微调后能让整体表现更稳定，降低边界风险。"


def _build_mentor_brief(
    document: dict[str, Any],
    proxy_prediction: dict[str, Any],
    top_risk_sections: list[dict[str, Any]],
) -> dict[str, Any]:
    top_titles = (
        "、".join(item["title"] for item in top_risk_sections[:3]) or "正文主体"
    )
    return {
        "headline": "这版论文已经可以作为定向修改底稿，但不建议直接正式送检。",
        "summary": (
            f"当前系统预测查重约 {proxy_prediction['predicted_cnki_dup_low'] * 100:.1f}% 至 "
            f"{proxy_prediction['predicted_cnki_dup_high'] * 100:.1f}%，"
            f"AIGC 风险约 {proxy_prediction['predicted_cnki_aigc_low'] * 100:.1f}% 至 "
            f"{proxy_prediction['predicted_cnki_aigc_high'] * 100:.1f}%。"
            f"优先建议处理 {top_titles}。"
        ),
        "suggested_message": (
            f"老师您好，我先对《{document.get('title') or document.get('filename')}》做了提交前风险预检，"
            "目前主要问题集中在少数高风险段落和模板化表达较多的章节。"
            "我会先按高风险段落逐段修改，再做一次复检后再提交正式送检版本。"
        ),
    }


def _build_submission_checklist(
    top_risk_sections: list[dict[str, Any]],
    top_similarity_matches: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {"label": "先改 Top 3 高风险段，再决定是否全篇重写", "done": False},
        {"label": "复核所有直接引用、转述引用和参考文献格式", "done": False},
        {"label": "把模板化结论句替换成与你研究数据相关的表达", "done": False},
        {
            "label": f"重点复查 {min(len(top_similarity_matches), 5)} 条最强相似证据对应段落",
            "done": False,
        },
        {"label": "修改后至少做一次复检，对比区间是否明显下降", "done": False},
        {"label": "正式送检前保留修改说明，便于和导师沟通", "done": False},
    ]


def _comfort_score(
    proxy_prediction: dict[str, Any], top_risk_sections: list[dict[str, Any]]
) -> int:
    dup_percent = proxy_prediction["predicted_cnki_dup_high"] * 100
    aigc_percent = proxy_prediction["predicted_cnki_aigc_high"] * 100
    high_count = sum(1 for item in top_risk_sections if item["risk_level"] == "high")
    score = 100 - dup_percent * 0.42 - aigc_percent * 0.38 - high_count * 3.5
    return max(18, min(96, round(score)))


def _overall_risk(
    proxy_prediction: dict[str, Any], top_risk_sections: list[dict[str, Any]]
) -> str:
    if (
        proxy_prediction["predicted_cnki_dup_high"] >= 0.28
        or proxy_prediction["predicted_cnki_aigc_high"] >= 0.38
        or sum(1 for item in top_risk_sections if item["risk_level"] == "high") >= 3
    ):
        return "high"
    if (
        proxy_prediction["predicted_cnki_dup_high"] >= 0.16
        or proxy_prediction["predicted_cnki_aigc_high"] >= 0.24
        or sum(1 for item in top_risk_sections if item["risk_level"] != "low") >= 3
    ):
        return "medium"
    return "low"


def _one_line_judgement(overall_risk: str, comfort_score: int) -> str:
    if overall_risk == "high":
        return f"这版还不适合直接正式送检，但并不是推倒重来，先抓关键段改会更划算。当前风险指数 {comfort_score}/100。"
    if overall_risk == "medium":
        return f"整体已经有基础，但还存在几处会拖高结果的不稳定因素。当前风险指数 {comfort_score}/100。"
    return f"整体风险相对可控，建议做一次定向复查后再进入正式送检。当前风险指数 {comfort_score}/100。"


def _score_band(center: float, low: float, high: float, label: str) -> dict[str, Any]:
    return {
        "label": label,
        "center": round(center, 4),
        "low": round(low, 4),
        "high": round(high, 4),
        "center_percent": round(center * 100, 2),
        "low_percent": round(low * 100, 2),
        "high_percent": round(high * 100, 2),
    }


def _chapter_advice(title: str, combined: float) -> str:
    if combined >= 0.58:
        return f"{title} 当前风险最高，建议优先补充个性化分析、真实数据和研究过程。"
    if combined >= 0.32:
        return f"{title} 有一定风险，适合通过删模板句、改句式和补论证细节来降风险。"
    return f"{title} 整体较稳，复核引用和术语一致性即可。"


def _level_from_score(score: float) -> str:
    if score >= 0.62:
        return "high"
    if score >= 0.34:
        return "medium"
    return "low"


def _strip_combined(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "section_index": item["section_index"],
        "title": item["title"],
        "section_title": item["section_title"],
        "paragraph_index": item["paragraph_index"],
        "text_preview": item["text_preview"],
        "char_count": item["char_count"],
        "aigc_score": item["aigc_score"],
        "duplication_score": item["duplication_score"],
        "combined_score": item["combined_score"],
        "risk_level": item["risk_level"],
        "reasons": item["reasons"],
    }
