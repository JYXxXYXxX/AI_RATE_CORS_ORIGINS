"""Block 匹配引擎 — 将知网报告风险片段映射到论文 DocumentBlock。

采用三级匹配策略：
1. 精确匹配（exact）：文本完全一致
2. 归一化匹配（normalized）：去除空格、标点、全角半角后匹配
3. 模糊匹配（fuzzy）：基于 difflib.SequenceMatcher 的相似度

匹配置信度阈值默认 0.75，低于此值的匹配不写入数据库，
而是放入 "未匹配" 列表供用户手动确认。
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.cnki_report_parser import CnkiRiskSpan
    from app.services.document_blocks import DocumentBlock


BlockLike = "DocumentBlock | dict[str, Any]"


@dataclass
class RiskMapping:
    span_id: str
    block_id: str
    match_method: str  # 'exact' | 'normalized' | 'fuzzy' | 'manual'
    match_confidence: float
    matched_text: str


def _block_value(block: Any, key: str, default: Any = None) -> Any:
    if isinstance(block, dict):
        return block.get(key, default)
    return getattr(block, key, default)


def _block_type(block: Any) -> str:
    return str(_block_value(block, "block_type", ""))


def _block_text(block: Any) -> str:
    value = _block_value(block, "text", "")
    return value if isinstance(value, str) else ""


def _block_id(block: Any) -> str:
    return str(_block_value(block, "block_id", ""))


# ---------------------------------------------------------------------------
# 文本归一化
# ---------------------------------------------------------------------------


def normalize_text(text: str) -> str:
    """文本归一化：统一全角半角、去除空白和标点差异。"""
    # NFKC 统一兼容字符（全角→半角）
    text = unicodedata.normalize("NFKC", text)
    # 去除所有空白字符
    text = re.sub(r"\s+", "", text)
    # 统一常见标点为半角
    text = (
        text.replace("，", ",")
        .replace("。", ".")
        .replace("；", ";")
        .replace("：", ":")
        .replace("？", "?")
        .replace("！", "!")
        .replace(""", '"')
        .replace(""", '"')
        .replace("'", "'")
        .replace("'", "'")
        .replace("（", "(")
        .replace("）", ")")
        .replace("【", "[")
        .replace("】", "]")
        .replace("《", "<")
        .replace("》", ">")
    )
    return text.strip().lower()


# ---------------------------------------------------------------------------
# 精确匹配
# ---------------------------------------------------------------------------


def exact_match(
    span_text: str, blocks: list[DocumentBlock | dict[str, Any]]
) -> list[RiskMapping]:
    """在 block.text 中精确查找 span_text 子串。"""
    mappings: list[RiskMapping] = []
    for block in blocks:
        block_type = _block_type(block)
        block_text = _block_text(block)
        block_id = _block_id(block)
        if block_type not in ("paragraph", "heading", "title"):
            continue
        if span_text in block_text:
            mappings.append(
                RiskMapping(
                    span_id="",
                    block_id=block_id,
                    match_method="exact",
                    match_confidence=1.0,
                    matched_text=block_text,
                )
            )
        elif block_text in span_text:
            # span 包含了整个 block
            mappings.append(
                RiskMapping(
                    span_id="",
                    block_id=block_id,
                    match_method="exact",
                    match_confidence=1.0,
                    matched_text=block_text,
                )
            )
    return mappings


# ---------------------------------------------------------------------------
# 归一化匹配
# ---------------------------------------------------------------------------


def normalized_match(
    span_text: str, blocks: list[DocumentBlock | dict[str, Any]]
) -> list[RiskMapping]:
    """归一化后的子串匹配。"""
    norm_span = normalize_text(span_text)
    if len(norm_span) < 10:
        return []

    mappings: list[RiskMapping] = []
    for block in blocks:
        block_type = _block_type(block)
        block_text = _block_text(block)
        block_id = _block_id(block)
        if block_type not in ("paragraph", "heading", "title"):
            continue
        norm_block = normalize_text(block_text)
        if norm_span in norm_block:
            mappings.append(
                RiskMapping(
                    span_id="",
                    block_id=block_id,
                    match_method="normalized",
                    match_confidence=1.0,
                    matched_text=block_text,
                )
            )
        elif norm_block in norm_span and len(norm_block) >= 10:
            mappings.append(
                RiskMapping(
                    span_id="",
                    block_id=block_id,
                    match_method="normalized",
                    match_confidence=1.0,
                    matched_text=block_text,
                )
            )
    return mappings


# ---------------------------------------------------------------------------
# 模糊匹配
# ---------------------------------------------------------------------------


def fuzzy_match(
    span_text: str,
    blocks: list[DocumentBlock | dict[str, Any]],
    threshold: float = 0.75,
) -> list[RiskMapping]:
    """使用 difflib.SequenceMatcher 计算文本相似度。

    策略：
    - 计算 span 与每个 block 的 overall ratio
    - 同时计算 span 在 block 中的 best partial match ratio
    - 取两者较高值作为 confidence
    """
    norm_span = normalize_text(span_text)
    if len(norm_span) < 10:
        return []

    mappings: list[RiskMapping] = []
    for block in blocks:
        block_type = _block_type(block)
        block_text = _block_text(block)
        block_id = _block_id(block)
        if block_type not in ("paragraph", "heading", "title"):
            continue
        norm_block = normalize_text(block_text)
        if len(norm_block) < 10:
            continue

        # 整体相似度
        overall_ratio = difflib.SequenceMatcher(None, norm_span, norm_block).ratio()

        # 最佳局部匹配（span 作为较短字符串在 block 中查找最佳匹配）
        if len(norm_span) <= len(norm_block):
            partial_ratio = _partial_ratio(norm_span, norm_block)
        else:
            partial_ratio = _partial_ratio(norm_block, norm_span)

        confidence = max(overall_ratio, partial_ratio)

        if confidence >= threshold:
            mappings.append(
                RiskMapping(
                    span_id="",
                    block_id=block_id,
                    match_method="fuzzy",
                    match_confidence=round(confidence, 4),
                    matched_text=block_text,
                )
            )

    return mappings


def _partial_ratio(shorter: str, longer: str) -> float:
    """计算 shorter 在 longer 中的最佳子串匹配率。"""
    if not shorter:
        return 0.0
    best = 0.0
    window_len = len(shorter)
    for i in range(len(longer) - window_len + 1):
        window = longer[i : i + window_len]
        ratio = difflib.SequenceMatcher(None, shorter, window).ratio()
        if ratio > best:
            best = ratio
    return best


# ---------------------------------------------------------------------------
# 三级匹配策略
# ---------------------------------------------------------------------------


def match_spans_to_blocks(
    spans: list[CnkiRiskSpan],
    blocks: list[DocumentBlock | dict[str, Any]],
    min_confidence: float = 0.75,
) -> tuple[list[RiskMapping], list[CnkiRiskSpan]]:
    """将知网报告风险片段映射到 DocumentBlock。

    Args:
        spans: 知网报告解析出的风险片段
        blocks: 论文的 DocumentBlock 列表
        min_confidence: 模糊匹配最小置信度

    Returns:
        (成功映射列表, 未匹配 spans 列表)
    """
    mappings: list[RiskMapping] = []
    unmatched: list[CnkiRiskSpan] = []

    # 预过滤：只保留有意义的 block
    text_blocks = [
        b for b in blocks
        if _block_type(b) in ("paragraph", "heading", "title")
        and len(_block_text(b)) >= 10
    ]

    for span in spans:
        span_text = span.text.strip()
        if len(span_text) < 10:
            unmatched.append(span)
            continue

        matched = False
        best_mapping: RiskMapping | None = None

        # Level 1: 精确匹配
        exact_mappings = exact_match(span_text, text_blocks)
        if exact_mappings:
            best_mapping = RiskMapping(
                span_id=span.span_id,
                block_id=exact_mappings[0].block_id,
                match_method="exact",
                match_confidence=1.0,
                matched_text=exact_mappings[0].matched_text,
            )
            matched = True

        # Level 2: 归一化匹配
        if not matched:
            norm_mappings = normalized_match(span_text, text_blocks)
            if norm_mappings:
                best_mapping = RiskMapping(
                    span_id=span.span_id,
                    block_id=norm_mappings[0].block_id,
                    match_method="normalized",
                    match_confidence=1.0,
                    matched_text=norm_mappings[0].matched_text,
                )
                matched = True

        # Level 3: 模糊匹配
        if not matched:
            fuzzy_mappings = fuzzy_match(span_text, text_blocks, threshold=min_confidence)
            if fuzzy_mappings:
                # 取置信度最高的
                fuzzy_mappings.sort(key=lambda m: m.match_confidence, reverse=True)
                best = fuzzy_mappings[0]
                best_mapping = RiskMapping(
                    span_id=span.span_id,
                    block_id=best.block_id,
                    match_method="fuzzy",
                    match_confidence=best.match_confidence,
                    matched_text=best.matched_text,
                )
                matched = True

        if matched and best_mapping:
            mappings.append(best_mapping)
        else:
            unmatched.append(span)

    return mappings, unmatched
