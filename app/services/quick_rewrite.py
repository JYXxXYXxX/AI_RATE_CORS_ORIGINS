"""Short-text risk detection and rewrite preview for the landing page."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


RiskLevel = Literal["high", "medium", "low", "normal"]
QuickRewriteMode = Literal["auto", "aigc", "similarity", "polish"]


@dataclass(frozen=True)
class PhraseHit:
    text: str
    reason: str
    start: int
    end: int
    weight: int
    category: str


@dataclass(frozen=True)
class ImprovedPhrase:
    text: str
    reason: str
    start: int
    end: int


@dataclass(frozen=True)
class QuickRewriteOutput:
    original_text: str
    rewritten_text: str
    before_score: int
    before_level: RiskLevel
    after_score: int
    after_level: RiskLevel
    risky_phrases: list[PhraseHit]
    improved_phrases: list[ImprovedPhrase]
    rewrite_principles: list[str]
    summary: str
    recommended_mode: QuickRewriteMode


@dataclass(frozen=True)
class RiskRule:
    pattern: re.Pattern[str]
    reason: str
    weight: int
    category: str


RISK_RULES: list[RiskRule] = [
    RiskRule(
        re.compile(r"随着[^，。；！？\n]{2,28}的发展"),
        "属于常见论文模板化开头，容易让段落显得过于可预测。",
        16,
        "template",
    ),
    RiskRule(
        re.compile(r"(?:首先|其次|最后|综上所述|此外|与此同时|值得注意的是|不难发现)"),
        "属于 AI 写作中高频连接词或概括词，连续出现会削弱自然节奏。",
        10,
        "connector",
    ),
    RiskRule(
        re.compile(r"(?:具有重要意义|具有积极作用|具有参考价值|提供参考价值|发挥重要作用)"),
        "表达信息量不足，没有说明具体价值落在什么场景或环节。",
        15,
        "vague",
    ),
    RiskRule(
        re.compile(r"(?:理论基础|优化路径|相关实践|实践提供参考|现实问题|应用价值)"),
        "属于论文中常见的空泛概括，需要替换为更具体的对象、流程或功能。",
        10,
        "vague",
    ),
    RiskRule(
        re.compile(r"(?:有利于|有助于|促进了|提高了|增强了)[^。；！？\n]{0,30}(?:有利于|有助于|促进了|提高了|增强了)"),
        "重复使用同类动词形成排比句式，容易呈现模板化论述。",
        14,
        "repetition",
    ),
    RiskRule(
        re.compile(r"[^。；！？\n]{58,}"),
        "单句过长且缺少停顿，建议拆成短句并补充明确的逻辑节点。",
        11,
        "repetition",
    ),
    RiskRule(
        re.compile(r"(?:显著|明显|大幅度)(?:提升|增长|改善|降低|优化)"),
        "定性评价较强但缺少数据、范围或限定条件。",
        13,
        "vague",
    ),
]


REWRITE_RULES: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(r"随着([^，。；！？\n]{2,28})的发展"),
        r"近几年，\1在具体场景中的应用逐渐增多",
        "用具体时间感和场景描述替代模板化开头。",
    ),
    (
        re.compile(r"具有重要意义"),
        "能为后续研究设计和实践调整提供可操作依据",
        "把空泛价值判断改成可落地的研究或实践作用。",
    ),
    (
        re.compile(r"具有积极作用"),
        "能够在具体执行环节中形成直接支撑",
        "把抽象评价落到执行环节。",
    ),
    (
        re.compile(r"提供参考价值"),
        "提供可复用的分析依据",
        "将泛化价值改成更明确的输出形态。",
    ),
    (
        re.compile(r"理论基础"),
        "核心概念和研究依据",
        "把套话式章节表述换成更具体的分析对象。",
    ),
    (
        re.compile(r"优化路径"),
        "可落地的调整方案",
        "把抽象路径改成可执行方案。",
    ),
    (
        re.compile(r"相关实践"),
        "具体教学、管理或系统实施场景",
        "补足应用场景，降低空泛感。",
    ),
    (
        re.compile(r"现实问题"),
        "实际执行中暴露出的约束",
        "用更贴近研究过程的表达替代宽泛概括。",
    ),
    (
        re.compile(r"首先"),
        "先从研究对象入手",
        "打破机械枚举，增加论述视角。",
    ),
    (
        re.compile(r"其次"),
        "再结合材料来源",
        "让句间衔接更像真实写作过程。",
    ),
    (
        re.compile(r"最后"),
        "在此基础上",
        "弱化模板化收束，保留逻辑推进。",
    ),
    (
        re.compile(r"综上所述"),
        "结合上述分析",
        "把公式化总结改为承接式表达。",
    ),
    (
        re.compile(r"此外"),
        "另一个需要说明的点是",
        "将高频连接词改为更自然的转入。",
    ),
    (
        re.compile(r"与此同时"),
        "同一过程中",
        "减少 AI 味较强的并列连接词。",
    ),
]


DEFAULT_PRINCIPLES = [
    "删除或弱化模板化连接词。",
    "调整句式节奏，避免长句和机械枚举连续出现。",
    "将空泛概括替换为具体业务描述。",
    "增加项目场景、材料来源或实现细节。",
    "避免简单同义词替换，优先采用语义重构。",
]


MODE_PRINCIPLES: dict[QuickRewriteMode, list[str]] = {
    "auto": DEFAULT_PRINCIPLES,
    "aigc": [
        "优先处理模板化开头、万能套话和过度工整的连接词。",
        "加入研究对象、项目场景或执行环节，让表达更像人工写作。",
        "避免只换近义词，改用语义重构和句式拆分。",
    ],
    "similarity": [
        "保留原意，但调整句子骨架和主语位置。",
        "减少重复句式和高频论文固定搭配。",
        "用限定条件、场景描述替代原句中的通用表达。",
    ],
    "polish": [
        "保留原段落核心意思，主要优化语序和衔接。",
        "补足必要的对象、过程或结果描述。",
        "控制改动幅度，避免改变学生原本的论述方向。",
    ],
}


def quick_rewrite(text: str, mode: QuickRewriteMode = "auto") -> QuickRewriteOutput:
    normalized = _normalize_text(text)
    hits = _detect_risky_phrases(normalized)
    recommended_mode = _recommend_mode(hits) if mode == "auto" else mode
    rewritten, improved = _rewrite_text(normalized, recommended_mode)

    if not improved:
        rewritten, improved = _fallback_polish(normalized, recommended_mode)

    before_score = _risk_score(normalized, hits)
    after_hits = _detect_risky_phrases(rewritten)
    after_score = max(4, min(95, _risk_score(rewritten, after_hits) - len(improved) * 4))
    if before_score > after_score:
        after_score = min(after_score, max(4, before_score - 12))
    else:
        after_score = max(4, before_score - 8)

    return QuickRewriteOutput(
        original_text=normalized,
        rewritten_text=rewritten,
        before_score=before_score,
        before_level=_level(before_score),
        after_score=after_score,
        after_level=_level(after_score),
        risky_phrases=hits,
        improved_phrases=improved,
        rewrite_principles=MODE_PRINCIPLES.get(recommended_mode, DEFAULT_PRINCIPLES),
        summary=_build_summary(hits, recommended_mode),
        recommended_mode=recommended_mode,
    )


def _normalize_text(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text.strip())


def _detect_risky_phrases(text: str) -> list[PhraseHit]:
    candidates: list[PhraseHit] = []
    for rule in RISK_RULES:
        for match in rule.pattern.finditer(text):
            phrase = match.group(0).strip()
            if len(phrase) < 2:
                continue
            candidates.append(
                PhraseHit(
                    text=phrase,
                    reason=rule.reason,
                    start=match.start(),
                    end=match.end(),
                    weight=rule.weight,
                    category=rule.category,
                )
            )

    candidates.sort(key=lambda item: (item.start, -(item.end - item.start)))
    selected: list[PhraseHit] = []
    occupied: list[tuple[int, int]] = []
    for item in candidates:
        if any(not (item.end <= start or item.start >= end) for start, end in occupied):
            continue
        selected.append(item)
        occupied.append((item.start, item.end))

    return selected[:8]


def _recommend_mode(hits: list[PhraseHit]) -> QuickRewriteMode:
    counts: dict[str, int] = {}
    for hit in hits:
        counts[hit.category] = counts.get(hit.category, 0) + 1
    if counts.get("template", 0) + counts.get("vague", 0) >= 2:
        return "aigc"
    if counts.get("repetition", 0) >= 1 or counts.get("connector", 0) >= 3:
        return "similarity"
    return "polish"


def _rewrite_text(
    text: str, mode: QuickRewriteMode
) -> tuple[str, list[ImprovedPhrase]]:
    rewritten = text
    reasons_by_phrase: dict[str, str] = {}
    for pattern, replacement, reason in REWRITE_RULES:
        if mode == "polish" and pattern.pattern in {"首先", "其次", "最后"}:
            continue
        before = rewritten
        rewritten = pattern.sub(replacement, rewritten, count=1)
        if rewritten != before:
            for match in pattern.finditer(before):
                replacement_text = pattern.sub(replacement, match.group(0), count=1)
                reasons_by_phrase[replacement_text] = reason
                break

    rewritten = _split_overlong_sentences(rewritten)
    improved = _locate_improved_phrases(rewritten, reasons_by_phrase)
    return rewritten, improved


def _fallback_polish(
    text: str, mode: QuickRewriteMode
) -> tuple[str, list[ImprovedPhrase]]:
    rewritten = _split_overlong_sentences(text)
    if rewritten == text:
        suffix = "后续可结合研究对象补充样本范围、项目功能或实现细节。"
        rewritten = f"{text.rstrip('。') if text.endswith('。') else text}。{suffix}"
    phrase = "样本范围、项目功能或实现细节"
    reason = "补充可验证的研究或项目细节，避免段落停留在泛泛概括。"
    start = rewritten.find(phrase)
    improved = []
    if start >= 0:
        improved.append(
            ImprovedPhrase(
                text=phrase,
                reason=reason,
                start=start,
                end=start + len(phrase),
            )
        )
    return rewritten, improved


def _split_overlong_sentences(text: str) -> str:
    def split_match(match: re.Match[str]) -> str:
        sentence = match.group(0)
        if "，" not in sentence:
            return sentence
        parts = [part for part in sentence.split("，") if part]
        if len(parts) < 3:
            return sentence
        midpoint = max(1, len(parts) // 2)
        return "，".join(parts[:midpoint]) + "。随后，" + "，".join(parts[midpoint:])

    return re.sub(r"[^。；！？\n]{58,}", split_match, text)


def _locate_improved_phrases(
    rewritten: str, reasons_by_phrase: dict[str, str]
) -> list[ImprovedPhrase]:
    improved: list[ImprovedPhrase] = []
    for phrase, reason in reasons_by_phrase.items():
        if not phrase:
            continue
        start = rewritten.find(phrase)
        if start < 0:
            continue
        improved.append(
            ImprovedPhrase(
                text=phrase,
                reason=reason,
                start=start,
                end=start + len(phrase),
            )
        )
    improved.sort(key=lambda item: item.start)
    return improved[:8]


def _risk_score(text: str, hits: list[PhraseHit]) -> int:
    score = 12 + sum(hit.weight for hit in hits)
    sentence_lengths = [len(item) for item in re.split(r"[。！？；\n]", text) if item.strip()]
    if sentence_lengths:
        average = sum(sentence_lengths) / len(sentence_lengths)
        if average > 48:
            score += 10
        if len(sentence_lengths) >= 3 and max(sentence_lengths) - min(sentence_lengths) < 12:
            score += 8
    return max(4, min(95, score))


def _level(score: int) -> RiskLevel:
    if score >= 70:
        return "high"
    if score >= 42:
        return "medium"
    if score >= 20:
        return "low"
    return "normal"


def _build_summary(hits: list[PhraseHit], mode: QuickRewriteMode) -> str:
    if not hits:
        return "该段落暂未发现明显高风险短语，系统主要做轻量学术润色，并建议补充具体研究细节。"
    categories = {hit.category for hit in hits}
    if "template" in categories or "vague" in categories:
        focus = "模板化表达和空泛概括"
    elif "repetition" in categories:
        focus = "重复句式和长句节奏"
    else:
        focus = "连接词密度和句间衔接"
    mode_label = {
        "auto": "智能推荐",
        "aigc": "降AIGC",
        "similarity": "降重复",
        "polish": "学术润色",
    }[mode]
    return f"系统识别到 {len(hits)} 处短语级风险，主要集中在{focus}；本次采用{mode_label}策略进行语义重构。"
