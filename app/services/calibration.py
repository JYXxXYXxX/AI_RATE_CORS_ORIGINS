import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

from app.config import Settings
from app.schemas import CnkiRiskRange


@dataclass(frozen=True)
class CalibrationSample:
    ai_like_score: float
    cnki_ai_rate: float
    subject: str | None = None
    degree_level: str | None = None


class CnkiCalibrator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.path = Path(settings.calibration_store_path)
        self.samples = self._load_samples()
        self.version = f"cnki-calibrator-0.2.{len(self.samples)}"

    def predict_range(self, ai_like_score: float, dispersion: float, subject: str | None = None) -> CnkiRiskRange:
        center = self._predict_center(ai_like_score, subject)
        base_margin = 0.10 if len(self.samples) < self.settings.calibration_min_samples else 0.07
        dispersion_margin = min(0.09, dispersion * 0.42)
        margin = max(0.06, min(0.18, base_margin + dispersion_margin))
        lower = max(0.0, center - margin)
        upper = min(1.0, center + margin)
        return CnkiRiskRange(
            lower=round(lower, 4),
            upper=round(upper, 4),
            lower_percent=round(lower * 100, 2),
            upper_percent=round(upper * 100, 2),
            label=self._label(center),
        )

    def confidence(self, segment_count: int, dispersion: float) -> float:
        sample_factor = min(0.22, len(self.samples) / max(self.settings.calibration_min_samples, 1) * 0.22)
        segment_factor = min(0.18, segment_count / 24 * 0.18)
        dispersion_penalty = min(0.20, dispersion * 0.38)
        confidence = 0.48 + sample_factor + segment_factor - dispersion_penalty
        return round(max(0.35, min(0.88, confidence)), 4)

    def append_sample(self, sample: CalibrationSample) -> int:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(sample.__dict__, ensure_ascii=False) + "\n")
        self.samples.append(sample)
        self.version = f"cnki-calibrator-0.2.{len(self.samples)}"
        return len(self.samples)

    def _predict_center(self, ai_like_score: float, subject: str | None) -> float:
        if not self.samples:
            return _fallback_mapping(ai_like_score)

        relevant = [sample for sample in self.samples if subject and sample.subject == subject]
        samples = relevant if len(relevant) >= 5 else self.samples
        x_mean = mean(sample.ai_like_score for sample in samples)
        y_mean = mean(sample.cnki_ai_rate for sample in samples)
        numerator = sum((sample.ai_like_score - x_mean) * (sample.cnki_ai_rate - y_mean) for sample in samples)
        denominator = sum((sample.ai_like_score - x_mean) ** 2 for sample in samples)
        if denominator <= 1e-9:
            return max(0.0, min(1.0, y_mean))

        slope = max(0.35, min(1.45, numerator / denominator))
        intercept = y_mean - slope * x_mean
        blended = 0.72 * (intercept + slope * ai_like_score) + 0.28 * _fallback_mapping(ai_like_score)
        return max(0.0, min(1.0, blended))

    def _load_samples(self) -> list[CalibrationSample]:
        if not self.path.exists():
            return []

        samples = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    payload = json.loads(line)
                    samples.append(
                        CalibrationSample(
                            ai_like_score=float(payload["ai_like_score"]),
                            cnki_ai_rate=float(payload["cnki_ai_rate"]),
                            subject=payload.get("subject"),
                            degree_level=payload.get("degree_level"),
                        )
                    )
                except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                    continue
        return samples

    @staticmethod
    def _label(score: float) -> str:
        if score >= 0.70:
            return "高度疑似"
        if score >= 0.42:
            return "中高风险"
        if score >= 0.22:
            return "可疑"
        return "低风险"


def _fallback_mapping(score: float) -> float:
    centered = (score - 0.50) * 0.88 + 0.50
    return max(0.0, min(1.0, centered))
