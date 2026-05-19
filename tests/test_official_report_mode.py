from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routes import documents
from app.routes.deps import AuthContext
from app.services.block_matcher import match_spans_to_blocks
from app.services.cnki_report_parser import CnkiRiskSpan
from app.schemas_unified import ReanalyzeRequest


class FakeReportRepository:
    def __init__(
        self,
        *,
        blocks: list[dict] | None = None,
        reports: list[dict] | None = None,
        spans: list[dict] | None = None,
        mappings: list[dict] | None = None,
    ):
        self.blocks = blocks or []
        self.reports = reports or []
        self.spans = spans or []
        self.mappings = mappings or []

    def get_run(self, run_id: str) -> dict:
        return {
            "id": run_id,
            "document_id": "doc-1",
            "mode": "report",
            "subject": "软件工程",
            "degree_level": "本科",
        }

    def can_user_access_document(self, *, user_id: str | None, document_id: str) -> bool:
        return True

    def list_document_blocks(self, document_id: str) -> list[dict]:
        return self.blocks

    def list_latest_patches_by_run(self, document_id: str, run_id: str) -> list[dict]:
        return []

    def list_document_patches(self, document_id: str, run_id: str) -> list[dict]:
        return []

    def get_report_snapshot(self, run_id: str) -> dict | None:
        return None

    def list_cnki_reports_by_document(self, document_id: str) -> list[dict]:
        return self.reports

    def list_cnki_report_spans(self, report_id: str) -> list[dict]:
        return [span for span in self.spans if str(span.get("report_id")) == str(report_id)]

    def get_cnki_report_span(self, report_id: str, span_id: str) -> dict | None:
        return next(
            (
                span
                for span in self.spans
                if str(span.get("report_id")) == str(report_id)
                and span.get("span_id") == span_id
            ),
            None,
        )

    def list_unmapped_cnki_report_spans(self, report_id: str) -> list[dict]:
        mapped = {
            mapping.get("span_id")
            for mapping in self.mappings
            if str(mapping.get("report_id")) == str(report_id)
        }
        return [
            span
            for span in self.list_cnki_report_spans(report_id)
            if span.get("span_id") not in mapped
        ]

    def list_block_report_mappings(self, document_id: str) -> list[dict]:
        return [
            mapping
            for mapping in self.mappings
            if str(mapping.get("document_id")) == str(document_id)
        ]

    def get_document_block(self, document_id: str, block_id: str) -> dict | None:
        return next((block for block in self.blocks if block.get("block_id") == block_id), None)

    def insert_block_report_mapping(self, **kwargs) -> dict:
        mapping = {**kwargs, "id": f"mapping-{len(self.mappings) + 1}"}
        self.mappings.append(mapping)
        return mapping

    def update_block_report_risk(
        self, document_id: str, block_id: str, report_risk: dict
    ) -> dict | None:
        block = self.get_document_block(document_id, block_id)
        if block is None:
            return None
        block["report_risk"] = report_risk
        return block


class FakeRewriteService:
    def __init__(self) -> None:
        self.kwargs: dict | None = None

    async def rewrite_paragraph(self, **kwargs):
        self.kwargs = kwargs
        return {
            "diagnosis": "官方报告标记片段需要重构句式。",
            "sentences": [
                {
                    "original": "原句",
                    "risk": "high",
                    "rewritten": "改写句",
                    "explanation": "按官方相似来源调整。",
                }
            ],
            "rewritten_paragraph": "改写后的段落。",
            "overall_advice": "优先处理官方标记片段。",
        }


def test_block_matcher_accepts_repository_block_dicts() -> None:
    spans = [
        CnkiRiskSpan(
            span_id="span-1",
            text="本系统使用 SpringBoot 和 Vue 完成预算提醒与账单管理模块。",
            risk_type="similarity",
            risk_level="high",
            similarity=82.0,
        )
    ]
    blocks = [
        {
            "block_id": "b1",
            "block_type": "paragraph",
            "text": "本系统使用 SpringBoot 和 Vue 完成预算提醒与账单管理模块，并补充了统计分析能力。",
            "source_type": "docx",
            "source_map": {"paragraphIndex": 8},
            "display_order": 8,
            "char_count": 40,
        }
    ]

    mappings, unmatched = match_spans_to_blocks(spans, blocks)

    assert len(mappings) == 1
    assert mappings[0].block_id == "b1"
    assert mappings[0].match_method in {"exact", "normalized", "fuzzy"}
    assert unmatched == []


def test_report_mode_reanalyze_requires_new_official_report(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(documents, "get_repository", lambda: FakeReportRepository())

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            documents.reanalyze_run(
                "run-report",
                ReanalyzeRequest(sections=[]),
                auth=AuthContext(token=None, user=None),
            )
        )

    assert exc.value.status_code == 409
    assert "官方" in exc.value.detail
    assert "复检报告" in exc.value.detail


def test_run_blocks_returns_official_report_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = FakeReportRepository(
        blocks=[
            {
                "block_id": "b1",
                "block_type": "paragraph",
                "text": "高风险段落",
                "source_type": "txt",
                "source_map": {"paragraphIndex": 1},
                "display_order": 1,
                "char_count": 5,
                "report_risk": {
                    "source": "cnki",
                    "risk_type": "aigc",
                    "risk_level": "high",
                    "aigc_score": 88.0,
                    "span_id": "s1",
                    "match_confidence": 0.95,
                },
            },
            {
                "block_id": "b2",
                "block_type": "paragraph",
                "text": "中风险段落",
                "source_type": "txt",
                "source_map": {"paragraphIndex": 2},
                "display_order": 2,
                "char_count": 5,
                "report_risk": {
                    "source": "cnki",
                    "risk_type": "similarity",
                    "risk_level": "medium",
                    "similarity": 61.0,
                    "span_id": "s2",
                    "match_confidence": 0.9,
                },
            },
        ],
        reports=[
            {
                "report_type": "mixed",
                "total_copy_ratio": 18.5,
                "aigc_ratio": 42.0,
            }
        ],
    )
    monkeypatch.setattr(documents, "get_repository", lambda: repo)

    response = asyncio.run(
        documents.get_run_blocks("run-report", auth=AuthContext(token=None, user=None))
    )

    assert response["reportSummary"] == {
        "reportType": "mixed",
        "totalCopyRatio": 18.5,
        "aigcRatio": 42.0,
        "highRiskCount": 1,
        "mediumRiskCount": 1,
        "lowRiskCount": 0,
        "unmatchedCount": 0,
    }


def test_run_blocks_returns_unmatched_official_spans(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = FakeReportRepository(
        blocks=[],
        reports=[
            {
                "id": "report-1",
                "report_type": "mixed",
                "total_copy_ratio": 18.5,
                "aigc_ratio": 42.0,
            }
        ],
        spans=[
            {
                "report_id": "report-1",
                "span_id": "s1",
                "text": "已匹配官方风险片段",
                "risk_type": "aigc",
                "risk_level": "high",
                "aigc_score": 88.0,
            },
            {
                "report_id": "report-1",
                "span_id": "s2",
                "text": "未匹配官方风险片段",
                "risk_type": "similarity",
                "risk_level": "medium",
                "similarity": 61.0,
            },
        ],
        mappings=[
            {
                "document_id": "doc-1",
                "report_id": "report-1",
                "span_id": "s1",
                "block_id": "b1",
            }
        ],
    )
    monkeypatch.setattr(documents, "get_repository", lambda: repo)

    response = asyncio.run(
        documents.get_run_blocks("run-report", auth=AuthContext(token=None, user=None))
    )

    assert response["reportSummary"]["highRiskCount"] == 1
    assert response["reportSummary"]["mediumRiskCount"] == 1
    assert response["reportSummary"]["unmatchedCount"] == 1
    assert response["unmatchedSpans"][0].span_id == "s2"


def test_manual_bind_report_span_updates_block_risk(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = FakeReportRepository(
        blocks=[
            {
                "block_id": "b2",
                "block_type": "paragraph",
                "text": "正文里对应的风险段落",
                "source_type": "txt",
                "source_map": {"paragraphIndex": 2},
                "display_order": 2,
                "char_count": 10,
                "report_risk": None,
            }
        ],
        reports=[
            {
                "id": "report-1",
                "report_type": "mixed",
                "total_copy_ratio": 18.5,
                "aigc_ratio": 42.0,
            }
        ],
        spans=[
            {
                "report_id": "report-1",
                "span_id": "s2",
                "text": "未匹配官方风险片段",
                "risk_type": "similarity",
                "risk_level": "medium",
                "similarity": 61.0,
            },
        ],
    )
    monkeypatch.setattr(documents, "get_repository", lambda: repo)

    response = asyncio.run(
        documents.bind_report_span_to_block(
            "run-report",
            documents.ManualReportSpanBindRequest(span_id="s2", block_id="b2"),
            auth=AuthContext(token=None, user=None),
        )
    )

    assert response.unmatched_count == 0
    assert response.mapped_count == 1
    assert repo.blocks[0]["report_risk"]["span_id"] == "s2"
    assert repo.blocks[0]["report_risk"]["risk_level"] == "medium"
    assert repo.mappings[0]["match_method"] == "manual"


def test_official_report_upload_can_save_learning_sample(tmp_path) -> None:
    repo = FakeReportRepository(
        blocks=[
            {
                "block_id": "b1",
                "block_type": "paragraph",
                "text": "随着系统持续发展，该机制为平台提供了支撑。",
                "source_type": "txt",
                "source_map": {"paragraphIndex": 1},
                "display_order": 1,
                "char_count": 18,
            }
        ],
        mappings=[
            {
                "document_id": "doc-1",
                "report_id": "report-1",
                "block_id": "b1",
                "span_id": "s1",
                "span_text": "随着系统持续发展",
                "risk_type": "aigc",
                "risk_level": "high",
                "aigc_score": 88.0,
                "match_method": "manual",
                "match_confidence": 1.0,
            }
        ],
    )
    settings = SimpleNamespace(
        feedback_learning_store_path=str(tmp_path / "learning.jsonl"),
        feedback_learning_skill_path=str(tmp_path / "skill" / "SKILL.md"),
    )

    saved, refreshed = documents._record_official_report_learning_if_allowed(
        repository=repo,
        settings=settings,
        document={"id": "doc-1", "subject": "cs", "degree_level": "本科"},
        report={
            "id": "report-1",
            "total_copy_ratio": 4.0,
            "aigc_ratio": 5.0,
            "generated_at": "2026-05-18",
            "parsed_at": "2026-05-18T10:00:00",
        },
        spans=[
            {
                "span_id": "s1",
                "text": "随着系统持续发展",
                "risk_type": "aigc",
                "risk_level": "high",
                "aigc_score": 88.0,
            }
        ],
        predicted_run_id=None,
        learning_consent=True,
    )

    assert saved is True
    assert refreshed is True
    assert "official-report-feedback-reducer" in (tmp_path / "skill" / "SKILL.md").read_text(encoding="utf-8")


def test_report_mode_rewrite_uses_official_risk_only() -> None:
    service = FakeRewriteService()
    repo = FakeReportRepository(
        blocks=[
            {
                "block_id": "b1",
                "block_type": "paragraph",
                "text": "本文通过系统设计提升财务管理效率。",
                "source_type": "txt",
                "source_map": {"paragraphIndex": 4},
                "display_order": 4,
                "char_count": 18,
                "section_title": "系统设计",
                "report_risk": {
                    "source": "cnki",
                    "risk_type": "similarity",
                    "risk_level": "high",
                    "similarity": 76.0,
                    "matched_source": "某篇相似论文",
                    "span_id": "span-1",
                    "match_confidence": 0.93,
                },
            }
        ],
        reports=[{"total_copy_ratio": 21.0, "aigc_ratio": 12.0}],
    )

    response = asyncio.run(
        documents._get_report_mode_rewrite_advice(
            run={
                "document_id": "doc-1",
                "subject": "软件工程",
                "degree_level": "本科",
            },
            run_id="run-report",
            section_index=4,
            repository=repo,
            llm_service=service,
        )
    )

    assert "官方查重/AIGC报告为准" in response.diagnosis
    assert service.kwargs is not None
    assert service.kwargs["risk_type"] == "duplication"
    assert service.kwargs["local_aigc_score"] is None
    assert service.kwargs["local_dup_score"] is None
    assert service.kwargs["cnki_dup_percent"] == 21.0
    assert service.kwargs["cnki_aigc_percent"] == 12.0


def test_report_mode_rewrite_ignores_unmarked_normal_block() -> None:
    repo = FakeReportRepository(
        blocks=[
            {
                "block_id": "b1",
                "block_type": "paragraph",
                "text": "官方报告没有标记的普通段落。",
                "source_type": "txt",
                "source_map": {"paragraphIndex": 3},
                "display_order": 3,
                "char_count": 14,
                "report_risk": None,
            }
        ]
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            documents._get_report_mode_rewrite_advice(
                run={"document_id": "doc-1"},
                run_id="run-report",
                section_index=3,
                repository=repo,
                llm_service=FakeRewriteService(),
            )
        )

    assert exc.value.status_code == 400
    assert "官方" in exc.value.detail
    assert "仅对官方标记片段" in exc.value.detail
