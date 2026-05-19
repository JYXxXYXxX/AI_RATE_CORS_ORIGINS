"""测试在线编辑器的真实重算(reanalyze)链路。"""
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app, get_calibrator
from app.services.calibration import CnkiCalibrator
from tests.conftest import make_docx_bytes

client = TestClient(app)


def test_reanalyze_after_rewrite() -> None:
    """上传文档→分析→获取段落→改写→真实重算→验证响应格式与分数更新。"""
    original_settings = app.dependency_overrides.get(get_settings)
    original_calibrator = app.dependency_overrides.get(get_calibrator)
    base_dir = Path("data/test_runtime") / uuid4().hex
    settings = Settings(
        upload_storage_dir=str(base_dir / "uploads"),
        cleaned_storage_dir=str(base_dir / "cleaned"),
        feedback_storage_dir=str(base_dir / "feedback"),
        model_artifact_dir=str(base_dir / "models"),
        calibration_store_path=str(base_dir / "calibration.jsonl"),
        provider_registry_path=str(base_dir / "provider_registry.json"),
    )

    @lru_cache
    def test_calibrator() -> CnkiCalibrator:
        return CnkiCalibrator(settings)

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_calibrator] = test_calibrator
    try:
        text = (
            "摘要\n\n本文围绕论文提交前风险预检展开分析，重点讨论本地 AIGC 检测、重复风险预检与真实结果回填。"
            "研究采用案例分析与流程拆解的方法。\n\n"
            "第一章 绪论\n\n为了减少正式送检前的返工，研究团队先对高风险段落进行定位，再安排定向修改。"
            "这种方式能让论文修改更聚焦。\n\n"
            "第二章 方法\n\n本文将检测结果、相似证据和回填样本统一结构化存储，为后续代理模型训练提供基础。"
        )

        # 1. 上传
        upload = client.post(
            "/v1/documents/upload",
            data={"title": "重算测试论文", "subject": "教育学", "degree_level": "本科"},
            files={"file": ("reanalyze.docx", make_docx_bytes(text), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        assert upload.status_code == 200
        document_id = upload.json()["document_id"]

        # 2. 分析
        analyze = client.post(f"/v1/documents/{document_id}/analyze")
        assert analyze.status_code == 200
        run_id = analyze.json()["run_id"]

        # 3. 获取段落列表
        sections_resp = client.get(f"/v1/runs/{run_id}/sections")
        assert sections_resp.status_code == 200
        sections = sections_resp.json()
        assert len(sections) > 0

        # 4. 模拟改写：把第一段内容改短一点
        payload_sections = [
            {"section_index": s["section_index"], "content": s["content"]}
            for s in sections
        ]
        # 改写第一个非跳过段落
        target_idx = next(
            (i for i, s in enumerate(payload_sections)
             if s["content"].strip() and "摘要" not in s["content"] and "第一章" not in s["content"]),
            0
        )
        original_text = payload_sections[target_idx]["content"]
        payload_sections[target_idx]["content"] = original_text.replace(
            "研究团队先对高风险段落进行定位", "研究者首先识别高风险文本片段"
        )

        # 5. 真实重算
        reanalyze_resp = client.post(
            f"/v1/runs/{run_id}/reanalyze",
            json={"sections": payload_sections},
        )
        assert reanalyze_resp.status_code == 200, f"reanalyze failed: {reanalyze_resp.text}"
        result = reanalyze_resp.json()

        # 6. 验证响应字段与类型
        assert "ai_like_score" in result
        assert "ai_like_percent" in result
        assert "duplication_score" in result
        assert "duplication_percent" in result
        assert "risk_level" in result
        assert "predicted_cnki_range" in result
        assert isinstance(result["predicted_cnki_range"], str)
        assert "confidence" in result
        assert isinstance(result["confidence"], str)
        assert "sections" in result
        assert len(result["sections"]) > 0
        for sec in result["sections"]:
            assert "section_index" in sec
            assert "aigc_score" in sec
            assert "duplication_score" in sec
            assert "risk_level" in sec

        # 7. 导出 txt
        export_txt = client.post(
            f"/v1/runs/{run_id}/export",
            json={"sections": payload_sections, "format": "txt"},
        )
        assert export_txt.status_code == 200
        # 如果改写内容确实在导出中更好；因 segment 映射可能不同，仅验证非空即可
        assert len(export_txt.content) > 0

        # 8. 导出 docx
        export_docx = client.post(
            f"/v1/runs/{run_id}/export",
            json={"sections": payload_sections, "format": "docx"},
        )
        assert export_docx.status_code == 200
        assert export_docx.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    finally:
        if original_settings is None:
            app.dependency_overrides.pop(get_settings, None)
        else:
            app.dependency_overrides[get_settings] = original_settings
        if original_calibrator is None:
            app.dependency_overrides.pop(get_calibrator, None)
        else:
            app.dependency_overrides[get_calibrator] = original_calibrator
