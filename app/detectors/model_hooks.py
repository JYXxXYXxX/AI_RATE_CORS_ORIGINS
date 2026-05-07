from __future__ import annotations

import logging
from pathlib import Path

from app.detectors.base import Detector, DetectorResult
from app.detectors.heuristics import cn_char_count

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# 模型路径配置
# 把微调好的 HuggingFace 模型目录放在这里，或者通过环境变量覆盖。
# 目录下应包含 config.json, model.safetensors/pytorch_model.bin,
# tokenizer.json, tokenizer_config.json 等标准文件。
# ------------------------------------------------------------------
_DEFAULT_MODEL_DIR = "data/models/aigc-detector"

_model_singleton: _TransformerModel | None = None
_model_load_attempted = False


class _TransformerModel:
    """封装 HuggingFace 模型的加载和推理，进程内单例。"""

    def __init__(self, model_dir: str) -> None:
        import torch
        from transformers import AutoTokenizer, AutoModelForSequenceClassification

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir)
        self.model.to(self.device)
        self.model.eval()
        logger.info("Transformer AIGC 检测模型已加载: %s (device=%s)", model_dir, self.device)

    def predict(self, text: str) -> float:
        """返回 AI 生成概率 [0, 1]。"""
        import torch

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        )
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        with torch.no_grad():
            logits = self.model(**inputs).logits
        probabilities = torch.softmax(logits, dim=-1)
        # 假设 label 1 = AI-generated
        return float(probabilities[0][1].cpu())


def _get_model() -> _TransformerModel | None:
    """延迟加载模型，失败时返回 None 而不是崩溃。"""
    global _model_singleton, _model_load_attempted
    if _model_load_attempted:
        return _model_singleton
    _model_load_attempted = True

    import os
    model_dir = os.environ.get("AI_RATE_TRANSFORMER_MODEL_DIR", _DEFAULT_MODEL_DIR)
    if not Path(model_dir).exists():
        logger.warning("模型目录不存在: %s，LocalTransformerDetector 将使用占位模式", model_dir)
        return None
    try:
        _model_singleton = _TransformerModel(model_dir)
    except Exception as exc:  # noqa: BLE001
        logger.error("加载 Transformer 模型失败: %s，将使用占位模式", exc)
        _model_singleton = None
    return _model_singleton


class LocalTransformerDetector(Detector):
    """段落级 AI 生成文本分类器。

    当 data/models/aigc-detector 下存在有效的 HuggingFace 模型时，
    使用真实 Transformer 推理；否则自动降级为轻量占位逻辑。
    """

    name = "local_transformer_classifier"
    weight = 0.45  # 真实模型应承担更高权重

    def score(self, segment: str, all_segments: list[str]) -> DetectorResult:
        model = _get_model()
        if model is not None:
            return self._score_with_model(model, segment)
        return self._score_fallback(segment)

    def _score_with_model(self, model: _TransformerModel, segment: str) -> DetectorResult:
        char_count = cn_char_count(segment)
        if char_count < 40:
            return DetectorResult(
                name=self.name,
                score=0.35,
                weight=self.weight * 0.4,  # 短文本降低权重
                reasons=["片段过短，Transformer 分类器置信度较低"],
            )

        probability = model.predict(segment)
        reasons: list[str] = []
        if probability >= 0.80:
            reasons.append(f"Transformer 分类器判定 AI 生成概率较高 ({probability:.0%})")
        elif probability >= 0.55:
            reasons.append(f"Transformer 分类器判定存在 AI 生成嫌疑 ({probability:.0%})")
        elif probability <= 0.25:
            reasons.append("Transformer 分类器判定该段更接近人类写作风格")

        return DetectorResult(
            name=self.name,
            score=round(probability, 4),
            weight=self.weight,
            reasons=reasons,
        )

    def _score_fallback(self, segment: str) -> DetectorResult:
        """无模型时的占位逻辑，保持服务可用。"""
        char_count = cn_char_count(segment)
        if char_count < 80:
            return DetectorResult(
                name=self.name,
                score=0.36,
                weight=0.16,  # 占位模式用低权重
                reasons=["片段较短，自托管分类器信号采用保守占位"],
            )

        generic_markers = (
            "本文", "研究表明", "具有重要意义", "优化路径",
            "相关研究", "理论基础", "应用策略", "综上所述",
        )
        hits = sum(1 for marker in generic_markers if marker in segment)
        fallback_score = max(0.0, min(1.0, 0.32 + hits * 0.08))
        return DetectorResult(
            name=self.name,
            score=fallback_score,
            weight=0.16,  # 占位模式用低权重
            reasons=["Transformer 模型未加载，使用轻量占位信号"],
        )


ExternalModelDetector = LocalTransformerDetector
