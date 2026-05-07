from __future__ import annotations

from typing import Any


FEATURE_NAMES = [
    "local_ai_like_score",
    "local_duplication_score",
    "local_segment_count",
    "local_high_risk_segment_count",
    "comfort_score",
    "top_risk_mean",
    "top_risk_max",
    "chapter_max_combined",
    "provider_count",
    "wanfang_dup",
    "wanfang_aigc",
    "vip_dup",
    "vip_aigc",
    "turnitin_dup",
    "turnitin_aigc",
    "manual_dup",
    "manual_aigc",
]


def build_feature_dict_from_runtime(
    *,
    ai_like_score: float,
    duplication_score: float,
    segment_count: int,
    high_risk_segment_count: int,
    comfort_score: int,
    top_risk_sections: list[dict[str, Any]],
    chapter_heatmap: list[dict[str, Any]],
    provider_payloads: list[dict[str, Any]],
) -> dict[str, float]:
    provider_map = _provider_feature_map(provider_payloads)
    top_scores = [float(item.get("combined_score", 0.0)) for item in top_risk_sections]
    chapter_scores = [
        float(item.get("combined_score", 0.0)) for item in chapter_heatmap
    ]
    base = {
        "local_ai_like_score": float(ai_like_score),
        "local_duplication_score": float(duplication_score),
        "local_segment_count": float(segment_count),
        "local_high_risk_segment_count": float(high_risk_segment_count),
        "comfort_score": float(comfort_score) / 100.0,
        "top_risk_mean": sum(top_scores) / len(top_scores) if top_scores else 0.0,
        "top_risk_max": max(top_scores) if top_scores else 0.0,
        "chapter_max_combined": max(chapter_scores) if chapter_scores else 0.0,
        "provider_count": float(sum(1 for value in provider_map.values() if value > 0)),
    }
    base.update(provider_map)
    return {name: round(float(base.get(name, 0.0)), 6) for name in FEATURE_NAMES}


def build_feature_dict_from_snapshot(
    report_json: dict[str, Any], provider_payloads: list[dict[str, Any]]
) -> dict[str, float]:
    local_metrics = report_json.get("local_metrics", {})
    summary = report_json.get("summary", {})
    return build_feature_dict_from_runtime(
        ai_like_score=float(local_metrics.get("ai_like_score", 0.0)),
        duplication_score=float(local_metrics.get("duplication_score", 0.0)),
        segment_count=int(local_metrics.get("segment_count", 0)),
        high_risk_segment_count=int(local_metrics.get("high_risk_segment_count", 0)),
        comfort_score=int(summary.get("comfort_score", 0)),
        top_risk_sections=list(report_json.get("top_risk_sections", [])),
        chapter_heatmap=list(report_json.get("chapter_heatmap", [])),
        provider_payloads=provider_payloads,
    )


def _provider_feature_map(provider_payloads: list[dict[str, Any]]) -> dict[str, float]:
    features = {
        "wanfang_dup": 0.0,
        "wanfang_aigc": 0.0,
        "vip_dup": 0.0,
        "vip_aigc": 0.0,
        "turnitin_dup": 0.0,
        "turnitin_aigc": 0.0,
        "manual_dup": 0.0,
        "manual_aigc": 0.0,
    }
    latest_by_provider: dict[str, dict[str, Any]] = {}
    for payload in provider_payloads:
        if payload.get("payload_type") == "normalized":
            latest_by_provider[payload["provider"]] = payload

    for provider, payload_row in latest_by_provider.items():
        payload = payload_row.get("payload") or {}
        dup_rate = _value_to_rate(
            payload.get("duplication_rate"), payload.get("duplication_percent")
        )
        aigc_rate = _value_to_rate(
            payload.get("aigc_rate"), payload.get("aigc_percent")
        )
        if provider == "wanfang":
            features["wanfang_dup"] = dup_rate
            features["wanfang_aigc"] = aigc_rate
        elif provider == "vip":
            features["vip_dup"] = dup_rate
            features["vip_aigc"] = aigc_rate
        elif provider == "turnitin":
            features["turnitin_dup"] = dup_rate
            features["turnitin_aigc"] = aigc_rate
        elif provider == "manual":
            features["manual_dup"] = dup_rate
            features["manual_aigc"] = aigc_rate
    return features


def _value_to_rate(rate_value: Any, percent_value: Any) -> float:
    if rate_value is not None:
        return float(rate_value)
    if percent_value is not None:
        return float(percent_value) / 100.0
    return 0.0
