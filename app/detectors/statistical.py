import logging
import math
from collections import Counter

from app.detectors.base import Detector, DetectorResult
from app.detectors.heuristics import cn_char_count, tokens

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 语言模型困惑度计算（进程单例）
# ---------------------------------------------------------------------------
_ppl_model: "_PerplexityModel | None" = None
_ppl_load_attempted = False


class _PerplexityModel:
    """用 GPT-2 中文模型计算 token 级困惑度。"""

    def __init__(self) -> None:
        import os
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        model_name = os.environ.get(
            "AI_RATE_PPL_MODEL",
            "uer/gpt2-chinese-cluecorpussmall",
        )
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()
        logger.info("PPL 语言模型已加载: %s (device=%s)", model_name, self.device)

    def compute_perplexity(self, text: str, max_length: int = 512) -> float:
        """返回文本的困惑度（越低越可能是 AI 生成）。"""
        import torch

        inputs = self.tokenizer(
            text, return_tensors="pt", truncation=True, max_length=max_length
        )
        input_ids = inputs["input_ids"].to(self.device)
        if input_ids.size(1) < 2:
            return 100.0

        with torch.no_grad():
            outputs = self.model(input_ids, labels=input_ids)
            loss = outputs.loss
        return float(torch.exp(loss).cpu())


def _get_ppl_model() -> "_PerplexityModel | None":
    global _ppl_model, _ppl_load_attempted
    if _ppl_load_attempted:
        return _ppl_model
    _ppl_load_attempted = True
    import os

    if os.environ.get("AI_RATE_ENABLE_PPL", "true").lower() in (
        "false",
        "0",
        "no",
        "off",
    ):
        logger.info("PPL 检测已禁用 (AI_RATE_ENABLE_PPL=false)，使用轻量熵近似")
        _ppl_model = None
        return _ppl_model
    try:
        _ppl_model = _PerplexityModel()
    except Exception as exc:  # noqa: BLE001
        logger.warning("加载 PPL 语言模型失败: %s，将使用 unigram 熵近似", exc)
        _ppl_model = None
    return _ppl_model


class PerplexityDetector(Detector):
    """困惑度检测器。

    有语言模型时用真实 token 级 PPL；否则降级为 unigram 熵。
    低困惑度 = 文本太顺滑 = 更可能是 AI 生成。
    """

    name = "perplexity"
    weight = 0.14

    def score(self, segment: str, all_segments: list[str]) -> DetectorResult:
        model = _get_ppl_model()
        if model is not None:
            return self._score_with_model(model, segment)
        return self._score_fallback(segment)

    def _score_with_model(
        self, model: _PerplexityModel, segment: str
    ) -> DetectorResult:
        char_count = cn_char_count(segment)
        if char_count < 40:
            return DetectorResult(
                self.name, 0.36, self.weight * 0.5, ["片段过短，困惑度判断置信度较低"]
            )

        ppl = model.compute_perplexity(segment)

        # PPL 低 → AI 嫌疑高。中文学术文本人类 PPL 大约 40-200，
        # AI 生成文本 PPL 通常 15-60。
        # 用 sigmoid 映射: PPL=30 → 0.75, PPL=80 → 0.35, PPL=150 → 0.15
        score = max(0.0, min(1.0, 1.0 / (1.0 + math.exp((ppl - 55) / 25))))
        reasons: list[str] = []
        if score >= 0.65:
            reasons.append(
                f"文本困惑度偏低 (PPL={ppl:.0f})，语言流畅度接近模型生成水平"
            )
        elif score <= 0.30:
            reasons.append(f"文本困惑度较高 (PPL={ppl:.0f})，用词组织更接近人类写作")
        return DetectorResult(self.name, round(score, 4), self.weight, reasons)

    def _score_fallback(self, segment: str) -> DetectorResult:
        """无模型时的降级: unigram 熵。"""
        ts = tokens(segment)
        if len(ts) < 45:
            return DetectorResult(
                self.name, 0.36, self.weight, ["文本片段较短，困惑度特征置信度较低"]
            )

        counter = Counter(ts)
        total = len(ts)
        entropy = -sum(
            (count / total) * math.log(count / total + 1e-12)
            for count in counter.values()
        )
        normalized_entropy = entropy / math.log(max(len(counter), 2))
        score = max(0.0, min(1.0, (0.86 - normalized_entropy) / 0.42))
        reasons = []
        if score > 0.55:
            reasons.append("词项分布较集中，近似困惑度信号偏低（语言模型未加载）")
        return DetectorResult(self.name, score, self.weight, reasons)


class TokenRankStyleDetector(Detector):
    name = "token_rank_style"
    weight = 0.10

    def score(self, segment: str, all_segments: list[str]) -> DetectorResult:
        ts = tokens(segment)
        if len(ts) < 45:
            return DetectorResult(self.name, 0.34, self.weight, [])

        common_tokens = {
            "的",
            "了",
            "和",
            "与",
            "在",
            "对",
            "中",
            "为",
            "是",
            "以",
            "及",
            "相关",
            "研究",
            "分析",
            "可以",
            "通过",
            "进行",
            "实现",
            "提升",
            "问题",
            "发展",
        }
        high_rank_ratio = sum(1 for token in ts if token in common_tokens) / len(ts)
        score = max(0.0, min(1.0, (high_rank_ratio - 0.16) / 0.24))
        reasons = []
        if score > 0.58:
            reasons.append("高频通用词占比偏高，token-rank 风格信号偏强")
        return DetectorResult(self.name, score, self.weight, reasons)


def build_statistical_detectors() -> list[Detector]:
    return [
        PerplexityDetector(),
        TokenRankStyleDetector(),
    ]
