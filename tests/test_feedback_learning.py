from pathlib import Path

from app.services.feedback_learning import (
    append_feedback_learning_sample,
    build_feedback_learning_sample,
    load_feedback_learning_guidance,
    refresh_feedback_learning_skill,
)


class FakeLearningRepository:
    def get_report_snapshot(self, run_id: str) -> dict:
        return {
            "report_json": {
                "summary": {
                    "predicted_cnki_dup": {"center_percent": 18.0},
                    "predicted_cnki_aigc": {"center_percent": 28.0},
                },
                "local_metrics": {
                    "ai_like_score": 0.41,
                    "duplication_score": 0.2,
                },
                "priority_sections": [
                    {
                        "section_index": 2,
                        "risk_level": "high",
                        "aigc_score": 0.72,
                        "duplication_score": 0.31,
                        "combined_score": 0.55,
                        "reasons": ["template"],
                        "text_preview": "随着系统持续发展，该机制提供了支撑。",
                    }
                ],
            }
        }

    def list_document_patches(self, document_id: str, run_id: str) -> list[dict]:
        return [
            {
                "block_id": "block-1",
                "old_text": "随着系统持续发展，该机制为平台提供了支撑。",
                "new_text": "在本系统中，预算提醒模块会先读取 MySQL 8.0 中的收支记录，再生成提示。",
            }
        ]


def test_feedback_learning_sample_is_anonymized_and_actionable() -> None:
    sample = build_feedback_learning_sample(
        repository=FakeLearningRepository(),
        document={"id": "doc-1", "subject": "cs", "degree_level": "本科"},
        feedback={
            "id": "fb-1",
            "cnki_dup_percent": 4.0,
            "cnki_aigc_percent": 5.0,
            "report_date": "2026-05-15",
            "created_at": "2026-05-15T10:00:00",
        },
        predicted_run_id="run-1",
        details={
            "fragments": [
                {
                    "type": "aigc",
                    "source_text": "随着系统持续发展",
                    "similar_text": "",
                    "matched_section_index": 2,
                    "match_ratio": 0.91,
                }
            ]
        },
    )

    assert sample is not None
    pair = sample["rewrite_pair_features"][0]
    assert "old_text" not in pair
    assert "new_text" not in pair
    assert "formal_register_removed" in pair["move_tags"]
    assert "verifiable_details_added" in pair["move_tags"]
    assert "prioritize_official_matched_fragments" in sample["learned_hints"]


def test_feedback_learning_guidance_reads_recent_samples(tmp_path: Path) -> None:
    path = tmp_path / "learning.jsonl"
    sample = build_feedback_learning_sample(
        repository=FakeLearningRepository(),
        document={"id": "doc-1", "subject": "cs", "degree_level": "本科"},
        feedback={
            "id": "fb-1",
            "cnki_dup_percent": 4.0,
            "cnki_aigc_percent": 5.0,
        },
        predicted_run_id="run-1",
        details={"fragments": []},
    )

    assert append_feedback_learning_sample(str(path), sample) is True

    guidance = load_feedback_learning_guidance(str(path))

    assert "Dynamic feedback learning" in guidance
    assert "formal_register_removed" in guidance


def test_feedback_learning_refreshes_skill_file(tmp_path: Path) -> None:
    store_path = tmp_path / "learning.jsonl"
    skill_path = tmp_path / "feedback_skill" / "SKILL.md"
    sample = build_feedback_learning_sample(
        repository=FakeLearningRepository(),
        document={"id": "doc-1", "subject": "cs", "degree_level": "本科"},
        feedback={
            "id": "fb-1",
            "cnki_dup_percent": 4.0,
            "cnki_aigc_percent": 5.0,
        },
        predicted_run_id="run-1",
        details={"fragments": [{"type": "aigc", "source_text": "demo"}]},
    )

    assert append_feedback_learning_sample(str(store_path), sample) is True
    assert refresh_feedback_learning_skill(str(store_path), str(skill_path)) is True

    content = skill_path.read_text(encoding="utf-8")
    assert "official-report-feedback-reducer" in content
    assert "formal_register_removed" in content
    assert "Calibration Rules" in content
