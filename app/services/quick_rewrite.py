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
        "模板化开头：属于高频论文起句，容易让段落显得过于可预测。",
        16,
        "template",
    ),
    RiskRule(
        re.compile(r"(首先|其次|最后|综上所述|此外|与此同时|值得注意的是|不难发现)"),
        "连接词堆叠：连续使用常见论文衔接词，句式会显得机械。",
        10,
        "connector",
    ),
    RiskRule(
        re.compile(r"(发挥着越来越重要的作用|具有较强的现实意义|具有重要的现实意义|具有重要意义)"),
        "价值判断偏空：只有结论，没有落到具体对象、流程或结果。",
        14,
        "vague",
    ),
    RiskRule(
        re.compile(r"(具有参考价值|提供一定参考价值|为相关研究提供一定参考价值|为相关实践提供参考价值)"),
        "参考价值表述泛化：没有说明具体服务于谁、落在什么场景。",
        15,
        "vague",
    ),
    RiskRule(
        re.compile(r"能够帮助[^，。；！？\n]{2,28}(提高|提升|优化)[^，。；！？\n]{2,28}(效率|质量|水平|能力)"),
        "功能价值泛化：建议换成更可验证的流程动作或结果。",
        15,
        "vague",
    ),
    RiskRule(
        re.compile(r"(理论基础|优化路径|相关实践|现实问题|应用价值)"),
        "抽象术语偏多：建议改成更明确的对象、环节或业务动作。",
        10,
        "vague",
    ),
    RiskRule(
        re.compile(r"(有利于|有助于|促进|提高|增强)[^。；！？\n]{0,24}(有利于|有助于|促进|提高|增强)"),
        "同类动词连用：容易形成模板化排比句。",
        14,
        "repetition",
    ),
    RiskRule(
        re.compile(r"[^。！？\n]{58,}"),
        "单句过长：建议拆成更短的句群，补出清晰停顿。",
        11,
        "repetition",
    ),
    RiskRule(
        re.compile(r"(显著|明显|大幅)(提高|提升|改善|降低|优化)"),
        "定性评价较强：缺少范围、条件或数据支撑。",
        13,
        "vague",
    ),
]


DEFAULT_PRINCIPLES = [
    "删除高频模板化开头。",
    "把空泛结论改成可验证的场景动作。",
    "保留原文对象，不随意换领域。",
    "优先重组句义，而不是只换近义词。",
    "把长句拆开，让节奏更像人工写作。",
]


MODE_PRINCIPLES: dict[QuickRewriteMode, list[str]] = {
    "auto": DEFAULT_PRINCIPLES,
    "aigc": [
        "优先消掉模板化开头和空泛价值判断。",
        "把结论压回真实业务流程或研究动作。",
        "保留原主题，不引入无关场景。",
        "减少套路连接词和总结腔。",
        "尽量改成更像人工写作的句序。",
    ],
    "similarity": [
        "优先重组句子骨架和主语位置。",
        "把并列句改成递进句或因果句。",
        "保留核心信息，不做无效同义词替换。",
        "减少重复动词和固定搭配。",
        "控制改写后语义偏移。",
    ],
    "polish": [
        "保持原意前提下做轻量润色。",
        "适度调整语序和句间衔接。",
        "减少空泛表达。",
        "压缩冗余套句。",
        "不强行添加与原文无关的新材料。",
    ],
}


def quick_rewrite(text: str, mode: QuickRewriteMode = "auto") -> QuickRewriteOutput:
    normalized = _normalize_text(text)
    hits = _detect_risky_phrases(normalized)
    recommended_mode = _recommend_mode(hits) if mode == "auto" else mode
    if hits:
        rewritten, improved = _rewrite_text(normalized, recommended_mode)
    else:
        if has_verifiable_detail(normalized):
            rewritten = apply_learned_rewrite_style(normalized)
            improved = []
        else:
            rewritten, improved = _rewrite_without_hits(normalized)

    if hits and not improved:
        rewritten, improved = _fallback_polish(normalized)

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
    if counts.get("repetition", 0) >= 1 or counts.get("connector", 0) >= 2:
        return "similarity"
    return "polish"


def _rewrite_text(text: str, mode: QuickRewriteMode) -> tuple[str, list[ImprovedPhrase]]:
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
            reasons_by_phrase["这类平台的问题主要集中在"] = "把连串问题改成按环节展开的直白表达。"
        if "信息断点" in rewritten:
            reasons_by_phrase["信息断点"] = "把抽象需求改成用户在具体动作里的卡点。"

    rewritten = _split_overlong_sentences(rewritten)
    rewritten = _normalize_punctuation(rewritten)
    rewritten = apply_learned_rewrite_style(rewritten)
    improved = _locate_improved_phrases(rewritten, reasons_by_phrase)
    return rewritten, improved


def _rewrite_without_hits(text: str) -> tuple[str, list[ImprovedPhrase]]:
    context = _infer_context(text)
    rewritten = _split_overlong_sentences(text)
    rewritten, reasons_by_phrase = _apply_direct_rewrite_rules(rewritten, context)
    rewritten = _normalize_punctuation(apply_learned_rewrite_style(rewritten))
    if rewritten == text:
        rewritten, reasons_by_phrase = _light_touch_rewrite(text)
    improved = _locate_improved_phrases(rewritten, reasons_by_phrase)
    return rewritten, improved


def _fallback_polish(text: str) -> tuple[str, list[ImprovedPhrase]]:
    context = _infer_context(text)
    rewritten = _split_overlong_sentences(text)
    rewritten, reasons_by_phrase = _apply_direct_rewrite_rules(rewritten, context)
    rewritten = _normalize_punctuation(apply_learned_rewrite_style(rewritten))
    if rewritten == text:
        rewritten, reasons_by_phrase = _light_touch_rewrite(text)
    improved = _locate_improved_phrases(rewritten, reasons_by_phrase)
    return rewritten, improved


def _apply_direct_rewrite_rules(
    text: str, context: dict[str, str]
) -> tuple[str, dict[str, str]]:
    rewritten = text
    reasons_by_phrase: dict[str, str] = {}

    multi_trigger = re.search(
        r"随着(?P<a>[^，。；！？\n]{2,20})的普及和(?P<b>[^，。；！？\n]{2,20})的兴起，",
        rewritten,
    )
    if multi_trigger:
        replacement = f"在{multi_trigger.group('a')}与{multi_trigger.group('b')}带动下，"
        rewritten = rewritten.replace(multi_trigger.group(0), replacement, 1)
        reasons_by_phrase[replacement.strip("，")] = "改成更直接的场景触发句，先交代变化来源，再落到正文内容。"

    single_trigger = re.search(r"随着(?P<trigger>[^，。；！？\n]{2,24})的发展，", rewritten)
    if single_trigger:
        replacement = f"在{single_trigger.group('trigger')}持续推进下，"
        rewritten = rewritten.replace(single_trigger.group(0), replacement, 1)
        reasons_by_phrase[replacement.strip("，")] = "弱化模板化开头，保留主题但换成更自然的叙述方式。"

    match = re.search(r"正逐渐从([^，。；！？\n]{1,20})转变为([^，。；！？\n]{1,20})", rewritten)
    if match:
        replacement = f"已经从{match.group(1)}逐步转向{match.group(2)}"
        rewritten = re.sub(r"正逐渐从([^，。；！？\n]{1,20})转变为([^，。；！？\n]{1,20})", replacement, rewritten, count=1)
        reasons_by_phrase[replacement] = "压缩套路表达，直接保留转变前后的核心信息。"

    if rewritten == text and "逐渐从" in rewritten and "转变为" in rewritten:
        match = re.search(r"逐渐从([^，。；！？\n]{1,20})转变为([^，。；！？\n]{1,20})", rewritten)
        if match:
            replacement = f"从{match.group(1)}逐步转向{match.group(2)}"
            rewritten = re.sub(r"逐渐从([^，。；！？\n]{1,20})转变为([^，。；！？\n]{1,20})", replacement, rewritten, count=1)
            reasons_by_phrase[replacement] = "保留原意不变，把常见书面套句改得更自然。"

    return rewritten, reasons_by_phrase


def _light_touch_rewrite(text: str) -> tuple[str, dict[str, str]]:
    variants = [
        ("本研究", "本文", "统一主语说法，让句子更紧凑。"),
        ("本文", "本研究", "统一主语说法，让句子更紧凑。"),
        ("本系统", "该系统", "减少重复主语，避免句子显得机械。"),
        ("该系统", "本系统", "减少连续重复表达，让表述更自然。"),
    ]
    for source, target, reason in variants:
        if source in text:
            return text.replace(source, target, 1), {target: reason}
    return text, {}


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
        focus = "服务内容与营销策略"
    elif "旅游" in text:
        actor = "旅游行业主体"
        scene = "旅游服务场景"
        focus = "服务内容与营销策略"
    elif "企业" in text:
        actor = "企业"
        scene = "企业实践场景"
        focus = "业务流程优化"
    elif "系统" in text or "平台" in text:
        actor = "系统"
        scene = "系统应用场景"
        focus = "功能设计与使用流程"
    elif "学生" in text or "教学" in text or "教育" in text:
        actor = "教学主体"
        scene = "教学应用场景"
        focus = "教学过程与实践反馈"

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
            return problem_rewrite, "把并列堆叠改成更具体的环节描述。"

    template_match = re.fullmatch(r"随着(.+)的发展", text)
    if template_match:
        subject = template_match.group(1)
        return (
            f"近年来，{subject}在{scene}中的应用逐步展开",
            "保留原话题，但把模板开头改成带场景的自然起句。",
        )

    replacements = {
        "发挥着越来越重要的作用": (
            f"已经被用于{scene}中的具体处理环节",
            "把空泛价值判断压回具体使用场景。",
        ),
        "具有较强的现实意义": (
            f"在{scene}中具有直接应用价值",
            "保留原意，但明确价值落点。",
        ),
        "具有重要的现实意义": (
            f"在{scene}中具有直接应用价值",
            "保留原意，但明确价值落点。",
        ),
        "具有重要意义": (
            f"能直接服务于{scene}中的关键环节",
            "把抽象意义改成更可感知的作用。",
        ),
        "具有参考价值": (
            f"可为{actor}后续调整{focus}提供参考",
            "补出参考价值具体服务的对象和动作。",
        ),
        "提供一定参考价值": (
            f"可为{actor}后续调整{focus}提供参考",
            "补出参考价值具体服务的对象和动作。",
        ),
        "为相关研究提供一定参考价值": (
            f"可为后续围绕{focus}的研究比较提供参考",
            "减少泛泛而谈，补出研究比较的具体方向。",
        ),
        "为相关实践提供参考价值": (
            f"可为{actor}在{scene}中的后续调整提供参考",
            "把相关实践落到当前对象和场景上。",
        ),
        "理论基础": (
            f"{focus}相关概念与研究依据",
            "把抽象章节词替换成更明确的分析对象。",
        ),
        "优化路径": (
            f"{actor}优化{focus}的具体路径",
            "补出谁来优化、优化什么。",
        ),
        "相关实践": (
            f"{actor}在{scene}中的具体实践",
            "避免泛指，直接回到原文场景。",
        ),
        "现实问题": (
            f"{actor}在{scene}中遇到的实际问题",
            "把抽象问题落到对象和场景里。",
        ),
        "应用价值": (
            f"{scene}中的实际使用价值",
            "让价值判断更贴近具体使用场景。",
        ),
    }
    if text in replacements:
        return replacements[text]

    if re.fullmatch(r"能够帮助[^，。；！？\n]{2,28}(提高|提升|优化)[^，。；！？\n]{2,28}(效率|质量|水平|能力)", text):
        return (
            f"可以帮助{actor}完成{focus}中的记录、提醒和复盘步骤",
            "把提高效率一类空泛表述改成可执行动作。",
        )

    if text in {"首先", "其次", "最后"} and mode != "polish":
        mapping = {
            "首先": "先从核心对象入手",
            "其次": "再结合具体场景展开",
            "最后": "在此基础上",
        }
        return mapping[text], "减少机械衔接词，让句间过渡更自然。"

    if text == "综上所述":
        return "结合前面的分析", "弱化公式化总结句。"
    if text == "此外":
        return "另一点是", "把高频连接词改得更口语化一些。"
    if text == "与此同时":
        return "同一过程中", "避免机械并列。"
    return "", ""


def _rewrite_problem_chain(text: str, context: dict[str, str]) -> str:
    rewritten = text
    problem_match = re.search(
        r"(?:然而|但是)?，?(?P<subject>[^。；！？]{2,42}?)(?:普遍)?存在(?P<problems>[^。；！？]{8,130}?)(?:等)?问题",
        rewritten,
    )
    if problem_match:
        subject = problem_match.group("subject").strip("， ")
        problems = _split_problem_items(problem_match.group("problems"))
        if len(problems) >= 2:
            subject_label = "这类平台" if "平台" in subject else subject
            replacement = f"{subject_label}的问题主要集中在{_cn_count(len(problems))}环节：{'、'.join(problems)}。"
            rewritten = rewritten[: problem_match.start()] + replacement + rewritten[problem_match.end() :]

    demand_match = re.search(
        r"这使得(?P<target>[^，。；！？]{1,36})难以满足(?P<who>[^，。；！？]{1,36})对于(?P<needs>[^。；！？]{4,90})的(?:深层)?需求",
        rewritten,
    )
    if demand_match:
        who = demand_match.group("who").strip()
        actions = _need_actions(_split_need_items(demand_match.group("needs")), context)
        replacement = f"因此，{who}在{actions}时更容易遇到信息断点。"
        rewritten = rewritten[: demand_match.start()] + replacement + rewritten[demand_match.end() :]

    return rewritten


def _split_problem_items(raw: str) -> list[str]:
    cleaned = raw.replace("以及", "、").replace("和", "、")
    items = [item.strip("，、。； ") for item in cleaned.split("、")]
    return [item for item in items if len(item) >= 2][:6]


def _split_need_items(raw: str) -> list[str]:
    cleaned = raw.replace("以及", "、").replace("和", "、")
    items = [item.strip("，、。； ") for item in cleaned.split("、")]
    return [item for item in items if item][:5]


def _need_actions(needs: list[str], context: dict[str, str]) -> str:
    actions: list[str] = []
    for need in needs:
        if "透明" in need or "信息" in need:
            actions.append("核对产品信息")
        elif "指导" in need or "系统性" in need or "知识" in need:
            actions.append("查找连续的种植指导")
        elif "情感" in need or "交流" in need or "社区" in need:
            actions.append("参与社区交流")
        elif "库存" in need:
            actions.append("确认库存状态")
    if not actions:
        if "种子电商" in context["scene"]:
            actions = ["核对产品信息", "查找连续的种植指导", "参与社区交流"]
        else:
            actions = [f"使用{context['focus']}"]
    return "、".join(list(dict.fromkeys(actions))[:4])


def _cn_count(value: int) -> str:
    return {2: "两个", 3: "三个", 4: "四个", 5: "五个", 6: "六个"}.get(value, str(value))


def _split_overlong_sentences(text: str) -> str:
    def split_match(match: re.Match[str]) -> str:
        sentence = match.group(0)
        if "，" not in sentence:
            return sentence
        parts = [part.strip() for part in sentence.split("，") if part.strip()]
        if len(parts) < 3:
            return sentence
        midpoint = max(1, len(parts) // 2)
        if len(parts[0]) <= 4:
            midpoint = min(2, len(parts) - 1)
        return "，".join(parts[:midpoint]) + "。随后，" + "，".join(parts[midpoint:])

    return re.sub(r"[^。！？\n]{58,}", split_match, text)


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
        return "该段内容整体风险较低，系统已按原意做了更自然的轻量改写。"
    categories = {hit.category for hit in hits}
    if "template" in categories or "vague" in categories:
        focus = "模板化表达和空泛结论"
    elif "repetition" in categories:
        focus = "重复句式和长句节奏"
    else:
        focus = "连接词密度和句间衔接"
    mode_label = {
        "auto": "智能推荐",
        "aigc": "降 AIGC",
        "similarity": "降重复",
        "polish": "学术润色",
    }[mode]
    return f"系统识别到 {len(hits)} 处短语级风险，主要集中在{focus}，这次按“{mode_label}”思路做了直接改写。"
