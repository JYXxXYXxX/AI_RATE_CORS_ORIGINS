from __future__ import annotations

import ipaddress
import json
import logging
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import Settings
from app.db.repositories import UnifiedRepository
from app.integrations.registry import ProviderRegistryService

logger = logging.getLogger(__name__)
MAX_RETRIES = 3
RETRY_BACKOFF = [1.0, 2.0, 4.0]


class ConfiguredProviderFetchService:
    def __init__(
        self,
        settings: Settings,
        repository: UnifiedRepository,
        registry: ProviderRegistryService | None = None,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.registry = registry or ProviderRegistryService(settings)
        self.provider_configs = self.registry.get_merged_configs()

    def fetch_and_import(
        self,
        *,
        document_id: str,
        run_id: str,
        provider: str,
        extra_payload: dict[str, Any],
    ) -> dict[str, Any]:
        document = self.repository.get_document(document_id)
        if document is None:
            raise ValueError("document not found")
        run = self.repository.get_run(run_id)
        if run is None:
            raise ValueError("run not found")
        if str(run["document_id"]) != document_id:
            raise ValueError("run does not belong to the document")

        config = self.provider_configs.get(provider)
        if not config:
            raise ValueError(f"provider config missing: {provider}")

        request_payload = {
            "document_id": document_id,
            "run_id": run_id,
            "title": document.get("title"),
            "filename": document.get("filename"),
            "subject": document.get("subject"),
            "degree_level": document.get("degree_level"),
            "extra_payload": extra_payload,
        }
        self.repository.insert_provider_payload(run_id, provider, "request", request_payload)
        response_payload = self._fetch(config, request_payload)
        self.repository.insert_provider_payload(run_id, provider, "response", response_payload)

        normalized = self._normalize(provider, config, response_payload)
        payload_row = self.repository.insert_provider_payload_row(run_id, provider, "normalized", normalized)
        return {"payload": payload_row, "normalized": normalized}

    def _fetch(self, config: dict[str, Any], request_payload: dict[str, Any]) -> dict[str, Any]:
        mode = str(config.get("mode", "http")).lower()
        if mode == "file":
            path = config.get("path")
            if not path:
                raise ValueError("provider file path missing")
            p = Path(path).resolve()
            allowed_base = Path(self.settings.provider_files_base_path).resolve()
            try:
                p.relative_to(allowed_base)
            except ValueError:
                raise ValueError("provider file path not allowed") from None
            return json.loads(p.read_text(encoding="utf-8"))

        if mode != "http":
            raise ValueError(f"unsupported provider mode: {mode}")

        url = config.get("url")
        if not url:
            raise ValueError("provider url missing")
        if _is_private_url(str(url)):
            raise ValueError("provider url points to private/internal address")
        method = str(config.get("method", "POST")).upper()
        timeout = float(config.get("timeout_seconds", self.settings.provider_request_timeout_seconds))
        headers = dict(config.get("headers") or {})
        auth_type = str(config.get("auth_type", "")).lower().strip()
        token = _resolve_token(config)
        if auth_type == "bearer" and token:
            headers["Authorization"] = f"Bearer {token}"

        with httpx.Client(timeout=timeout) as client:
            last_exc: Exception | None = None
            for attempt in range(MAX_RETRIES):
                try:
                    if method == "GET":
                        response = client.get(url, params=request_payload, headers=headers)
                    else:
                        response = client.request(method, url, json=request_payload, headers=headers)
                    response.raise_for_status()
                    break
                except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                    last_exc = exc
                    if attempt < MAX_RETRIES - 1:
                        wait = RETRY_BACKOFF[attempt]
                        logger.warning("Provider %s attempt %d failed: %s, retrying in %.1fs", url, attempt + 1, exc, wait)
                        time.sleep(wait)
                    else:
                        raise
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("provider response must be a json object")
        return data

    def _normalize(self, provider: str, config: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        field_map = config.get("field_map") or {}
        duplication_percent = _extract_number(
            payload,
            field_map.get("duplication_percent"),
            ["duplication_percent", "dup_percent", "similarity_percent", "duplicate_percent", "plagiarism_percent"],
        )
        aigc_percent = _extract_number(
            payload,
            field_map.get("aigc_percent"),
            ["aigc_percent", "ai_percent", "ai_rate_percent", "ai_writing_percent", "ai_generated_percent"],
        )
        confidence = _extract_number(
            payload,
            field_map.get("confidence"),
            ["confidence", "score_confidence"],
        )
        version = _extract_string(payload, field_map.get("version"), ["version", "provider_version"]) or config.get("version")
        return {
            "provider": provider,
            "duplication_percent": duplication_percent,
            "duplication_rate": round(duplication_percent / 100, 6) if duplication_percent is not None else None,
            "aigc_percent": aigc_percent,
            "aigc_rate": round(aigc_percent / 100, 6) if aigc_percent is not None else None,
            "confidence": confidence,
            "version": version,
            "raw_payload": payload,
        }
def _is_private_url(url: str) -> bool:
    """检测 URL 是否指向私有/内部地址，防止 SSRF。"""
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        return True
    hostname_lower = hostname.lower()
    if hostname_lower in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        return True
    try:
        ip = ipaddress.ip_address(hostname_lower)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
    except ValueError:
        pass
    return False


def _resolve_token(config: dict[str, Any]) -> str | None:
    if config.get("token"):
        return str(config["token"])
    token_env = config.get("token_env")
    if token_env:
        return os.getenv(str(token_env))
    return None


def _extract_number(payload: dict[str, Any], mapped_path: str | None, fallback_keys: list[str]) -> float | None:
    value = _extract_by_path(payload, mapped_path) if mapped_path else None
    if value is None:
        for key in fallback_keys:
            value = _search_key(payload, key)
            if value is not None:
                break
    if value is None:
        return None
    return float(value)


def _extract_string(payload: dict[str, Any], mapped_path: str | None, fallback_keys: list[str]) -> str | None:
    value = _extract_by_path(payload, mapped_path) if mapped_path else None
    if value is None:
        for key in fallback_keys:
            value = _search_key(payload, key)
            if value is not None:
                break
    return str(value) if value is not None else None


def _extract_by_path(payload: dict[str, Any], path: str | None) -> Any:
    if not path:
        return None
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _search_key(payload: Any, target: str) -> Any:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key == target:
                return value
            nested = _search_key(value, target)
            if nested is not None:
                return nested
    elif isinstance(payload, list):
        for item in payload:
            nested = _search_key(item, target)
            if nested is not None:
                return nested
    return None
