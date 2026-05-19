from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.schemas_unified import (
    RewriteWorkspaceHighlight,
    RewriteWorkspaceMetrics,
    RewriteWorkspaceResponse,
    RewriteWorkspaceRiskItem,
    RewriteWorkspaceSectionNode,
)


RISK_PRIORITY = {"normal": 0, "low": 1, "medium": 2, "high": 3}
RISK_REDUCTION = {"high": 7.0, "medium": 4.0, "low": 2.0, "normal": 0.0}
SENTENCE_PATTERN = re.compile(r"[^。！？!?；;]+[。！？!?；;]?|[^\s]+", re.UNICODE)


def _clean_text(value: Any) -> str:
    return str(value or "").replace("\x00", "").strip()


def _split_sentences(text: str) -> list[str]:
    clean = _clean_text(text)
    if not clean:
        return []
    parts = [part.strip() for part in SENTENCE_PATTERN.findall(clean)]
    return [part for part in parts if part]


def _resolve_risk_level(block: dict[str, Any], section_score: float | None = None) -> str:
    report_risk = block.get("report_risk") or {}
    report_level = str(report_risk.get("risk_level") or "").lower()
    if report_level in RISK_PRIORITY:
        return report_level

    score = _resolve_aigc_score(block, section_score)
    if score >= 70:
        return "high"
    if score >= 60:
        return "medium"
    if score >= 30:
        return "low"
    return "normal"


def _resolve_aigc_score(block: dict[str, Any], section_score: float | None = None) -> float:
    report_risk = block.get("report_risk") or {}
    report_aigc = report_risk.get("aigc_score")
    if report_aigc is not None:
        try:
            value = float(report_aigc)
            if value <= 1:
                value *= 100
            return max(0.0, min(100.0, value))
        except (TypeError, ValueError):
            pass

    for candidate in (
        block.get("risk_score"),
        (block.get("internal_risk") or {}).get("overall_risk"),
        section_score,
    ):
        if candidate is None:
            continue
        try:
            value = float(candidate)
            if value <= 1:
                value *= 100
            return max(0.0, min(100.0, value))
        except (TypeError, ValueError):
            continue
    return 0.0


def _build_diagnosis(level: str, reasons: list[str], block: dict[str, Any]) -> str:
    if reasons:
        return "；".join(str(item).strip() for item in reasons[:3] if str(item).strip())

    report_risk = block.get("report_risk") or {}
    risk_type = str(report_risk.get("risk_type") or "").lower()
    if risk_type == "similarity":
        return "该段与已有文献表达相近，复述方式偏集中，容易触发相似性风险。"
    if level == "high":
        return "该段表达模式较强，句式重复和模板化痕迹明显，建议优先重写。"
    if level == "medium":
        return "该段存在较明显的 AI 化表达，需要补足语义细节与论证层次。"
    if level == "low":
        return "该段整体可读，但仍有少量泛化表达，可继续做细节化处理。"
    return "该段当前风险较低，可保留为参考版本。"


def _build_rewrite_hint(level: str, reasons: list[str]) -> str:
    if any("模板" in reason or "套话" in reason for reason in reasons):
        return "减少套话式开头，改成带主语、对象和场景的信息表达。"
    if any("重复" in reason for reason in reasons):
        return "拆开重复句式，替换同构表达，避免连续使用相同论证模板。"
    if any("语义" in reason or "空泛" in reason for reason in reasons):
        return "补充限定词、研究对象和条件，让句子更具体。"
    if level == "high":
        return "优先重写整段核心句，改动句式结构和信息顺序，不要只做同义替换。"
    if level == "medium":
        return "保留原意，补充语境和动作细节，让表达更像人工写作。"
    if level == "low":
        return "局部微调即可，重点处理容易显得公式化的短句。"
    return "当前段落可暂不处理。"


def _build_principle(level: str, reasons: list[str]) -> str:
    if any("模板" in reason or "套话" in reason for reason in reasons):
        return "通过替换模板化起手式并重组句法结构，削弱固定生成痕迹。"
    if any("重复" in reason for reason in reasons):
        return "通过调整句序和论证节奏，降低重复表达带来的可识别模式。"
    if any("语义" in reason or "空泛" in reason for reason in reasons):
        return "通过增加限定条件和具体对象，提升信息密度，降低空泛句特征。"
    if level == "high":
        return "优先改写信息组织方式和主谓结构，从结构层面拉开与模板句的距离。"
    if level == "medium":
        return "在保持原意的前提下增加细节、变化句式，降低连续 AI 风格特征。"
    if level == "low":
        return "做轻量化表达优化，尽量保持原段结构稳定。"
    return "当前无需额外改写原理。"


def _build_highlights(text: str, level: str) -> list[RewriteWorkspaceHighlight]:
    sentences = _split_sentences(text)
    if not sentences:
        return []
    return [
        RewriteWorkspaceHighlight(text=sentence, risk_level=level)
        for sentence in sentences
    ]


def _priority_matches_block(block_text: str, priority_preview: str) -> bool:
    block_clean = _clean_text(block_text)
    preview_clean = _clean_text(priority_preview)
    if not block_clean or not preview_clean:
        return False
    if len(block_clean) < 24:
        return False
    short_block = block_clean[: min(len(block_clean), 48)]
    short_preview = preview_clean[: min(len(preview_clean), 96)]
    return short_block in preview_clean or short_preview[:24] in block_clean


def _priority_match_score(block: dict[str, Any], priority_item: dict[str, Any]) -> int:
    block_text = _clean_text(block.get("text"))
    preview = _clean_text(priority_item.get("text_preview"))
    if not block_text or not preview:
        return -1
    if len(block_text) < 24:
        return -1

    score = -1
    preview_head = preview[:24]
    block_head = block_text[:24]
    if preview_head and preview_head in block_text:
        score = 100
    elif block_head and block_head in preview:
        score = 80
    elif preview[:16] and preview[:16] in block_text:
        score = 60

    section_title = _clean_text(priority_item.get("section_title"))
    block_section_title = _clean_text(block.get("section_title"))
    if score >= 0 and section_title and block_section_title and section_title == block_section_title:
        score += 20
    return score


def _base_aigc_percent(run: dict[str, Any], report: dict[str, Any] | None) -> float:
    summary = (report or {}).get("summary") or {}
    predicted = summary.get("predicted_cnki_aigc") or {}
    for candidate in (
        summary.get("official_aigc_ratio"),
        predicted.get("center_percent"),
        (report or {}).get("ai_like_percent"),
        (run.get("result_json") or {}).get("ai_like_percent"),
    ):
        if candidate is None:
            continue
        try:
            return max(0.0, min(100.0, float(candidate)))
        except (TypeError, ValueError):
            continue
    return 0.0


def build_rewrite_workspace(
    *,
    run_id: str,
    run: dict[str, Any],
    document: dict[str, Any],
    blocks: list[dict[str, Any]],
    sections: list[dict[str, Any]],
    section_scores: list[dict[str, Any]],
    patches: list[dict[str, Any]],
    report: dict[str, Any] | None,
) -> RewriteWorkspaceResponse:
    score_map: dict[int, float] = {}
    reason_map: dict[int, list[str]] = {}
    for score in section_scores:
        if score.get("score_type") != "aigc":
            continue
        try:
            section_index = int(score.get("section_index"))
        except (TypeError, ValueError):
            continue
        try:
            score_map[section_index] = float(score.get("normalized_score") or 0.0)
        except (TypeError, ValueError):
            score_map[section_index] = 0.0
        raw_reasons = score.get("reasons") or []
        if isinstance(raw_reasons, list):
            reason_map[section_index] = [str(item) for item in raw_reasons if str(item).strip()]

    section_by_paragraph: dict[int, dict[str, Any]] = {}
    for section in sections:
        paragraph_index = section.get("paragraph_index")
        if paragraph_index is not None:
            try:
                section_by_paragraph[int(paragraph_index)] = section
            except (TypeError, ValueError):
                pass

    patch_map = {str(patch.get("block_id")): patch for patch in patches}
    priority_sections = (
        (report or {}).get("priority_sections")
        or (report or {}).get("top_risk_sections")
        or []
    )
    priority_by_section: dict[int, dict[str, Any]] = {}
    priority_by_block_id: dict[str, dict[str, Any]] = {}
    for item in priority_sections:
        if not isinstance(item, dict):
            continue
        section_index = item.get("section_index")
        if section_index is not None:
            try:
                priority_by_section[int(section_index)] = item
            except (TypeError, ValueError):
                pass
        best_block = None
        best_score = -1
        for block in blocks:
            if str(block.get("block_type")) != "paragraph":
                continue
            score = _priority_match_score(block, item)
            if score > best_score:
                best_score = score
                best_block = block
        if best_block is not None and best_score >= 60:
            priority_by_block_id[str(best_block["block_id"])] = item

    risk_items: list[RewriteWorkspaceRiskItem] = []
    section_nodes: dict[str, RewriteWorkspaceSectionNode] = {}
    level_counts = {"high": 0, "medium": 0, "low": 0}
    rewritten_count = 0
    ignored_count = 0

    for block in blocks:
        if str(block.get("block_type")) != "paragraph":
            continue
        text = _clean_text(block.get("text"))
        if not text:
            continue

        patch = patch_map.get(str(block.get("block_id")))
        current_text = _clean_text((patch or {}).get("new_text")) or text
        source_map = block.get("source_map") or {}
        paragraph_index = source_map.get("paragraphIndex")
        matched_section = None
        if paragraph_index is not None:
            try:
                matched_section = section_by_paragraph.get(int(paragraph_index))
            except (TypeError, ValueError):
                matched_section = None

        matched_section_index = (
            int(matched_section.get("section_index"))
            if matched_section and matched_section.get("section_index") is not None
            else None
        )
        section_index = matched_section_index if matched_section_index is not None else int(block.get("display_order", 0))
        section_title = (
            matched_section.get("section_title")
            if matched_section
            else block.get("section_title")
        ) or f"正文第 {section_index + 1} 段"

        section_score = score_map.get(section_index)
        priority_item = priority_by_block_id.get(str(block["block_id"]))
        if priority_item is not None:
            try:
                section_index = int(priority_item.get("section_index") or section_index)
            except (TypeError, ValueError):
                pass
            section_title = _clean_text(priority_item.get("section_title")) or section_title
            section_score = score_map.get(section_index, section_score)

        reasons = (
            [str(item) for item in (priority_item or {}).get("reasons", []) if str(item).strip()]
            or reason_map.get(section_index, [])
        )
        internal_reasons = (block.get("internal_risk") or {}).get("reasons") or []
        if not reasons and isinstance(internal_reasons, list):
            reasons = [str(item) for item in internal_reasons if str(item).strip()]

        level = str((priority_item or {}).get("risk_level") or "").lower() or _resolve_risk_level(block, section_score)
        patch_source_map = (patch or {}).get("source_map") or {}
        action = str(patch_source_map.get("action") or "").lower()
        if level == "normal" and action not in {"ignored", "replace", "rewrite"}:
            continue

        status = "pending"
        if action == "ignored":
            status = "ignored"
            ignored_count += 1
        elif patch and current_text != text:
            status = "applied"
            rewritten_count += 1

        score = _resolve_aigc_score(
            {"report_risk": {"aigc_score": (priority_item or {}).get("aigc_score")}}
            if priority_item and (priority_item.get("aigc_score") is not None)
            else block,
            section_score,
        )
        if level in level_counts:
            level_counts[level] += 1

        risk_id = f"risk_{block['block_id']}"
        section_id = f"sec_{section_index}"
        display_order = int(block.get("display_order") or 0)
        item = RewriteWorkspaceRiskItem(
            risk_id=risk_id,
            block_id=str(block["block_id"]),
            section_id=section_id,
            section_index=section_index,
            paragraph_index=paragraph_index,
            section_title=_clean_text(section_title),
            display_order=display_order,
            original_text=text,
            current_text=current_text,
            risk_level=level,
            aigc_score=round(score, 2),
            diagnosis=_build_diagnosis(level, reasons, block),
            rewrite_hint=_build_rewrite_hint(level, reasons),
            principle=_build_principle(level, reasons),
            reasons=reasons,
            status=status,
            highlights=_build_highlights(current_text or text, level),
            source_map=source_map or None,
        )
        risk_items.append(item)

        node = section_nodes.get(section_id)
        if node is None:
            node = RewriteWorkspaceSectionNode(
                section_id=section_id,
                section_index=section_index,
                paragraph_index=paragraph_index,
                title=_clean_text(section_title),
                risk_level=level,
                item_ids=[],
                item_count=0,
                risk_counts={"high": 0, "medium": 0, "low": 0, "normal": 0},
            )
            section_nodes[section_id] = node

        node.item_ids.append(risk_id)
        node.item_count += 1
        node.risk_counts[level] = int(node.risk_counts.get(level, 0)) + 1
        if RISK_PRIORITY[level] > RISK_PRIORITY[node.risk_level]:
            node.risk_level = level

    risk_items.sort(
        key=lambda item: (
            -RISK_PRIORITY[item.risk_level],
            -item.aigc_score,
            item.display_order,
        )
    )

    section_list = sorted(
        section_nodes.values(),
        key=lambda node: (
            -RISK_PRIORITY[node.risk_level],
            node.section_index,
            node.paragraph_index if node.paragraph_index is not None else node.section_index,
        ),
    )

    current_aigc = round(_base_aigc_percent(run, report), 2)
    reduction = sum(RISK_REDUCTION[item.risk_level] for item in risk_items if item.status == "applied")
    estimated_optimized = round(max(0.0, current_aigc - reduction), 2)
    warnings = [str(item) for item in ((report or {}).get("warnings") or []) if str(item).strip()]

    return RewriteWorkspaceResponse(
        run_id=run_id,
        document_id=str(document["id"]),
        title=document.get("title"),
        filename=str(document.get("filename") or "paper.docx"),
        mode=str(run.get("mode") or "estimate"),
        source_format=(
            str(document.get("file_ext") or "").lower().lstrip(".")
            or Path(str(document.get("filename") or "")).suffix.lower().lstrip(".")
            or None
        ),
        warnings=warnings,
        metrics=RewriteWorkspaceMetrics(
            current_aigc_percent=current_aigc,
            estimated_optimized_percent=estimated_optimized,
            rewritten_count=rewritten_count,
            ignored_count=ignored_count,
            total_risk_count=len(risk_items),
            high_count=level_counts["high"],
            medium_count=level_counts["medium"],
            low_count=level_counts["low"],
        ),
        sections=section_list,
        risk_items=risk_items,
    )
