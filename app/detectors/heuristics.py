import math
import re
from collections import Counter

from app.detectors.base import Detector, DetectorResult


CN_RE = re.compile(r"[\u4e00-\u9fff]")
TOKEN_RE = re.compile(r"[\u4e00-\u9fff]|[A-Za-z0-9_]+")
SENTENCE_RE = re.compile(r"[^。！？!?；;]+[。！？!?；;]?")

ACADEMIC_TEMPLATES = (
    # 经典模板句式
    "随着",
    "不断发展",
    "日益",
    "具有重要意义",
    "本文首先",
    "其次",
    "最后",
    "综上所述",
    "研究表明",
    "相关研究",
    "理论基础",
    "应用路径",
    "优化策略",
    "存在问题",
    "提出建议",
    "进一步推动",
    "促进发展",
    "具有一定的参考价值",
    "在此基础上",
    "从而实现",
    "有效提升",
    "显著提高",
    "综合分析",
    # ChatGPT/通义千问 典型中文输出模式
    "值得注意的是",
    "需要指出的是",
    "不可忽视",
    "不容忽视",
    "总而言之",
    "概括而言",
    "简言之",
    "换言之",
    "这一现象",
    "这一趋势",
    "这一问题",
    "这一领域",
    "为此",
    "鉴于此",
    "有鉴于此",
    "由此可见",
    "不仅如此",
    "更为重要的是",
    "尤为关键的是",
    "提供了新的思路",
    "提供了有益参考",
    "具有重要的理论价值和实践意义",
    "为…提供了",
    "为…奠定了基础",
    "在很大程度上",
    "从根本上",
    "从本质上看",
    "呈现出",
    "体现在以下几个方面",
    "对…产生了深远影响",
    "发挥着重要作用",
)

CONNECTORS = (
    "首先",
    "其次",
    "再次",
    "最后",
    "同时",
    "此外",
    "因此",
    "然而",
    "总之",
    "综上",
    "一方面",
    "另一方面",
    "基于此",
    "与此同时",
    "进一步",
    "具体而言",
    # 扩充
    "不仅…而且",
    "不仅如此",
    "除此之外",
    "更为重要的是",
    "归纳起来",
    "总体来看",
    "从整体上看",
    "由此可知",
    "据此",
    "相应地",
    "反之",
    "尽管如此",
    "事实上",
)

VAGUE_TERMS = (
    "相关",
    "一定",
    "有效",
    "显著",
    "合理",
    "科学",
    "完善",
    "优化",
    "提升",
    "推动",
    "促进",
    "保障",
    "机制",
    "体系",
    "路径",
    "策略",
    "问题",
    "价值",
    # 扩充：AI 生成高频模糊词
    "探索",
    "构建",
    "赋能",
    "助力",
    "深化",
    "拓展",
    "创新",
    "系统性",
    "全面性",
    "针对性",
    "可行性",
    "前瞻性",
    "新模式",
    "新路径",
    "新格局",
    "新业态",
)

REPORT_LEARNED_AI_TERMS = (
    "持续发展",
    "持续迭代",
    "趋于多元",
    "赋能",
    "支撑",
    "体系",
    "机制",
    "路径",
    "落地",
    "拓展",
    "坚实基础",
    "有效弥补",
    "场景适配",
    "优化完善",
    "提供参考",
    "参考价值",
    "重要意义",
    "应用价值",
)

DETAIL_EVIDENCE_RE = re.compile(
    r"(?:\d+(?:\.\d+)?\s*(?:%|ms|秒|s|个|人|次|年|月)|"
    r"SpringBoot|Springboot|Vue|MySQL|JWT|MyBatis|Postman|Docker|"
    r"API|RAG|ECharts|Element Plus|\[\d+\])",
    re.IGNORECASE,
)


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text)


def sentences(text: str) -> list[str]:
    items = [item.strip() for item in SENTENCE_RE.findall(text)]
    return [item for item in items if item]


def cn_char_count(text: str) -> int:
    return len(CN_RE.findall(text))


class LexicalDiversityDetector(Detector):
    name = "lexical_diversity"
    weight = 0.15

    def score(self, segment: str, all_segments: list[str]) -> DetectorResult:
        ts = tokens(segment)
        if len(ts) < 40:
            return DetectorResult(
                self.name, 0.35, self.weight, ["文本片段较短，词汇多样性判断置信度较低"]
            )

        unique_ratio = len(set(ts)) / len(ts)
        repetition_ratio = 1 - unique_ratio
        score = clamp((repetition_ratio - 0.30) / 0.35)
        reasons = []
        if score > 0.58:
            reasons.append("词汇重复度偏高，表达变化不足")
        elif score < 0.25:
            reasons.append("词汇多样性较高")
        return DetectorResult(self.name, score, self.weight, reasons)


class SentenceUniformityDetector(Detector):
    name = "sentence_uniformity"
    weight = 0.14

    def score(self, segment: str, all_segments: list[str]) -> DetectorResult:
        ss = sentences(segment)
        if len(ss) < 3:
            return DetectorResult(
                self.name, 0.40, self.weight, ["句子数量较少，句式均匀度判断置信度较低"]
            )

        lengths = [max(1, cn_char_count(s)) for s in ss]
        mean = sum(lengths) / len(lengths)
        variance = sum((length - mean) ** 2 for length in lengths) / len(lengths)
        cv = math.sqrt(variance) / max(mean, 1)
        score = clamp((0.72 - cv) / 0.72)
        reasons = []
        if score > 0.65:
            reasons.append("句长波动偏低，段落节奏较均匀")
        return DetectorResult(self.name, score, self.weight, reasons)


class TemplatePhraseDetector(Detector):
    name = "academic_template_phrases"
    weight = 0.12

    def score(self, segment: str, all_segments: list[str]) -> DetectorResult:
        char_count = max(cn_char_count(segment), 1)
        hits = [phrase for phrase in ACADEMIC_TEMPLATES if phrase in segment]
        density = len(hits) / (char_count / 220)
        score = clamp(density / 4.0)
        reasons = []
        if hits:
            preview = "、".join(hits[:5])
            reasons.append(f"学术模板化表达较集中：{preview}")
        return DetectorResult(self.name, score, self.weight, reasons)


class ConnectorDensityDetector(Detector):
    name = "connector_density"
    weight = 0.10

    def score(self, segment: str, all_segments: list[str]) -> DetectorResult:
        char_count = max(cn_char_count(segment), 1)
        hits = [word for word in CONNECTORS if word in segment]
        density = len(hits) / (char_count / 240)
        score = clamp(density / 4.5)
        reasons = []
        if score > 0.55:
            reasons.append("连接词密度偏高，论述组织方式较模板化")
        return DetectorResult(self.name, score, self.weight, reasons)


class VagueAbstractionDetector(Detector):
    name = "vague_abstraction"
    weight = 0.10

    def score(self, segment: str, all_segments: list[str]) -> DetectorResult:
        char_count = max(cn_char_count(segment), 1)
        count = sum(segment.count(term) for term in VAGUE_TERMS)
        density = count / (char_count / 180)
        score = clamp((density - 1.2) / 5.0)
        reasons = []
        if score > 0.52:
            reasons.append("抽象概括词密度偏高，可能缺少具体研究细节")
        return DetectorResult(self.name, score, self.weight, reasons)


class ReportLearnedStyleDetector(Detector):
    name = "report_learned_style"
    weight = 0.13

    def score(self, segment: str, all_segments: list[str]) -> DetectorResult:
        char_count = max(cn_char_count(segment), 1)
        hits = [term for term in REPORT_LEARNED_AI_TERMS if term in segment]
        density = len(hits) / (char_count / 260)
        score = clamp((density - 0.8) / 4.2)

        has_detail = bool(DETAIL_EVIDENCE_RE.search(segment))
        if hits and not has_detail:
            score = clamp(score + 0.12)

        reasons = []
        if score > 0.45:
            preview = "、".join(hits[:5])
            if has_detail:
                reasons.append(
                    f"存在报告对照中常见的AI书面化表达：{preview}，建议保留版本号/数据/引用并改成更自然的系统说明句"
                )
            else:
                reasons.append(
                    f"存在报告对照中常见的AI书面化表达：{preview}，且缺少版本号、测试数据或引用等可核验细节"
                )
        return DetectorResult(self.name, score, self.weight, reasons)


class CrossSegmentRepetitionDetector(Detector):
    name = "cross_segment_repetition"
    weight = 0.10

    def score(self, segment: str, all_segments: list[str]) -> DetectorResult:
        ts = tokens(segment)
        if len(ts) < 30 or len(all_segments) < 2:
            return DetectorResult(self.name, 0.25, self.weight, [])

        current = Counter(_ngrams(ts, 3))
        if not current:
            return DetectorResult(self.name, 0.20, self.weight, [])

        max_similarity = 0.0
        for other in all_segments:
            if other == segment:
                continue
            ots = tokens(other)
            other_counter = Counter(_ngrams(ots, 3))
            if not other_counter:
                continue
            overlap = sum((current & other_counter).values())
            union = sum((current | other_counter).values())
            max_similarity = max(max_similarity, overlap / max(union, 1))

        score = clamp((max_similarity - 0.12) / 0.35)
        reasons = []
        if score > 0.55:
            reasons.append("与其他段落存在较高表达重复，可能有泛化复述痕迹")
        return DetectorResult(self.name, score, self.weight, reasons)


def _ngrams(items: list[str], n: int) -> list[tuple[str, ...]]:
    if len(items) < n:
        return []
    return [tuple(items[index : index + n]) for index in range(len(items) - n + 1)]


def build_default_detectors() -> list[Detector]:
    return [
        LexicalDiversityDetector(),
        SentenceUniformityDetector(),
        TemplatePhraseDetector(),
        ConnectorDensityDetector(),
        VagueAbstractionDetector(),
        ReportLearnedStyleDetector(),
        CrossSegmentRepetitionDetector(),
    ]
