from __future__ import annotations

from typing import Any

from app.db.repositories import UnifiedRepository


class ManualProviderImportService:
    def __init__(self, repository: UnifiedRepository) -> None:
        self.repository = repository

    def import_result(
        self,
        *,
        document_id: str,
        run_id: str,
        provider: str,
        duplication_percent: float | None,
        aigc_percent: float | None,
        confidence: float | None,
        version: str | None,
        notes: str | None,
        raw_payload: dict[str, Any],
    ) -> dict[str, Any]:
        if duplication_percent is None and aigc_percent is None:
            raise ValueError("duplication_percent or aigc_percent is required")
        if confidence is not None and not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")

        document = self.repository.get_document(document_id)
        if document is None:
            raise ValueError("document not found")
        run = self.repository.get_run(run_id)
        if run is None:
            raise ValueError("run not found")
        if str(run["document_id"]) != document_id:
            raise ValueError("run does not belong to the document")

        normalized = {
            "document_id": document_id,
            "run_id": run_id,
            "provider": provider,
            "duplication_percent": duplication_percent,
            "duplication_rate": round(duplication_percent / 100, 6)
            if duplication_percent is not None
            else None,
            "aigc_percent": aigc_percent,
            "aigc_rate": round(aigc_percent / 100, 6)
            if aigc_percent is not None
            else None,
            "confidence": confidence,
            "version": version,
            "notes": notes,
            "raw_payload": raw_payload,
        }
        payload = self.repository.insert_provider_payload_row(
            run_id, provider, "normalized", normalized
        )
        return {"payload": payload, "normalized": normalized}
