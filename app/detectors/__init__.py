from app.detectors.base import Detector, DetectorResult
from app.detectors.heuristics import build_default_detectors
from app.detectors.model_hooks import LocalTransformerDetector
from app.detectors.statistical import build_statistical_detectors


def build_production_detectors() -> list[Detector]:
    return [
        *build_default_detectors(),
        LocalTransformerDetector(),
        *build_statistical_detectors(),
    ]


__all__ = ["Detector", "DetectorResult", "build_default_detectors", "build_production_detectors"]
