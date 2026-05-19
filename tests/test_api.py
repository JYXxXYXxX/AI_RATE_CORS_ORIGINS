from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app, get_calibrator, get_job_store
from app.services.calibration import CnkiCalibrator
from tests.conftest import make_docx_bytes


client = TestClient(app)


def test_job_lifecycle_for_text_file() -> None:
    response = client.post(
        "/v1/jobs",
        data={"title": "demo", "subject": "教育学", "degree_level": "本科"},
        files={
            "file": (
                "paper.txt",
                "本文首先分析人工智能赋能教育评价的理论基础，其次探讨现实问题，最后提出优化路径。"
                "该研究具有重要意义，并能够为相关实践提供参考价值。\n\n"
                "访谈记录显示，三位教师在实际课堂中主要使用形成性评价表，其中两位教师提到学生反馈会影响下一轮教学设计。",
                "text/plain",
            )
        },
    )

    assert response.status_code == 200
    job_id = response.json()["job_id"]

    status_response = client.get(f"/v1/jobs/{job_id}")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "completed"

    report_response = client.get(f"/v1/jobs/{job_id}/report")
    assert report_response.status_code == 200
    report = report_response.json()
    assert report["ai_like_score"] >= 0
    assert (
        report["predicted_cnki_range"]["upper"]
        >= report["predicted_cnki_range"]["lower"]
    )

    job = get_job_store().get(job_id)
    assert job is not None
    assert not hasattr(job, "content")
    assert not hasattr(job, "text")


def test_job_rejects_unsupported_file() -> None:
    response = client.post(
        "/v1/jobs",
        files={"file": ("paper.exe", b"abc", "application/octet-stream")},
    )

    assert response.status_code == 200
    job_id = response.json()["job_id"]
    status = client.get(f"/v1/jobs/{job_id}").json()
    assert status["status"] == "failed"
    assert "支持" in status["error"]


def test_calibration_sample_accepts_job_report() -> None:
    original_override = app.dependency_overrides.get(get_calibrator)
    settings_path = Path("/tmp/ai_rate_detector_test_calibration.jsonl")
    settings_path.unlink(missing_ok=True)
    settings = Settings(calibration_store_path=str(settings_path))

    @lru_cache
    def test_calibrator() -> CnkiCalibrator:
        return CnkiCalibrator(settings)

    app.dependency_overrides[get_calibrator] = test_calibrator
    try:
        response = client.post(
            "/v1/jobs",
            files={
                "file": (
                    "paper.txt",
                    "本文首先分析相关理论基础，其次探讨应用路径，最后提出优化建议。"
                    "研究具有重要意义，并能够为相关实践提供参考价值。",
                    "text/plain",
                )
            },
        )
        job_id = response.json()["job_id"]

        calibration = client.post(
            "/v1/calibration-samples",
            json={"job_id": job_id, "cnki_ai_rate_percent": 34.5},
        )

        assert calibration.status_code == 200
        assert calibration.json()["accepted"] is True
        assert calibration.json()["sample_count"] >= 1
    finally:
        if original_override is None:
            app.dependency_overrides.pop(get_calibrator, None)
        else:
            app.dependency_overrides[get_calibrator] = original_override
        settings_path.unlink(missing_ok=True)


def test_manual_provider_import_and_proxy_training() -> None:
    import os

    original_settings_override = app.dependency_overrides.get(get_settings)
    original_calibrator_override = app.dependency_overrides.get(get_calibrator)
    original_admin_token = os.environ.get("AI_RATE_ADMIN_TOKEN")
    os.environ["AI_RATE_ADMIN_TOKEN"] = "test-admin-token"
    base_dir = Path("data/test_runtime") / uuid4().hex
    provider_file = base_dir / "provider_mock.json"
    provider_file.parent.mkdir(parents=True, exist_ok=True)
    provider_file.write_text(
        '{"result":{"duplication_percent":17.8,"aigc_percent":23.6,"confidence":0.84},"version":"mock-provider-v1"}',
        encoding="utf-8",
    )
    settings = Settings(
        upload_storage_dir=str(base_dir / "uploads"),
        cleaned_storage_dir=str(base_dir / "cleaned"),
        feedback_storage_dir=str(base_dir / "feedback"),
        model_artifact_dir=str(base_dir / "models"),
        calibration_store_path=str(base_dir / "calibration.jsonl"),
        provider_registry_path=str(base_dir / "provider_registry.json"),
        provider_files_base_path=str(base_dir),
        provider_configs_json=(
            '{"wanfang":{"mode":"file","path":"'
            + str(provider_file).replace("\\", "\\\\")
            + '","field_map":{"duplication_percent":"result.duplication_percent","aigc_percent":"result.aigc_percent","confidence":"result.confidence","version":"version"}}}'
        ),
        auto_train_enabled=True,
        auto_train_every_feedbacks=1,
        proxy_training_min_samples=1,
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

        upload = client.post(
            "/v1/documents/upload",
            data={"title": "训练样本论文", "subject": "教育学", "degree_level": "本科"},
            files={"file": ("train.docx", make_docx_bytes(text), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        assert upload.status_code == 200
        document_id = upload.json()["document_id"]

        analyze = client.post(f"/v1/documents/{document_id}/analyze")
        assert analyze.status_code == 200
        run_id = analyze.json()["run_id"]

        provider_import = client.post(
            "/v1/provider-results/manual",
            json={
                "document_id": document_id,
                "run_id": run_id,
                "provider": "manual",
                "duplication_percent": 19.6,
                "aigc_percent": 27.4,
                "confidence": 0.81,
                "version": "manual-check-1",
                "notes": "manual import for training",
                "raw_payload": {"source": "operator"},
            },
        )
        assert provider_import.status_code == 200
        assert provider_import.json()["accepted"] is True

        fetched = client.post(
            "/v1/provider-results/fetch",
            json={
                "document_id": document_id,
                "run_id": run_id,
                "provider": "wanfang",
                "extra_payload": {"trace_id": "case-1"},
            },
        )
        assert fetched.status_code == 200
        assert fetched.json()["accepted"] is True

        provider_catalog = client.get("/v1/providers")
        assert provider_catalog.status_code == 200
        providers = provider_catalog.json()["providers"]
        assert any(
            item["provider"] == "wanfang" and item["configured"] is True
            for item in providers
        )

        feedback = client.post(
            "/v1/cnki-feedback",
            data={
                "document_id": document_id,
                "predicted_run_id": run_id,
                "cnki_dup_percent": "21.3",
                "cnki_aigc_percent": "25.8",
                "report_date": "2026-04-28",
                "notes": "training sample",
            },
        )
        assert feedback.status_code == 200
        assert feedback.json()["calibration_updated"] is True
        assert feedback.json()["auto_train_triggered"] is True
        assert len(feedback.json()["auto_train_versions"]) == 2

        report = client.get(f"/v1/runs/{run_id}/report")
        assert report.status_code == 200
        report_payload = report.json()
        assert report_payload["workflow_overview"]["provider_result_count"] >= 2
        assert report_payload["workflow_overview"]["feedback_count"] >= 1
        assert len(report_payload["provider_results"]) >= 2
        assert len(report_payload["feedback_timeline"]) >= 1
        assert report_payload["calibration_insight"]["latest_cnki_dup_percent"] == 21.3

        model_status = client.get("/v1/models/status")
        assert model_status.status_code == 200
        status_payload = model_status.json()
        assert status_payload["feedback_count"] >= 1
        assert len(status_payload["active_models"]) >= 2

        markdown = client.get(f"/v1/runs/{run_id}/report/markdown")
        assert markdown.status_code == 200
        assert markdown.headers["content-type"].startswith("text/markdown")
        assert "训练样本论文" in markdown.text

        trained = client.post(
            "/v1/models/train-proxy",
            json={"model_type": "both", "min_samples": 1, "activate": True},
            headers={"X-Admin-Token": "test-admin-token"},
        )
        assert trained.status_code == 200
        payload = trained.json()
        assert len(payload["trained_models"]) == 2
        for item in payload["trained_models"]:
            assert Path(item["artifact_path"]).exists()
            assert item["train_count"] >= 1
    finally:
        if original_admin_token is None:
            os.environ.pop("AI_RATE_ADMIN_TOKEN", None)
        else:
            os.environ["AI_RATE_ADMIN_TOKEN"] = original_admin_token
        if original_settings_override is None:
            app.dependency_overrides.pop(get_settings, None)
        else:
            app.dependency_overrides[get_settings] = original_settings_override
        if original_calibrator_override is None:
            app.dependency_overrides.pop(get_calibrator, None)
        else:
            app.dependency_overrides[get_calibrator] = original_calibrator_override


def test_provider_registry_update_and_reset() -> None:
    import os

    original_settings_override = app.dependency_overrides.get(get_settings)
    original_admin_token = os.environ.get("AI_RATE_ADMIN_TOKEN")
    os.environ["AI_RATE_ADMIN_TOKEN"] = "test-admin-token"
    base_dir = Path("data/test_provider_registry") / uuid4().hex
    wanfang_file = base_dir / "wanfang.json"
    vip_file = base_dir / "vip.json"
    wanfang_file.parent.mkdir(parents=True, exist_ok=True)
    wanfang_file.write_text(
        '{"result":{"duplication_percent":15.4,"aigc_percent":18.6,"confidence":0.83},"version":"wanfang-base-v1"}',
        encoding="utf-8",
    )
    vip_file.write_text(
        '{"payload":{"duplication":11.2,"aigc":14.8},"meta":{"confidence":0.79,"version":"vip-local-v1"}}',
        encoding="utf-8",
    )
    registry_path = base_dir / "provider_registry.json"
    settings = Settings(
        upload_storage_dir=str(base_dir / "uploads"),
        cleaned_storage_dir=str(base_dir / "cleaned"),
        feedback_storage_dir=str(base_dir / "feedback"),
        model_artifact_dir=str(base_dir / "models"),
        calibration_store_path=str(base_dir / "calibration.jsonl"),
        provider_registry_path=str(registry_path),
        provider_files_base_path=str(base_dir),
        provider_configs_json=(
            '{"wanfang":{"mode":"file","path":"'
            + str(wanfang_file).replace("\\", "\\\\")
            + '","field_map":{"duplication_percent":"result.duplication_percent","aigc_percent":"result.aigc_percent","confidence":"result.confidence","version":"version"}}}'
        ),
    )

    app.dependency_overrides[get_settings] = lambda: settings
    try:
        config_list = client.get("/v1/providers/config")
        assert config_list.status_code == 200
        providers = {item["provider"]: item for item in config_list.json()["providers"]}
        assert providers["wanfang"]["configured"] is True
        assert providers["wanfang"]["source"] == "default"
        assert providers["vip"]["configured"] is False

        update_response = client.put(
            "/v1/providers/config/vip",
            json={
                "mode": "file",
                "path": str(vip_file),
                "version": "vip-file-runtime-v1",
                "field_map": {
                    "duplication_percent": "payload.duplication",
                    "aigc_percent": "payload.aigc",
                    "confidence": "meta.confidence",
                    "version": "meta.version",
                },
            },
            headers={"X-Admin-Token": "test-admin-token"},
        )
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["configured"] is True
        assert updated["source"] == "override"
        assert updated["updated_in_registry"] is True
        assert registry_path.exists()

        catalog = client.get("/v1/providers")
        assert catalog.status_code == 200
        catalog_map = {item["provider"]: item for item in catalog.json()["providers"]}
        assert catalog_map["vip"]["configured"] is True
        assert catalog_map["vip"]["mode"] == "file"

        upload = client.post(
            "/v1/documents/upload",
            data={"title": "provider registry demo"},
            files={
                "file": (
                    "provider.docx",
                    make_docx_bytes("链路验证文本，用于测试 provider registry。"),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        assert upload.status_code == 200
        document_id = upload.json()["document_id"]

        analyze = client.post(f"/v1/documents/{document_id}/analyze")
        assert analyze.status_code == 200
        run_id = analyze.json()["run_id"]

        fetched = client.post(
            "/v1/provider-results/fetch",
            json={
                "document_id": document_id,
                "run_id": run_id,
                "provider": "vip",
                "extra_payload": {"trace_id": "registry-case"},
            },
        )
        assert fetched.status_code == 200
        assert fetched.json()["accepted"] is True

        reset_response = client.delete(
            "/v1/providers/config/vip",
            headers={"X-Admin-Token": "test-admin-token"},
        )
        assert reset_response.status_code == 200
        reset_payload = reset_response.json()
        assert reset_payload["configured"] is False
        assert reset_payload["source"] == "none"
        assert reset_payload["updated_in_registry"] is False
    finally:
        if original_admin_token is None:
            os.environ.pop("AI_RATE_ADMIN_TOKEN", None)
        else:
            os.environ["AI_RATE_ADMIN_TOKEN"] = original_admin_token
        if original_settings_override is None:
            app.dependency_overrides.pop(get_settings, None)
        else:
            app.dependency_overrides[get_settings] = original_settings_override


def test_async_analysis_and_ocr_flow_runs_without_login_or_credit_deduction() -> None:
    import os

    original_settings_override = app.dependency_overrides.get(get_settings)
    original_calibrator_override = app.dependency_overrides.get(get_calibrator)
    original_admin_token = os.environ.get("AI_RATE_ADMIN_TOKEN")
    os.environ["AI_RATE_ADMIN_TOKEN"] = "test-admin-token"
    base_dir = Path("data/test_c_end_runtime") / uuid4().hex
    settings = Settings(
        upload_storage_dir=str(base_dir / "uploads"),
        cleaned_storage_dir=str(base_dir / "cleaned"),
        feedback_storage_dir=str(base_dir / "feedback"),
        model_artifact_dir=str(base_dir / "models"),
        calibration_store_path=str(base_dir / "calibration.jsonl"),
        provider_registry_path=str(base_dir / "provider_registry.json"),
        starter_credits=2,
        analysis_credit_cost=1,
    )

    @lru_cache
    def test_calibrator() -> CnkiCalibrator:
        return CnkiCalibrator(settings)

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_calibrator] = test_calibrator
    try:
        upload = client.post(
            "/v1/documents/upload",
            data={"title": "C端闭环论文", "subject": "教育学", "degree_level": "本科"},
            files={
                "file": (
                    "c_end.docx",
                    make_docx_bytes(
                        "这是一个用于测试 C 端异步分析与匿名闭环的样本文本。它包含摘要、方法和结论描述。"
                    ),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        assert upload.status_code == 200
        document_id = upload.json()["document_id"]

        async_task = client.post(f"/v1/documents/{document_id}/analyze-async")
        assert async_task.status_code == 200
        task_id = async_task.json()["task_id"]

        task_payload = None
        for _ in range(20):
            task_response = client.get(f"/v1/tasks/{task_id}")
            assert task_response.status_code == 200
            task_payload = task_response.json()
            if task_payload["status"] == "completed":
                break
        assert task_payload is not None
        assert task_payload["status"] == "completed"
        assert task_payload["run_id"]

        report = client.get(f"/v1/runs/{task_payload['run_id']}/report")
        assert report.status_code == 200
        assert report.json()["title"] == "C端闭环论文"

        ocr_preview = client.post(
            "/v1/cnki-feedback/ocr-preview",
            files={
                "file": (
                    "cnki.txt",
                    "总文字复制比 21.3% AIGC 25.8% 报告日期 2026年4月28日".encode(
                        "utf-8"
                    ),
                    "text/plain",
                )
            },
        )
        assert ocr_preview.status_code == 200
        ocr_payload = ocr_preview.json()
        assert ocr_payload["cnki_dup_percent"] == 21.3
        assert ocr_payload["cnki_aigc_percent"] == 25.8
        assert ocr_payload["report_date"] == "2026-04-28"

        feedback = client.post(
            "/v1/cnki-feedback",
            data={
                "document_id": document_id,
                "predicted_run_id": task_payload["run_id"],
                "cnki_dup_percent": "21.3",
                "cnki_aigc_percent": "25.8",
                "report_date": "2026-04-28",
            },
        )
        assert feedback.status_code == 200
        assert feedback.json()["calibration_updated"] is True

        trained = client.post(
            "/v1/models/train-proxy",
            json={"model_type": "both", "min_samples": 1, "activate": True},
            headers={"X-Admin-Token": "test-admin-token"},
        )
        assert trained.status_code == 200
        assert len(trained.json()["trained_models"]) == 2

        email = f"user_{uuid4().hex[:8]}@example.com"
        register = client.post(
            "/v1/auth/register",
            json={
                "email": email,
                "password": "Password123",
                "display_name": "Demo User",
            },
        )
        assert register.status_code == 200
        token = register.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        billing = client.get("/v1/billing/summary", headers=headers)
        assert billing.status_code == 200
        assert billing.json()["user"]["credits_balance"] == 2

        user_upload = client.post(
            "/v1/documents/upload",
            headers=headers,
            data={
                "title": "登录态闭环论文",
                "subject": "教育学",
                "degree_level": "本科",
            },
            files={
                "file": (
                    "c_end_auth.docx",
                    make_docx_bytes(
                        "这是一个用于确认登录态下也不会扣减额度的样本文本。"
                    ),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        assert user_upload.status_code == 200

        user_task = client.post(
            f"/v1/documents/{user_upload.json()['document_id']}/analyze-async",
            headers=headers,
        )
        assert user_task.status_code == 200

        user_task_payload = None
        for _ in range(20):
            task_response = client.get(
                f"/v1/tasks/{user_task.json()['task_id']}", headers=headers
            )
            assert task_response.status_code == 200
            user_task_payload = task_response.json()
            if user_task_payload["status"] == "completed":
                break
        assert user_task_payload is not None
        assert user_task_payload["status"] == "completed"

        billing_after = client.get("/v1/billing/summary", headers=headers)
        assert billing_after.status_code == 200
        assert billing_after.json()["user"]["credits_balance"] == 2
        assert len(billing_after.json()["recent_tasks"]) >= 1
        assert (
            billing_after.json()["recent_tasks"][0]["run_id"]
            == user_task_payload["run_id"]
        )

        me = client.get("/v1/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["email"] == email

        logout = client.post("/v1/auth/logout", headers=headers)
        assert logout.status_code == 200
    finally:
        if original_admin_token is None:
            os.environ.pop("AI_RATE_ADMIN_TOKEN", None)
        else:
            os.environ["AI_RATE_ADMIN_TOKEN"] = original_admin_token
        if original_settings_override is None:
            app.dependency_overrides.pop(get_settings, None)
        else:
            app.dependency_overrides[get_settings] = original_settings_override
        if original_calibrator_override is None:
            app.dependency_overrides.pop(get_calibrator, None)
        else:
            app.dependency_overrides[get_calibrator] = original_calibrator_override


def test_private_document_access_is_restricted() -> None:
    # 使用独立的 TestClient，避免 Cookie 在测试间泄漏
    isolated_client = TestClient(app)
    original_settings_override = app.dependency_overrides.get(get_settings)
    original_calibrator_override = app.dependency_overrides.get(get_calibrator)
    base_dir = Path("data/test_private_access_runtime") / uuid4().hex
    settings = Settings(
        upload_storage_dir=str(base_dir / "uploads"),
        cleaned_storage_dir=str(base_dir / "cleaned"),
        feedback_storage_dir=str(base_dir / "feedback"),
        model_artifact_dir=str(base_dir / "models"),
        calibration_store_path=str(base_dir / "calibration.jsonl"),
        provider_registry_path=str(base_dir / "provider_registry.json"),
        starter_credits=2,
        analysis_credit_cost=1,
    )

    @lru_cache
    def test_calibrator() -> CnkiCalibrator:
        return CnkiCalibrator(settings)

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_calibrator] = test_calibrator
    try:
        owner_email = f"owner_{uuid4().hex[:8]}@example.com"
        other_email = f"other_{uuid4().hex[:8]}@example.com"

        owner = isolated_client.post(
            "/v1/auth/register",
            json={
                "email": owner_email,
                "password": "Password123",
                "display_name": "Owner",
            },
        )
        assert owner.status_code == 200
        owner_headers = {"Authorization": f"Bearer {owner.json()['token']}"}

        other = isolated_client.post(
            "/v1/auth/register",
            json={
                "email": other_email,
                "password": "Password123",
                "display_name": "Other",
            },
        )
        assert other.status_code == 200
        other_headers = {"Authorization": f"Bearer {other.json()['token']}"}

        upload = isolated_client.post(
            "/v1/documents/upload",
            headers=owner_headers,
            data={
                "title": "private paper",
                "subject": "教育学",
                "degree_level": "本科",
            },
            files={
                "file": (
                    "private.docx",
                    make_docx_bytes(
                        "这是一篇带有私有访问控制的测试论文，用来验证登录用户之外无法查看分析结果。"
                    ),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        assert upload.status_code == 200
        document_id = upload.json()["document_id"]

        # 匿名请求：不携带任何认证信息（也不携带 cookie）
        anonymous_client = TestClient(app)
        anonymous_analyze = anonymous_client.post(
            f"/v1/documents/{document_id}/analyze"
        )
        assert anonymous_analyze.status_code == 403

        foreign_analyze = isolated_client.post(
            f"/v1/documents/{document_id}/analyze", headers=other_headers
        )
        assert foreign_analyze.status_code == 403

        owner_analyze = isolated_client.post(
            f"/v1/documents/{document_id}/analyze", headers=owner_headers
        )
        assert owner_analyze.status_code == 200
        run_id = owner_analyze.json()["run_id"]

        foreign_report = isolated_client.get(
            f"/v1/runs/{run_id}/report", headers=other_headers
        )
        assert foreign_report.status_code == 403

        anonymous_report = anonymous_client.get(f"/v1/runs/{run_id}/report")
        assert anonymous_report.status_code == 403

        owner_report = isolated_client.get(
            f"/v1/runs/{run_id}/report", headers=owner_headers
        )
        assert owner_report.status_code == 200
        assert owner_report.json()["title"] == "private paper"
    finally:
        if original_settings_override is None:
            app.dependency_overrides.pop(get_settings, None)
        else:
            app.dependency_overrides[get_settings] = original_settings_override
        if original_calibrator_override is None:
            app.dependency_overrides.pop(get_calibrator, None)
        else:
            app.dependency_overrides[get_calibrator] = original_calibrator_override


def test_admin_task_summary_requires_admin_token() -> None:
    import os

    original_admin_token = os.environ.get("AI_RATE_ADMIN_TOKEN")
    os.environ["AI_RATE_ADMIN_TOKEN"] = "test-admin-token"
    try:
        unauthorized = client.get("/v1/admin/tasks/summary")
        assert unauthorized.status_code == 403

        authorized = client.get(
            "/v1/admin/tasks/summary",
            headers={"X-Admin-Token": "test-admin-token"},
        )
        assert authorized.status_code == 200
        payload = authorized.json()
        assert {"total", "queued", "processing", "completed", "failed"}.issubset(
            payload.keys()
        )
        assert payload["total"] >= payload["queued"]
    finally:
        if original_admin_token is None:
            os.environ.pop("AI_RATE_ADMIN_TOKEN", None)
        else:
            os.environ["AI_RATE_ADMIN_TOKEN"] = original_admin_token


def test_prod_rejects_local_analysis_queue_backend() -> None:
    from fastapi import BackgroundTasks

    from app.task_queue import dispatch_analysis_task

    settings = Settings(service_env="prod", async_queue_backend="local")
    try:
        dispatch_analysis_task(
            settings=settings,
            task_id="00000000-0000-0000-0000-000000000001",
            document_id="00000000-0000-0000-0000-000000000002",
            user_id=None,
            background_tasks=BackgroundTasks(),
        )
    except RuntimeError as exc:
        assert "production" in str(exc)
    else:
        raise AssertionError("prod local queue backend should be rejected")


def test_billing_order_lifecycle_is_idempotent() -> None:
    original_settings_override = app.dependency_overrides.get(get_settings)
    original_calibrator_override = app.dependency_overrides.get(get_calibrator)
    base_dir = Path("data/test_billing_orders_runtime") / uuid4().hex
    settings = Settings(
        upload_storage_dir=str(base_dir / "uploads"),
        cleaned_storage_dir=str(base_dir / "cleaned"),
        feedback_storage_dir=str(base_dir / "feedback"),
        model_artifact_dir=str(base_dir / "models"),
        calibration_store_path=str(base_dir / "calibration.jsonl"),
        provider_registry_path=str(base_dir / "provider_registry.json"),
        starter_credits=0,
        analysis_credit_cost=1,
        mock_payment_enabled=True,
        payment_callback_secret="test-callback-secret",
    )

    @lru_cache
    def test_calibrator() -> CnkiCalibrator:
        return CnkiCalibrator(settings)

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_calibrator] = test_calibrator
    try:
        owner_email = f"bill_{uuid4().hex[:8]}@example.com"
        other_email = f"bill_other_{uuid4().hex[:8]}@example.com"

        owner = client.post(
            "/v1/auth/register",
            json={
                "email": owner_email,
                "password": "Password123",
                "display_name": "Bill Owner",
            },
        )
        assert owner.status_code == 200
        owner_headers = {"Authorization": f"Bearer {owner.json()['token']}"}

        other = client.post(
            "/v1/auth/register",
            json={
                "email": other_email,
                "password": "Password123",
                "display_name": "Bill Other",
            },
        )
        assert other.status_code == 200
        other_headers = {"Authorization": f"Bearer {other.json()['token']}"}

        create_order = client.post(
            "/v1/billing/orders",
            headers=owner_headers,
            json={"package_code": "starter_5", "provider": "mock_qr"},
        )
        assert create_order.status_code == 200
        order_payload = create_order.json()
        assert order_payload["order"]["status"] == "pending"
        assert order_payload["mock_pay_supported"] is True
        assert order_payload["provider_label"] == "模拟支付"
        assert order_payload["provider_ready"] is True
        order_no = order_payload["order"]["order_no"]

        detail = client.get(f"/v1/billing/orders/{order_no}", headers=owner_headers)
        assert detail.status_code == 200
        assert detail.json()["order"]["order_no"] == order_no

        foreign_detail = client.get(
            f"/v1/billing/orders/{order_no}", headers=other_headers
        )
        assert foreign_detail.status_code == 404

        billing_before = client.get("/v1/billing/summary", headers=owner_headers)
        assert billing_before.status_code == 200
        assert billing_before.json()["user"]["credits_balance"] == 0
        assert billing_before.json()["recent_orders"][0]["status"] == "pending"
        assert len(billing_before.json()["payment_channels"]) >= 3

        alipay_order = client.post(
            "/v1/billing/orders",
            headers=owner_headers,
            json={"package_code": "starter_5", "provider": "alipay"},
        )
        assert alipay_order.status_code == 200
        assert alipay_order.json()["order"]["provider"] == "alipay"
        assert alipay_order.json()["mock_pay_supported"] is False
        assert alipay_order.json()["provider_label"] == "支付宝"
        assert alipay_order.json()["provider_ready"] is False
        alipay_order_no = alipay_order.json()["order"]["order_no"]

        wechat_order = client.post(
            "/v1/billing/orders",
            headers=owner_headers,
            json={"package_code": "starter_5", "provider": "wechat"},
        )
        assert wechat_order.status_code == 200
        assert wechat_order.json()["order"]["provider"] == "wechat"
        assert wechat_order.json()["mock_pay_supported"] is False
        assert wechat_order.json()["provider_label"] == "微信支付"
        assert wechat_order.json()["provider_ready"] is False

        wrong_channel_pay = client.post(
            f"/v1/billing/orders/{alipay_order_no}/mock-pay", headers=owner_headers
        )
        assert wrong_channel_pay.status_code == 400

        pay_once = client.post(
            f"/v1/billing/orders/{order_no}/mock-pay", headers=owner_headers
        )
        assert pay_once.status_code == 200
        assert pay_once.json()["credited"] is True
        assert pay_once.json()["balance_after"] == 5
        assert pay_once.json()["order"]["status"] == "paid"

        pay_twice = client.post(
            f"/v1/billing/orders/{order_no}/mock-pay", headers=owner_headers
        )
        assert pay_twice.status_code == 200
        assert pay_twice.json()["credited"] is False
        assert pay_twice.json()["balance_after"] == 5
        assert pay_twice.json()["order"]["status"] == "paid"

        callback_order = client.post(
            "/v1/billing/orders",
            headers=owner_headers,
            json={"package_code": "starter_5", "provider": "mock_qr"},
        )
        assert callback_order.status_code == 200
        callback_order_no = callback_order.json()["order"]["order_no"]
        callback_amount = callback_order.json()["order"]["amount_cents"]

        import hmac
        import hashlib

        callback_signature = hmac.new(
            settings.payment_callback_secret.encode("utf-8"),
            f"{callback_order_no}:{callback_amount}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        callback_pay = client.post(
            "/v1/billing/callback/mock",
            json={
                "order_no": callback_order_no,
                "paid_amount_cents": callback_amount,
                "signature": callback_signature,
            },
        )
        assert callback_pay.status_code == 200
        assert callback_pay.json()["accepted"] is True
        assert callback_pay.json()["credited"] is True
        assert callback_pay.json()["balance_after"] == 10

        billing_after = client.get("/v1/billing/summary", headers=owner_headers)
        assert billing_after.status_code == 200
        assert billing_after.json()["user"]["credits_balance"] == 10
        assert billing_after.json()["recent_orders"][0]["status"] == "paid"
    finally:
        if original_settings_override is None:
            app.dependency_overrides.pop(get_settings, None)
        else:
            app.dependency_overrides[get_settings] = original_settings_override
        if original_calibrator_override is None:
            app.dependency_overrides.pop(get_calibrator, None)
        else:
            app.dependency_overrides[get_calibrator] = original_calibrator_override
