from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from pathlib import Path
from typing import Any

from app.config import Settings
from app.services.docx_patch import export_docx_with_patch_report


SAVE_STATUSES = {2, 6}
SUPPORTED_EXTENSIONS = {".docx"}


def is_onlyoffice_enabled(settings: Settings) -> bool:
    return bool(settings.onlyoffice_enabled and settings.onlyoffice_document_server_url)


def get_document_extension(document: dict[str, Any]) -> str:
    filename = str(document.get("filename") or "")
    original_path = str(document.get("original_file_path") or "")
    ext = Path(filename).suffix.lower()
    if ext:
        return ext
    return Path(original_path).suffix.lower()


def get_original_docx_path(document: dict[str, Any]) -> Path | None:
    path = Path(str(document.get("original_file_path") or ""))
    if path.exists() and path.suffix.lower() == ".docx":
        return path
    return None


def is_onlyoffice_supported(document: dict[str, Any]) -> tuple[bool, str | None]:
    path = get_original_docx_path(document)
    if path is None:
        ext = get_document_extension(document) or "unknown"
        return False, f"当前仅支持 DOCX 在线保格式改写，当前文件类型为 {ext}"
    return True, None


def onlyoffice_work_dir(settings: Settings, document_id: str) -> Path:
    return Path(settings.upload_storage_dir) / "onlyoffice" / document_id


def onlyoffice_edited_path(settings: Settings, document_id: str) -> Path:
    return onlyoffice_work_dir(settings, document_id) / "edited.docx"


def _shared_secret(settings: Settings) -> str:
    return (
        settings.onlyoffice_jwt_secret
        or settings.payment_callback_secret
        or "patafix-onlyoffice-local-secret"
    )


def _urlsafe_b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _sign_payload(payload: dict[str, Any], secret: str) -> str:
    body = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    digest = hmac.new(secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    token = {"payload": payload, "sig": digest}
    return _urlsafe_b64(json.dumps(token, ensure_ascii=True, separators=(",", ":")).encode("utf-8"))


def make_access_token(
    settings: Settings,
    *,
    document_id: str,
    purpose: str,
    ttl_seconds: int = 60 * 60 * 6,
) -> str:
    now = int(time.time())
    payload = {
        "document_id": document_id,
        "purpose": purpose,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    return _sign_payload(payload, _shared_secret(settings))


def validate_access_token(
    settings: Settings,
    token: str,
    *,
    document_id: str,
    purpose: str,
) -> bool:
    try:
        raw = token.encode("ascii")
        padded = raw + b"=" * (-len(raw) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded))
        payload = data["payload"]
        sig = str(data["sig"])
    except Exception:
        return False

    expected = hmac.new(
        _shared_secret(settings).encode("utf-8"),
        json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return False
    if payload.get("document_id") != document_id or payload.get("purpose") != purpose:
        return False
    if int(payload.get("exp", 0)) < int(time.time()):
        return False
    return True


def create_jwt(payload: dict[str, Any], secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = f"{_urlsafe_b64(json.dumps(header, separators=(',', ':')).encode('utf-8'))}.{_urlsafe_b64(json.dumps(payload, separators=(',', ':')).encode('utf-8'))}"
    signature = hmac.new(
        secret.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_urlsafe_b64(signature)}"


def ensure_working_copy(
    settings: Settings,
    repository: Any,
    *,
    document: dict[str, Any],
    run_id: str,
) -> Path:
    original_path = get_original_docx_path(document)
    if original_path is None:
        raise ValueError("onlyoffice working copy requires a docx source")

    document_id = str(document["id"])
    edited_path = onlyoffice_edited_path(settings, document_id)
    if edited_path.exists():
        return edited_path

    patches = repository.list_latest_patches_by_run(document_id, run_id)
    if not patches:
        return original_path

    blocks = repository.list_document_blocks(document_id)
    result = export_docx_with_patch_report(
        str(original_path),
        blocks,
        patches,
        highlight_risks=False,
        strict=False,
    )
    edited_path.parent.mkdir(parents=True, exist_ok=True)
    edited_path.write_bytes(result.content)
    return edited_path


def apply_patch_to_working_copy(
    settings: Settings,
    repository: Any,
    *,
    document: dict[str, Any],
    run_id: str,
    block_id: str | None = None,
) -> dict[str, int]:
    original_path = get_original_docx_path(document)
    if original_path is None:
        raise ValueError("当前文件不是可保格式改写的 DOCX")

    document_id = str(document["id"])
    base_path = onlyoffice_edited_path(settings, document_id)
    if not base_path.exists():
        base_path = ensure_working_copy(
            settings,
            repository,
            document=document,
            run_id=run_id,
        )

    patches = repository.list_latest_patches_by_run(document_id, run_id)
    if block_id is not None:
        patches = [patch for patch in patches if str(patch.get("block_id")) == block_id]
    if not patches:
        return {
            "requested": 0,
            "applied": 0,
            "failed": 0,
            "skipped": 0,
            "highlighted": 0,
        }

    blocks = repository.list_document_blocks(document_id)
    result = export_docx_with_patch_report(
        str(base_path),
        blocks,
        patches,
        highlight_risks=False,
        strict=False,
    )
    target = onlyoffice_edited_path(settings, document_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(result.content)
    stats = result.stats
    return {
        "requested": stats.requested_patch_count,
        "applied": stats.applied_count,
        "failed": stats.failed_count,
        "skipped": stats.skipped_block_count,
        "highlighted": stats.highlighted_block_count,
    }


def build_editor_config(
    settings: Settings,
    *,
    repository: Any,
    run: dict[str, Any],
    document: dict[str, Any],
    user_id: str | None,
    display_name: str | None,
    browser_base_url: str | None = None,
) -> dict[str, Any]:
    working_path = ensure_working_copy(
        settings,
        repository=repository,
        document=document,
        run_id=str(run["id"]),
    )
    stat = working_path.stat()
    file_token = make_access_token(
        settings,
        document_id=str(document["id"]),
        purpose="file",
    )
    callback_token = make_access_token(
        settings,
        document_id=str(document["id"]),
        purpose="callback",
        ttl_seconds=60 * 60 * 12,
    )
    backend_base = settings.onlyoffice_backend_base_url.rstrip("/")
    browser_base = str(browser_base_url or backend_base).rstrip("/")
    proxy_base = f"{browser_base}/v1/onlyoffice"
    title = str(document.get("filename") or document.get("title") or "paper.docx")
    document_key = hashlib.sha1(
        f"{document['id']}:{run['id']}:{stat.st_mtime_ns}:{stat.st_size}".encode("utf-8")
    ).hexdigest()[:20]
    config: dict[str, Any] = {
        "documentType": "word",
        "type": "desktop",
        "width": "100%",
        "height": "100%",
        "document": {
            "title": title,
            "url": f"{backend_base}/v1/documents/{document['id']}/onlyoffice/file?token={file_token}",
            "fileType": "docx",
            "key": document_key,
            "permissions": {
                "edit": True,
                "download": False,
                "print": True,
                "comment": False,
                "copy": True,
                "review": False,
            },
        },
        "editorConfig": {
            "mode": "edit",
            "lang": "zh-CN",
            "callbackUrl": f"{backend_base}/v1/documents/{document['id']}/onlyoffice/callback?token={callback_token}",
            "user": {
                "id": user_id or "guest",
                "name": display_name or "PataFix User",
            },
            "customization": {
                "autosave": True,
                "forcesave": True,
                "compactHeader": False,
                "toolbarHideFileName": False,
                "hideRightMenu": False,
            },
        },
    }
    if settings.onlyoffice_jwt_secret:
        config["token"] = create_jwt(config, settings.onlyoffice_jwt_secret)

    return {
        "enabled": True,
        "supported": True,
        "documentServerUrl": proxy_base,
        "scriptUrl": f"{proxy_base}/web-apps/apps/api/documents/api.js",
        "editorConfig": config,
        "sourceFormat": "docx",
        "workingCopyReady": True,
    }
