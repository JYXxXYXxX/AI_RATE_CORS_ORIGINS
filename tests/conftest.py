"""共享 pytest fixtures，减少测试代码重复。"""

from __future__ import annotations

import shutil
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app, get_calibrator
from app.services.calibration import CnkiCalibrator


@pytest.fixture
def client() -> TestClient:
    """创建测试客户端。"""
    return TestClient(app)


@pytest.fixture
def temp_test_dir(tmp_path: Path) -> Path:
    """创建临时测试目录，测试结束自动清理。"""
    test_dir = tmp_path / uuid4().hex
    test_dir.mkdir(parents=True, exist_ok=True)
    yield test_dir
    shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture
def isolated_settings(temp_test_dir: Path) -> Settings:
    """创建隔离的测试 Settings，所有数据目录指向临时目录。"""
    return Settings(
        upload_storage_dir=str(temp_test_dir / "uploads"),
        cleaned_storage_dir=str(temp_test_dir / "cleaned"),
        feedback_storage_dir=str(temp_test_dir / "feedback"),
        feedback_learning_store_path=str(temp_test_dir / "feedback_learning.jsonl"),
        feedback_learning_skill_path=str(temp_test_dir / "feedback_skill" / "SKILL.md"),
        model_artifact_dir=str(temp_test_dir / "models"),
        calibration_store_path=str(temp_test_dir / "calibration.jsonl"),
        provider_registry_path=str(temp_test_dir / "provider_registry.json"),
        provider_files_base_path=str(temp_test_dir),
        auto_train_enabled=False,
    )


@pytest.fixture
def isolated_calibrator(isolated_settings: Settings) -> CnkiCalibrator:
    """创建隔离的校准器。"""
    return CnkiCalibrator(isolated_settings)


@pytest.fixture
def override_settings(isolated_settings: Settings):
    """临时覆盖 app 依赖为隔离 settings，测试结束自动恢复。"""
    from app.config import get_settings

    original = app.dependency_overrides.copy()
    app.dependency_overrides[get_settings] = lambda: isolated_settings

    @lru_cache
    def test_calibrator() -> CnkiCalibrator:
        return CnkiCalibrator(isolated_settings)

    app.dependency_overrides[get_calibrator] = test_calibrator
    yield isolated_settings
    app.dependency_overrides = original


SAMPLE_ACADEMIC_TEXT = (
    "本文首先分析人工智能赋能教育评价的理论基础，其次讨论现实问题，最后提出优化路径。"
    "该研究具有重要意义，并能为相关实践提供参考价值。\n\n"
    "访谈记录显示，三位教师在实际课堂中主要使用形成性评价表。"
    "其中两位教师提到学生反馈会影响下一轮教学设计。"
    "这些材料来自 2024 年 10 月至 11 月的校内调研。"
)
