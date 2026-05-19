"""Short-text risk detection and rewrite preview for the landing page."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.services.rewrite_strategy import apply_learned_rewrite_style, has_verifiable_detail


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
        "模板化开头：属于常见论文开场句，容易让段落显得过于可预测。",
        16,
        "template",
    ),
    RiskRule(
        re.compile(r"(?:首先|其次|最后|综上所述|此外|与此同时|值得注意的是|不难发现)"),
        "论文常见套话：高频连接词或概括词连续出现，会削弱自然节奏。",
        10,
        "connector",
    ),
    RiskRule(
        re.compile(r"(?:并能够)?为相关实践提供参考价值"),
        "表达空泛：没有说明参考价值具体服务于哪个对象或业务环节。",
        16,
        "vague",
    ),
    RiskRule(
        re.compile(r"(?:并)?为相关研究提供(?:一定)?参考价值"),
        "表达空泛：没有说明参考价值具体落在哪类研究、数据或方法上。",
        16,
        "vague",
    ),
    RiskRule(
        re.compile(r"(?:(?:发挥着)?越来越重要的作用|具有较强的现实意义|具有重要的现实意义|较强的现实意义|重要的现实意义)"),
        "AI 高频价值判断：只给结论，没有说明作用发生在哪个流程或对象上。",
        14,
        "vague",
    ),
    RiskRule(
        re.compile(r"能够帮助[^，。；！？\n]{2,28}(?:提高|提升|优化)[^，。；！？\n]{2,28}(?:效率|质量|水平|能力)"),
        "泛化功能价值：需要把“帮助提高效率”改成具体处理步骤或可验证结果。",
        15,
        "vague",
    ),
    RiskRule(
        re.compile(r"(?:具有重要意义|具有积极作用|具有参考价值|提供参考价值|发挥重要作用)"),
        "表达空泛：没有说明具体价值落在什么对象、场景或环节。",
        15,
        "vague",
    ),
    RiskRule(
        re.compile(r"(?:理论基础|优化路径|相关实践|实践提供参考|现实问题|应用价值)"),
        "缺少具体对象或数据：需要替换为更明确的对象、流程或业务功能。",
        10,
        "vague",
    ),
    RiskRule(
        re.compile(r"(?:有利于|有助于|促进了|提高了|增强了)[^。；！？\n]{0,30}(?:有利于|有助于|促进了|提高了|增强了)"),
        "重复句式：同类动词形成排比，容易呈现模板化论述。",
        14,
        "repetition",
    ),
    RiskRule(
        re.compile(r"[^。；！？\n]{58,}"),
        "句式节奏单一：单句过长且缺少停顿，建议拆成短句并补充逻辑节点。",
        11,
        "repetition",
    ),
    RiskRule(
        re.compile(r"(?:显著|明显|大幅度)(?:提升|增长|改善|降低|优化)"),
        "表达空泛：定性评价较强，但缺少数据、范围或限定条件。",
        13,
        "vague",
    ),
]


DEFAULT_PRINCIPLES = [
    "删除高频模板化开头。",
    "将空泛表达替换成具体作用。",
    "保留原文研究对象和业务场景。",
    "调整长短句节奏。",
    "避免只做同义词替换，采用语义重构。",
]


MODE_PRINCIPLES: dict[QuickRewriteMode, list[str]] = {
    "auto": DEFAULT_PRINCIPLES,
    "aigc": [
        "删除高频模板化开头。",
        "将空泛表达替换成具体作用。",
        "保留原文研究对象和业务场景。",
        "调整长短句节奏。",
        "避免只做同义词替换，采用语义重构。",
    ],
    "similarity": [
        "保留原文研究对象和业务场景。",
        "调整句子骨架和主语位置。",
        "将重复句式改成递进或因果表达。",
        "用具体作用替代通用固定搭配。",
        "避免只做同义词替换，采用语义重构。",
    ],
    "polish": [
        "保留原文研究对象和业务场景。",
        "优化语序和句间衔接。",
        "将空泛表达替换成具体作用。",
        "调整长短句节奏。",
        "控制改动幅度，避免改变原文论述方向。",
    ],
}


def quick_rewrite(text: str, mode: QuickRewriteMode = "auto") -> QuickRewriteOutput:
    normalized = _normalize_text(text)
    hits = _detect_risky_phrases(normalized)
    recommended_mode = _recommend_mode(hits) if mode == "auto" else mode
    if hits:
        rewritten, improved = _rewrite_text(normalized, recommended_mode)
    else:
        rewritten = apply_learned_rewrite_style(normalized)
        improved = []

    if hits and not improved:
        rewritten, improved = _fallback_polish(normalized, recommended_mode)

    before_score = _risk_score(normalized, hits)
    after_hits = _detect_risky_phrases(rewritten)
    after_score = _estimate_after_score(before_score, _risk_score(rewritten, after_hits), len(improved))

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
            if rule.category == "repetition" and has_verifiable_detail(phrase):
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

    candidates.sort(key=lambda item: (item.start, -item.weight, item.end - item.start))
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
    context = _infer_context(text)
    rewritten = text
    reasons_by_phrase: dict[str, str] = {}

    for hit in _detect_risky_phrases(text):
        replacement, reason = _replacement_for_hit(hit, context, mode)
        if not replacement or replacement == hit.text:
            continue
        if hit.text not in rewritten:
            continue
        rewritten = rewritten.replace(hit.text, replacement, 1)
        reasons_by_phrase[replacement] = reason

    problem_rewritten = _rewrite_problem_chain(rewritten, context)
    if problem_rewritten != rewritten:
        rewritten = problem_rewritten
        if "这类平台的问题主要集中在" in rewritten:
            reasons_by_phrase["这类平台的问题主要集中在"] = "拆解问题链：把连续罗列的问题改成具体环节。"
        if "信息断点" in rewritten:
            reasons_by_phrase["信息断点"] = "落到用户动作：把抽象需求改成使用过程中会遇到的具体断点。"

    rewritten = _split_overlong_sentences(rewritten)
    rewritten = _normalize_punctuation(rewritten)
    rewritten = apply_learned_rewrite_style(rewritten)
    improved = _locate_improved_phrases(rewritten, reasons_by_phrase)
    return rewritten, improved


def _fallback_polish(
    text: str, mode: QuickRewriteMode
) -> tuple[str, list[ImprovedPhrase]]:
    context = _infer_context(text)
    rewritten = _split_overlong_sentences(text)
    rewritten = apply_learned_rewrite_style(rewritten)
    if rewritten == text:
        suffix = f"后续可结合{context['actor']}的{context['focus']}补充更具体的材料或案例。"
        rewritten = f"{text.rstrip('。') if text.endswith('。') else text}。{suffix}"
    phrase = f"{context['actor']}的{context['focus']}"
    reason = "补充业务对象：围绕原文对象增加可验证的场景细节，避免偏离主题。"
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


def _infer_context(text: str) -> dict[str, str]:
    actor = "研究对象"
    scene = "原文场景"
    focus = "具体作用"

    if "个人财务" in text or "财务管理" in text:
        actor = "用户"
        scene = "个人财务管理场景"
        focus = "收支记录、预算提醒和月度复盘"
    elif "绿色植物" in text or "种子电商" in text or "家庭园艺" in text:
        actor = "家庭园艺用户"
        scene = "绿色植物种子电商场景"
        focus = "品种信息、种植指导、社区互动和库存管理"
    elif "旅游企业" in text:
        actor = "旅游企业"
        scene = "旅游服务与营销场景"
    elif "旅游" in text:
        actor = "旅游行业主体"
        scene = "旅游服务场景"
    elif "企业" in text:
        actor = "企业"
        scene = "企业实践场景"
    elif "系统" in text or "平台" in text:
        actor = "系统"
        scene = "系统应用场景"
    elif "学生" in text or "教学" in text or "教育" in text:
        actor = "教育实践主体"
        scene = "教学应用场景"

    if "营销" in text and "服务" in text:
        focus = "服务内容与营销策略"
    elif "营销" in text:
        focus = "营销策略"
    elif "绿色植物" in text or "种子电商" in text or "家庭园艺" in text:
        focus = "品种信息、种植指导、社区互动和库存管理"
    elif "服务" in text:
        focus = "服务内容"
    elif "系统" in text or "功能" in text:
        focus = "功能设计"
    elif "教学" in text or "教育" in text:
        focus = "教学实践"

    return {"actor": actor, "scene": scene, "focus": focus}


def _replacement_for_hit(
    hit: PhraseHit, context: dict[str, str], mode: QuickRewriteMode
) -> tuple[str, str]:
    text = hit.text
    actor = context["actor"]
    scene = context["scene"]
    focus = context["focus"]

    if hit.category == "repetition":
        problem_rewrite = _rewrite_problem_chain(text, context)
        if problem_rewrite != text:
            return (
                problem_rewrite,
                "拆解问题链：把连续罗列的问题改成具体环节，再把用户需求落到可理解的使用动作上。",
            )

    template_match = re.fullmatch(r"随着(.+)的发展", text)
    if template_match:
        subject = template_match.group(1)
        return (
            f"近年来，{subject}在{scene}中的应用逐渐增多",
            "增加具体场景：保留原文对象，降低'随着……的发展'的模板化痕迹。",
        )

    if text in {"具有重要意义", "具有积极作用", "发挥重要作用"}:
        return (
            f"能为{actor}优化{focus}提供依据",
            "保留原意但降低模板化表达：把空泛价值改成面向原文对象的具体作用。",
        )
    if text in {"具有参考价值", "提供参考价值"}:
        return (
            f"可为{actor}后续调整{focus}提供参考",
            "补充业务对象：说明参考价值具体服务于谁、作用于什么环节。",
        )
    if re.fullmatch(r"(?:并)?为相关研究提供(?:一定)?参考价值", text):
        return (
            f"可为后续研究比较{focus}与实际使用效果提供参照",
            "补充研究对象：把泛泛的参考价值落到可比较的功能和使用效果上。",
        )
    if text in {"为相关实践提供参考价值", "并能够为相关实践提供参考价值"}:
        return (
            f"可为{actor}后续调整{focus}提供参考",
            "补充业务对象：将泛泛的'相关实践'落到原文对象和业务环节。",
        )
    if text in {"发挥着越来越重要的作用", "越来越重要的作用"}:
        return (
            f"可以用于{scene}中的具体管理环节",
            "落到具体场景：减少空泛价值判断，说明作用发生的业务位置。",
        )
    if text in {"具有较强的现实意义", "具有重要的现实意义", "较强的现实意义", "重要的现实意义"}:
        return (
            f"在{scene}中具有直接应用价值",
            "落到具体场景：减少空泛价值判断，说明作用发生的业务位置。",
        )
    if re.fullmatch(r"能够帮助[^，。；！？\n]{2,28}(?:提高|提升|优化)[^，。；！？\n]{2,28}(?:效率|质量|水平|能力)", text):
        return (
            f"可以帮助{actor}完成{focus}中的记录、提醒和复盘步骤",
            "替换泛化价值：用具体流程替代'提高效率'这类空泛表达。",
        )
    if text == "相关实践" or text == "实践提供参考":
        return (
            f"{actor}在{scene}中的具体实践",
            "补充业务对象：沿用原文行业场景，不引入无关领域。",
        )
    if text == "理论基础":
        return (
            f"{focus}相关概念和研究依据",
            "保留原意但降低模板化表达：把抽象章节套话改成具体分析对象。",
        )
    if text == "优化路径":
        return (
            f"{actor}优化{focus}的具体路径",
            "补充业务对象：明确谁在优化、优化什么。",
        )
    if text == "现实问题":
        return (
            f"{actor}在{scene}中遇到的实际问题",
            "增加具体场景：把宽泛问题落回原文业务场景。",
        )
    if text in {"首先", "其次", "最后"} and mode != "polish":
        replacement_map = {
            "首先": "先从原文研究对象入手",
            "其次": "再结合具体场景",
            "最后": "在此基础上",
        }
        return (
            replacement_map[text],
            "调整句式节奏：减少机械枚举，保留原文论述顺序。",
        )
    if text == "综上所述":
        return ("结合上述分析", "调整句式节奏：弱化公式化总结。")
    if text == "此外":
        return ("另一个需要说明的点是", "调整句式节奏：用更自然的转入替代高频连接词。")
    if text == "与此同时":
        return ("同一过程中", "调整句式节奏：减少并列连接词的 AI 味。")
    return ("", "")


def _rewrite_problem_chain(text: str, context: dict[str, str]) -> str:
    rewritten = text
    problem_match = re.search(
        r"(?P<prefix>然而，|但是，|但)?(?P<subject>[^。；！？]{2,42}?)(?:普遍)?存在(?P<problems>[^。；！？]{8,130}?)(?:等)?问题",
        rewritten,
    )
    if problem_match:
        subject = problem_match.group("subject").strip("，, ")
        problems = _split_problem_items(problem_match.group("problems"))
        if len(problems) >= 2:
            subject_label = "这类平台" if "平台" in subject else subject
            problem_text = "、".join(problems)
            suffix = "" if problem_match.end() < len(rewritten) and rewritten[problem_match.end()] in "。；！？" else "。"
            replacement = f"{subject_label}的问题主要集中在{_cn_count(len(problems))}个环节：{problem_text}{suffix}"
            rewritten = (
                rewritten[: problem_match.start()]
                + replacement
                + rewritten[problem_match.end() :]
            )

    demand_match = re.search(
        r"这使得(?P<target>[^，。；！？]{1,36})难以满足(?P<who>[^，。；！？]{1,36})对于(?P<needs>[^。；！？]{4,90})的(?:深层)?需求",
        rewritten,
    )
    if demand_match:
        who = demand_match.group("who").strip()
        actions = _need_actions(_split_need_items(demand_match.group("needs")), context)
        suffix = "" if demand_match.end() < len(rewritten) and rewritten[demand_match.end()] in "。；！？" else "。"
        replacement = f"因此，{who}在{actions}时容易出现信息断点{suffix}"
        rewritten = (
            rewritten[: demand_match.start()]
            + replacement
            + rewritten[demand_match.end() :]
        )

    return rewritten


def _split_problem_items(raw: str) -> list[str]:
    cleaned = raw.replace("以及", "、").replace("及", "、").replace("和", "、")
    items = [item.strip("，, 、。；;") for item in cleaned.split("、")]
    return [item for item in items if len(item) >= 2][:6]


def _split_need_items(raw: str) -> list[str]:
    cleaned = raw.replace("以及", "、").replace("及", "、").replace("和", "、")
    items = [item.strip("，, 、。；;") for item in cleaned.split("、")]
    return [item for item in items if item][:5]


def _need_actions(needs: list[str], context: dict[str, str]) -> str:
    actions: list[str] = []
    for need in needs:
        if "透明" in need or "信息" in need:
            actions.append("核对产品信息")
        elif "指导" in need or "系统" in need or "知识" in need:
            actions.append("查找连续的种植指导")
        elif "情感" in need or "交流" in need or "社区" in need:
            actions.append("参与社区交流")
        elif "库存" in need:
            actions.append("确认库存状态")
    if not actions:
        if "种子电商" in context["scene"]:
            actions = ["核对品种信息", "查找养护建议", "交流种植经验"]
        else:
            actions = [f"使用{context['focus']}"]
    deduped = list(dict.fromkeys(actions))
    return "、".join(deduped[:4])


def _cn_count(value: int) -> str:
    return {2: "两", 3: "三", 4: "四", 5: "五", 6: "六"}.get(value, str(value))


def _split_overlong_sentences(text: str) -> str:
    def split_match(match: re.Match[str]) -> str:
        sentence = match.group(0)
        if "，" not in sentence:
            return sentence
        parts = [part for part in sentence.split("，") if part]
        if len(parts) < 3:
            return sentence
        midpoint = max(1, len(parts) // 2)
        if len(parts[0]) <= 4 and len(parts) >= 3:
            midpoint = min(2, len(parts) - 1)
        return "，".join(parts[:midpoint]) + "。随后，" + "，".join(parts[midpoint:])

    return re.sub(r"[^。；！？\n]{58,}", split_match, text)


def _normalize_punctuation(text: str) -> str:
    text = re.sub(r"。{2,}", "。", text)
    text = re.sub(r"，{2,}", "，", text)
    return text


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
    if not hits and has_verifiable_detail(text):
        return 12
    score = 12 + sum(hit.weight for hit in hits)
    sentence_lengths = [len(item) for item in re.split(r"[。！？；\n]", text) if item.strip()]
    if sentence_lengths:
        average = sum(sentence_lengths) / len(sentence_lengths)
        if average > 48:
            score += 10
        if len(sentence_lengths) >= 3 and max(sentence_lengths) - min(sentence_lengths) < 12:
            score += 8
    return max(4, min(95, score))


def _estimate_after_score(before_score: int, rewritten_score: int, improved_count: int) -> int:
    reduction = 8 + min(12, improved_count * 3)
    if before_score >= 70:
        floor = 46
    elif before_score >= 42:
        floor = 28
    elif before_score >= 20:
        floor = 16
    else:
        floor = 10
    estimated = min(rewritten_score, before_score - reduction)
    return max(floor, min(before_score - 4, estimated))


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
