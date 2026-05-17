from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from app.routes import documents
from app.routes.deps import AuthContext
from app.schemas_unified import ReanalyzeRequest


class FakeReportRepository:
    def __init__(self, *, blocks: list[dict] | None = None, reports: list[dict] | None = None):
        self.blocks = blocks or []
        self.reports = reports or []

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

    def list_cnki_reports_by_document(self, document_id: str) -> list[dict]:
        return self.reports


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
