from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.services.calibration import CnkiCalibrator


@lru_cache
def get_calibrator_runtime() -> CnkiCalibrator:
    return CnkiCalibrator(get_settings())
