from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from app.config import Settings

KNOWN_PROVIDERS = ("wanfang", "vip", "turnitin", "manual")
AUTO_FETCH_PROVIDERS = ("wanfang", "vip", "turnitin")


class ProviderRegistryService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.registry_path = Path(settings.provider_registry_path)
        self.base_configs = load_provider_configs(
            settings.provider_configs_json, source_name="provider_configs_json"
        )
        self.override_configs = self._load_registry_file()

    def get_runtime_config(self, provider: str) -> dict[str, Any] | None:
        return self.get_merged_configs().get(provider)

    def get_merged_configs(self) -> dict[str, dict[str, Any]]:
        merged = {key: deepcopy(value) for key, value in self.base_configs.items()}
        for provider, override in self.override_configs.items():
            merged[provider] = _merge_dict(merged.get(provider, {}), override)
        return merged

    def list_public_configs(self) -> list[dict[str, Any]]:
        return [self.get_public_config(provider) for provider in KNOWN_PROVIDERS]

    def get_public_config(self, provider: str) -> dict[str, Any]:
        provider_key = _normalize_provider_name(provider)
        merged_config = self.get_runtime_config(provider_key) or {}
        validation_errors = _validate_provider_config(provider_key, merged_config)
        mode = (
            str(merged_config.get("mode")).lower()
            if merged_config.get("mode") is not None
            else None
        )
        method = (
            str(merged_config.get("method", "POST")).upper()
            if mode == "http" or merged_config.get("method")
            else None
        )
        auth_type = str(merged_config.get("auth_type", "")).lower().strip() or None
        timeout = merged_config.get("timeout_seconds")
        timeout_seconds = float(timeout) if timeout is not None else None

        return {
            "provider": provider_key,
            "supports_auto_fetch": provider_key in AUTO_FETCH_PROVIDERS,
            "configured": provider_key in AUTO_FETCH_PROVIDERS
            and not validation_errors,
            "source": _provider_source(
                provider_key, self.base_configs, self.override_configs
            ),
            "mode": mode,
            "method": method,
            "url": _to_optional_string(merged_config.get("url")),
            "path": _to_optional_string(merged_config.get("path")),
            "auth_type": auth_type,
            "token_env": _to_optional_string(merged_config.get("token_env")),
            "has_inline_token": bool(merged_config.get("token")),
            "version": _to_optional_string(merged_config.get("version")),
            "timeout_seconds": timeout_seconds,
            "headers": _to_string_dict(merged_config.get("headers")),
            "field_map": _to_string_dict(merged_config.get("field_map")),
            "validation_errors": validation_errors,
            "updated_in_registry": provider_key in self.override_configs,
        }

    def update_provider_config(
        self, provider: str, config: dict[str, Any]
    ) -> dict[str, Any]:
        provider_key = _normalize_provider_name(provider)
        if provider_key not in AUTO_FETCH_PROVIDERS:
            raise ValueError(
                f"provider does not support runtime fetch config: {provider_key}"
            )

        normalized = _normalize_provider_config(config)
        errors = _validate_provider_config(provider_key, normalized)
        if errors:
            raise ValueError("; ".join(errors))

        overrides = self._load_registry_file()
        overrides[provider_key] = normalized
        self._save_registry_file(overrides)
        self.override_configs = overrides
        return self.get_public_config(provider_key)

    def reset_provider_config(self, provider: str) -> dict[str, Any]:
        provider_key = _normalize_provider_name(provider)
        overrides = self._load_registry_file()
        if provider_key in overrides:
            overrides.pop(provider_key, None)
            self._save_registry_file(overrides)
        self.override_configs = overrides
        return self.get_public_config(provider_key)

    def _load_registry_file(self) -> dict[str, dict[str, Any]]:
        if not self.registry_path.exists():
            return {}
        try:
            payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("provider registry file is not valid json") from exc
        if not isinstance(payload, dict):
            raise ValueError("provider registry file must be a json object")
        return {
            str(key): value for key, value in payload.items() if isinstance(value, dict)
        }

    def _save_registry_file(self, payload: dict[str, dict[str, Any]]) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )


def load_provider_configs(
    raw_json: str, *, source_name: str = "provider_configs_json"
) -> dict[str, dict[str, Any]]:
    if not raw_json.strip():
        return {}
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{source_name} is not valid json") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{source_name} must be a json object")
    return {
        str(key): value for key, value in payload.items() if isinstance(value, dict)
    }


def _normalize_provider_name(provider: str) -> str:
    return str(provider).strip().lower()


def _normalize_provider_config(config: dict[str, Any]) -> dict[str, Any]:
    mode = str(config.get("mode", "")).strip().lower()
    normalized: dict[str, Any] = {
        "mode": mode,
        "method": str(config.get("method", "POST")).strip().upper() or "POST",
        "url": _strip_or_none(config.get("url")),
        "path": _strip_or_none(config.get("path")),
        "auth_type": _strip_or_none(str(config.get("auth_type", "")).strip().lower()),
        "token_env": _strip_or_none(config.get("token_env")),
        "version": _strip_or_none(config.get("version")),
        "headers": _to_string_dict(config.get("headers")),
        "field_map": _to_string_dict(config.get("field_map")),
    }
    timeout = config.get("timeout_seconds")
    normalized["timeout_seconds"] = float(timeout) if timeout is not None else None
    return normalized


def _validate_provider_config(provider: str, config: dict[str, Any]) -> list[str]:
    if provider not in AUTO_FETCH_PROVIDERS:
        return []
    if not config:
        return ["mode is required"]

    mode = str(config.get("mode", "")).lower().strip()
    errors: list[str] = []
    if mode not in {"http", "file"}:
        errors.append("mode must be http or file")
        return errors

    if mode == "http":
        if not config.get("url"):
            errors.append("url is required for http mode")
        method = str(config.get("method", "POST")).upper()
        if method not in {"GET", "POST", "PUT", "PATCH"}:
            errors.append("method must be GET, POST, PUT, or PATCH")
    if mode == "file" and not config.get("path"):
        errors.append("path is required for file mode")

    timeout = config.get("timeout_seconds")
    if timeout is not None and float(timeout) <= 0:
        errors.append("timeout_seconds must be greater than 0")
    return errors


def _provider_source(
    provider: str,
    base_configs: dict[str, dict[str, Any]],
    override_configs: dict[str, dict[str, Any]],
) -> str:
    in_base = provider in base_configs
    in_override = provider in override_configs
    if in_base and in_override:
        return "merged"
    if in_override:
        return "override"
    if in_base:
        return "default"
    return "none"


def _merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dict(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _strip_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_string_dict(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items() if item is not None}


def _to_optional_string(value: Any) -> str | None:
    return str(value) if value is not None else None
