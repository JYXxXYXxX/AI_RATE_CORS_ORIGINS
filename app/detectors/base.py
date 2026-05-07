from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DetectorResult:
    name: str
    score: float
    weight: float
    reasons: list[str] = field(default_factory=list)


class Detector(ABC):
    name: str
    weight: float

    @abstractmethod
    def score(self, segment: str, all_segments: list[str]) -> DetectorResult:
        """Return an AI-like score in [0, 1]."""
