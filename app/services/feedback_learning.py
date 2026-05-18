from __future__ import annotations

import json
import hashlib
from collections import Counter
from pathlib import Path
from typing import Any

from app.services.rewrite_strategy import (
    actionable_marker_count,
    has_verifiable_detail,
)


def build_feedback_learning_sample(
    *,
    repository: Any,
    document: dict[str, Any],
    feedback: dict[str, Any],
    predicted_run_id: str | None,
    details: dict[str, Any] | None,
) -> dict[str, Any] | None:
    official_bindings = _official_binding_features(repository, str(document["id"]))
    if not predicted_run_id and not official_bindings and not _fragment_features(details):
        return None

    snapshot = repository.get_report_snapshot(predicted_run_id) if predicted_run_id else None
    report_json = snapshot.get("report_json") if snapshot else {}
    if not isinstance(report_json, dict):
        report_json = {}

    patches = (
        _safe_list_patches(repository, str(document["id"]), predicted_run_id)
        if predicted_run_id
        else []
    )
    summary = report_json.get("summary") if isinstance(report_json.get("summary"), dict) else {}
    local_metrics = (
        report_json.get("local_metrics")
        if isinstance(report_json.get("local_metrics"), dict)
        else {}
    )

    cnki_dup = _safe_float(feedback.get("cnki_dup_percent"))
    cnki_aigc = _safe_float(feedback.get("cnki_aigc_percent"))
    sample = {
        "version": "feedback-learning-0.2",
        "feedback_id": str(feedback["id"]),
        "document_id_hash": _hash_text(str(document["id"])),
        "run_id_hash": _hash_text(predicted_run_id),
        "scene_key": f"{document.get('subject') or 'general'}:{document.get('degree_level') or 'general'}",
        "created_at": str(feedback.get("created_at") or ""),
        "official_metrics": {
            "cnki_dup_percent": cnki_dup,
            "cnki_aigc_percent": cnki_aigc,
            "report_date": str(feedback.get("report_date") or ""),
        },
        "predicted_metrics": {
            "cnki_dup_center_percent": _band_center(summary, "predicted_cnki_dup"),
            "cnki_aigc_center_percent": _band_center(summary, "predicted_cnki_aigc"),
            "local_ai_like_score": _safe_float(local_metrics.get("ai_like_score")),
            "local_duplication_score": _safe_float(local_metrics.get("duplication_score")),
        },
        "prediction_delta": {},
        "risk_section_features": _risk_section_features(report_json),
        "official_fragment_features": _fragment_features(details),
        "official_bound_span_features": _attach_patch_moves_to_bindings(
            official_bindings, patches
        ),
        "report_alignment": _report_alignment_features(official_bindings, patches),
        "rewrite_pair_features": [_patch_features(item) for item in patches[:24]],
        "outcome": _outcome_label(cnki_dup, cnki_aigc, patches),
    }
    sample["prediction_delta"] = _prediction_delta(
        sample["predicted_metrics"], sample["official_metrics"]
    )
    sample["learned_hints"] = _learned_hints(sample)
    return sample


def append_feedback_learning_sample(
    store_path: str,
    sample: dict[str, Any] | None,
) -> bool:
    if not sample:
        return False
    path = Path(store_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(sample, ensure_ascii=False, default=str) + "\n")
    return True


def append_private_feedback_learning_sample(
    base_dir: str,
    user_id: str | None,
    sample: dict[str, Any] | None,
) -> bool:
    if not user_id or not sample:
        return False
    item = dict(sample)
    item["learning_scope"] = "private_account"
    item["private_user_hash"] = _hash_text(user_id)
    path = Path(base_dir) / f"{_hash_text(user_id)}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False, default=str) + "\n")
    return True


def refresh_feedback_learning_skill(
    store_path: str,
    skill_path: str,
    limit: int = 200,
) -> bool:
    samples = _read_recent_samples(Path(store_path), limit)
    if not samples:
        return False

    summary = _summarize_samples(samples)
    content = _render_skill_markdown(summary)
    path = Path(skill_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def load_feedback_learning_guidance(store_path: str, limit: int = 80) -> str:
    path = Path(store_path)
    if not path.exists():
        return ""

    tag_counter: Counter[str] = Counter()
    outcome_counter: Counter[str] = Counter()
    samples_seen = 0
    for sample in _read_recent_samples(path, limit):
        samples_seen += 1
        outcome = sample.get("outcome")
        if isinstance(outcome, str):
            outcome_counter[outcome] += 1
        for pair in sample.get("rewrite_pair_features") or []:
            if not isinstance(pair, dict):
                continue
            for tag in pair.get("move_tags") or []:
                tag_counter[str(tag)] += 1
        for binding in sample.get("official_bound_span_features") or []:
            if not isinstance(binding, dict):
                continue
            if binding.get("match_method") == "manual":
                tag_counter["official_manual_binding"] += 1
            if binding.get("has_user_patch"):
                tag_counter["official_bound_patch_used"] += 1
            for tag in binding.get("patch_move_tags") or []:
                tag_counter[f"official:{tag}"] += 1
        for hint in sample.get("learned_hints") or []:
            if isinstance(hint, str):
                tag_counter[f"hint:{hint}"] += 1

    if samples_seen == 0 or not tag_counter:
        return ""

    top_tags = ", ".join(tag for tag, _ in tag_counter.most_common(8))
    outcomes = ", ".join(f"{name}={count}" for name, count in outcome_counter.items())
    return (
        "\n\n[Dynamic feedback learning]\n"
        f"Recent official-report feedback samples: {samples_seen}. Outcomes: {outcomes or 'n/a'}.\n"
        f"Prefer rewrite moves that worked most often: {top_tags}.\n"
        "Use these only as strategy signals; never invent official percentages or user-specific facts."
    )


def _summarize_samples(samples: list[dict[str, Any]]) -> dict[str, Any]:
    tag_counter: Counter[str] = Counter()
    hint_counter: Counter[str] = Counter()
    outcome_counter: Counter[str] = Counter()
    scene_counter: Counter[str] = Counter()
    fragment_type_counter: Counter[str] = Counter()
    binding_type_counter: Counter[str] = Counter()
    manual_binding_count = 0
    patched_binding_count = 0
    dup_errors: list[float] = []
    aigc_errors: list[float] = []

    for sample in samples:
        outcome = sample.get("outcome")
        if isinstance(outcome, str):
            outcome_counter[outcome] += 1
        scene = sample.get("scene_key")
        if isinstance(scene, str):
            scene_counter[scene] += 1
        delta = sample.get("prediction_delta")
        if isinstance(delta, dict):
            dup_error = _safe_float(delta.get("dup_percent_error"))
            aigc_error = _safe_float(delta.get("aigc_percent_error"))
            if dup_error is not None:
                dup_errors.append(dup_error)
            if aigc_error is not None:
                aigc_errors.append(aigc_error)
        for fragment in sample.get("official_fragment_features") or []:
            if isinstance(fragment, dict):
                fragment_type_counter[str(fragment.get("type") or "unknown")] += 1
        for binding in sample.get("official_bound_span_features") or []:
            if not isinstance(binding, dict):
                continue
            binding_type_counter[
                f"{binding.get('risk_type') or 'unknown'}:{binding.get('risk_level') or 'unknown'}"
            ] += 1
            if binding.get("match_method") == "manual":
                manual_binding_count += 1
            if binding.get("has_user_patch"):
                patched_binding_count += 1
            for tag in binding.get("patch_move_tags") or []:
                tag_counter[f"official:{tag}"] += 1
        for pair in sample.get("rewrite_pair_features") or []:
            if not isinstance(pair, dict):
                continue
            for tag in pair.get("move_tags") or []:
                tag_counter[str(tag)] += 1
        for hint in sample.get("learned_hints") or []:
            if isinstance(hint, str):
                hint_counter[hint] += 1

    return {
        "sample_count": len(samples),
        "outcomes": outcome_counter,
        "scenes": scene_counter,
        "fragment_types": fragment_type_counter,
        "official_bound_types": binding_type_counter,
        "manual_binding_count": manual_binding_count,
        "patched_binding_count": patched_binding_count,
        "move_tags": tag_counter,
        "hints": hint_counter,
        "avg_dup_error": _mean(dup_errors),
        "avg_aigc_error": _mean(aigc_errors),
    }


def _render_skill_markdown(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "---",
            "name: official-report-feedback-reducer",
            "description: Learned calibration skill generated from user-submitted official similarity/AIGC reports.",
            "---",
            "",
            "# Official Report Feedback Skill",
            "",
            "## Purpose",
            "",
            "Use this skill to align local detection and rewrite advice with official report feedback. The source samples are anonymized feature records, not full user papers.",
            "",
            "## Current Evidence",
            "",
            f"- Recent samples: {summary['sample_count']}",
            f"- Outcomes: {_format_counter(summary['outcomes'])}",
            f"- Main scenes: {_format_counter(summary['scenes'])}",
            f"- Official fragment types: {_format_counter(summary['fragment_types'])}",
            f"- Official bound span types: {_format_counter(summary['official_bound_types'])}",
            f"- Manual official bindings: {summary['manual_binding_count']}",
            f"- Bound spans later rewritten: {summary['patched_binding_count']}",
            f"- Average duplication prediction error: {_format_number(summary['avg_dup_error'])} percentage points",
            f"- Average AIGC prediction error: {_format_number(summary['avg_aigc_error'])} percentage points",
            "",
            "## Learned Checking Signals",
            "",
            *_bullet_lines(summary["hints"], _hint_description),
            "",
            "## Learned Rewrite Moves",
            "",
            *_bullet_lines(summary["move_tags"], _move_tag_description),
            "",
            "## Calibration Rules",
            "",
            "- Treat official matched fragments as high-priority evidence, especially when they map back to a concrete section.",
            "- Treat manually bound official spans as correction signals: they reveal where automatic matching was too strict or the document parser split content differently from the official report.",
            "- When a bound official span has a user patch and the later official report score is low, prefer that patch's move tags for similar risk types.",
            "- If official AIGC or similarity is higher than the local estimate, tighten thresholds for similar scenes and prioritize the matched section over generic normal sections.",
            "- Prefer sentence-skeleton rewrites, concrete module/process details, and removal of official-register phrases over simple synonym replacement.",
            "- Do not expose stored hashes or infer private user text from samples.",
            "",
        ]
    )


def _bullet_lines(counter: Counter[str], describe: Any) -> list[str]:
    if not counter:
        return ["- No stable signal yet."]
    return [
        f"- {name}: {count} samples. {describe(name)}"
        for name, count in counter.most_common(8)
    ]


def _hint_description(name: str) -> str:
    descriptions = {
        "reduce_official_register": "Official reports often punish broad, policy-like wording; prefer concrete academic explanation.",
        "rewrite_sentence_skeleton": "Successful reductions changed subject, clause order, or sentence boundaries.",
        "keep_or_add_verifiable_details": "Concrete versions, modules, dates, metrics, tools, or citations help distinguish human research context.",
        "prioritize_official_matched_fragments": "Officially highlighted fragments should override low-value normal-section output.",
        "prioritize_manual_bound_report_spans": "Manual bindings should be treated as user-verified official risk alignment.",
        "learn_from_bound_span_rewrites": "Patches on officially bound spans are stronger rewrite evidence than patches on unmarked normal text.",
    }
    return descriptions.get(name, "Use as a weak calibration signal until more feedback is collected.")


def _move_tag_description(name: str) -> str:
    descriptions = {
        "formal_register_removed": "Replace words like support/system/mechanism/path/value with concrete action and object.",
        "sentence_boundary_changed": "Break or merge sentences so the rhythm is less template-like.",
        "verifiable_details_preserved": "Keep factual anchors while changing the expression.",
        "verifiable_details_added": "Add missing implementation, data, or citation details when the source paragraph is empty.",
        "length_rebalanced": "Avoid keeping the same sentence length profile as the risky original.",
        "light_polish_only": "This was not a strong reduction move; do not over-trust it.",
        "official:formal_register_removed": "This move worked on an official-report-bound span; prefer it for similar official risk types.",
        "official:sentence_boundary_changed": "This move worked on an official-report-bound span; use it when official reports flag sentence-template risk.",
        "official:verifiable_details_added": "This move worked on an official-report-bound span; add concrete evidence where the original is broad.",
        "official:verifiable_details_preserved": "This move worked on an official-report-bound span; keep factual anchors while changing wording.",
        "official:length_rebalanced": "This move worked on an official-report-bound span; alter rhythm when the official report flags formulaic text.",
    }
    return descriptions.get(name, "Review with more official feedback before making it a hard rule.")


def _safe_list_patches(
    repository: Any, document_id: str, predicted_run_id: str
) -> list[dict[str, Any]]:
    try:
        rows = repository.list_document_patches(document_id, predicted_run_id)
    except Exception:
        return []
    return rows if isinstance(rows, list) else []


def _official_binding_features(
    repository: Any, document_id: str
) -> list[dict[str, Any]]:
    try:
        mappings = repository.list_block_report_mappings(document_id)
    except Exception:
        return []
    if not isinstance(mappings, list):
        return []

    blocks_by_id: dict[str, dict[str, Any]] = {}
    try:
        blocks = repository.list_document_blocks(document_id)
        if isinstance(blocks, list):
            blocks_by_id = {
                str(block.get("block_id")): block
                for block in blocks
                if isinstance(block, dict) and block.get("block_id")
            }
    except Exception:
        blocks_by_id = {}

    features: list[dict[str, Any]] = []
    for mapping in mappings[:80]:
        if not isinstance(mapping, dict):
            continue
        block_id = str(mapping.get("block_id") or "")
        block = blocks_by_id.get(block_id, {})
        span_text = str(mapping.get("span_text") or "")
        block_text = str(block.get("text") or mapping.get("matched_text") or "")
        features.append(
            {
                "report_id_hash": _hash_text(str(mapping.get("report_id") or "")),
                "span_id_hash": _hash_text(str(mapping.get("span_id") or "")),
                "block_id_hash": _hash_text(block_id),
                "risk_type": mapping.get("risk_type") or "unknown",
                "risk_level": mapping.get("risk_level") or "unknown",
                "similarity": _safe_float(mapping.get("similarity")),
                "aigc_score": _safe_float(mapping.get("aigc_score")),
                "match_method": mapping.get("match_method") or "unknown",
                "match_confidence": _safe_float(mapping.get("match_confidence")),
                "span_hash": _hash_text(span_text),
                "span_len": len(span_text),
                "block_hash": _hash_text(block_text),
                "block_len": len(block_text),
                "section_type": block.get("section_type"),
                "section_title_hash": _hash_text(str(block.get("section_title") or "")),
                "display_order": block.get("display_order"),
            }
        )
    return features


def _attach_patch_moves_to_bindings(
    bindings: list[dict[str, Any]], patches: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    patch_features_by_block: dict[str, dict[str, Any]] = {}
    for patch in patches:
        if not isinstance(patch, dict):
            continue
        block_hash = _hash_text(str(patch.get("block_id") or ""))
        patch_features_by_block[block_hash] = _patch_features(patch)

    enriched: list[dict[str, Any]] = []
    for binding in bindings[:80]:
        item = dict(binding)
        patch_feature = patch_features_by_block.get(str(item.get("block_id_hash") or ""))
        item["has_user_patch"] = patch_feature is not None
        item["patch_move_tags"] = (
            patch_feature.get("move_tags", []) if patch_feature else []
        )
        item["patch_length_change_ratio"] = (
            patch_feature.get("length_change_ratio") if patch_feature else None
        )
        enriched.append(item)
    return enriched


def _report_alignment_features(
    official_bindings: list[dict[str, Any]], patches: list[dict[str, Any]]
) -> dict[str, Any]:
    patch_block_hashes = {
        _hash_text(str(patch.get("block_id") or ""))
        for patch in patches
        if isinstance(patch, dict)
    }
    manual_count = sum(
        1 for item in official_bindings if item.get("match_method") == "manual"
    )
    patched_count = sum(
        1
        for item in official_bindings
        if item.get("block_id_hash") in patch_block_hashes
    )
    high_or_medium = sum(
        1
        for item in official_bindings
        if item.get("risk_level") in {"high", "medium"}
    )
    return {
        "official_bound_span_count": len(official_bindings),
        "manual_bound_span_count": manual_count,
        "patched_official_bound_span_count": patched_count,
        "high_or_medium_official_bound_span_count": high_or_medium,
        "official_bound_patch_coverage": round(
            patched_count / max(len(official_bindings), 1), 4
        ),
    }


def _risk_section_features(report_json: dict[str, Any]) -> list[dict[str, Any]]:
    sections = report_json.get("priority_sections") or report_json.get("top_risk_sections") or []
    features: list[dict[str, Any]] = []
    for item in sections[:12]:
        if not isinstance(item, dict):
            continue
        features.append(
            {
                "section_index": item.get("section_index"),
                "risk_level": item.get("risk_level"),
                "aigc_score": _safe_float(item.get("aigc_score")),
                "duplication_score": _safe_float(item.get("duplication_score")),
                "combined_score": _safe_float(item.get("combined_score")),
                "reason_count": len(item.get("reasons") or []),
                "preview_hash": _hash_text(str(item.get("text_preview") or "")),
                "preview_len": len(str(item.get("text_preview") or "")),
            }
        )
    return features


def _fragment_features(details: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(details, dict):
        return []
    fragments = details.get("fragments")
    if not isinstance(fragments, list):
        return []
    features: list[dict[str, Any]] = []
    for item in fragments[:24]:
        if not isinstance(item, dict):
            continue
        source_text = str(item.get("source_text") or "")
        similar_text = str(item.get("similar_text") or "")
        features.append(
            {
                "type": item.get("type") or "unknown",
                "source_hash": _hash_text(source_text),
                "source_len": len(source_text),
                "similar_hash": _hash_text(similar_text),
                "similar_len": len(similar_text),
                "matched_section_index": item.get("matched_section_index"),
                "match_ratio": _safe_float(item.get("match_ratio")),
            }
        )
    return features


def _patch_features(patch: dict[str, Any]) -> dict[str, Any]:
    old_text = str(patch.get("old_text") or "")
    new_text = str(patch.get("new_text") or "")
    old_markers = actionable_marker_count(old_text)
    new_markers = actionable_marker_count(new_text)
    move_tags: list[str] = []
    if old_markers > new_markers:
        move_tags.append("formal_register_removed")
    if _sentence_count(old_text) != _sentence_count(new_text):
        move_tags.append("sentence_boundary_changed")
    if has_verifiable_detail(old_text) and has_verifiable_detail(new_text):
        move_tags.append("verifiable_details_preserved")
    elif not has_verifiable_detail(old_text) and has_verifiable_detail(new_text):
        move_tags.append("verifiable_details_added")
    if _length_change_ratio(old_text, new_text) >= 0.18:
        move_tags.append("length_rebalanced")
    if not move_tags:
        move_tags.append("light_polish_only")

    return {
        "block_id_hash": _hash_text(str(patch.get("block_id") or "")),
        "old_hash": _hash_text(old_text),
        "new_hash": _hash_text(new_text),
        "old_len": len(old_text),
        "new_len": len(new_text),
        "length_change_ratio": _length_change_ratio(old_text, new_text),
        "old_actionable_marker_count": old_markers,
        "new_actionable_marker_count": new_markers,
        "move_tags": move_tags,
    }


def _learned_hints(sample: dict[str, Any]) -> list[str]:
    tags: Counter[str] = Counter()
    for pair in sample.get("rewrite_pair_features") or []:
        for tag in pair.get("move_tags") or []:
            tags[str(tag)] += 1
    hints: list[str] = []
    if tags["formal_register_removed"]:
        hints.append("reduce_official_register")
    if tags["sentence_boundary_changed"]:
        hints.append("rewrite_sentence_skeleton")
    if tags["verifiable_details_added"] or tags["verifiable_details_preserved"]:
        hints.append("keep_or_add_verifiable_details")
    if sample.get("official_fragment_features"):
        hints.append("prioritize_official_matched_fragments")
    alignment = sample.get("report_alignment")
    if isinstance(alignment, dict):
        if int(alignment.get("manual_bound_span_count") or 0) > 0:
            hints.append("prioritize_manual_bound_report_spans")
        if int(alignment.get("patched_official_bound_span_count") or 0) > 0:
            hints.append("learn_from_bound_span_rewrites")
    return hints[:6]


def _prediction_delta(
    predicted_metrics: dict[str, Any], official_metrics: dict[str, Any]
) -> dict[str, Any]:
    return {
        "dup_percent_error": _subtract(
            predicted_metrics.get("cnki_dup_center_percent"),
            official_metrics.get("cnki_dup_percent"),
        ),
        "aigc_percent_error": _subtract(
            predicted_metrics.get("cnki_aigc_center_percent"),
            official_metrics.get("cnki_aigc_percent"),
        ),
    }


def _outcome_label(
    cnki_dup_percent: float | None,
    cnki_aigc_percent: float | None,
    patches: list[dict[str, Any]],
) -> str:
    has_rewrite = bool(patches)
    dup_ok = cnki_dup_percent is None or cnki_dup_percent <= 10
    aigc_ok = cnki_aigc_percent is None or cnki_aigc_percent <= 12
    if has_rewrite and dup_ok and aigc_ok:
        return "successful_rewrite_feedback"
    if dup_ok and aigc_ok:
        return "low_risk_feedback"
    return "needs_more_rewrite"


def _band_center(summary: dict[str, Any], key: str) -> float | None:
    band = summary.get(key)
    if isinstance(band, dict):
        return _safe_float(band.get("center_percent"))
    return None


def _read_recent_samples(path: Path, limit: int) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    samples: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            samples.append(payload)
    return samples


def _sentence_count(text: str) -> int:
    return max(1, sum(1 for char in text if char in "。！？；.!?;"))


def _length_change_ratio(old_text: str, new_text: str) -> float:
    base = max(len(old_text), 1)
    return round(abs(len(new_text) - len(old_text)) / base, 4)


def _subtract(left: Any, right: Any) -> float | None:
    left_value = _safe_float(left)
    right_value = _safe_float(right)
    if left_value is None or right_value is None:
        return None
    return round(left_value - right_value, 4)


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _format_counter(counter: Counter[str]) -> str:
    if not counter:
        return "n/a"
    return ", ".join(f"{name}={count}" for name, count in counter.most_common(6))


def _format_number(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}"


def _hash_text(text: str) -> str:
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
