"""Landing-page quick rewrite endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from app.routes.deps import get_llm_rewrite_service
from app.schemas_unified import (
    QuickRewritePhrase,
    QuickRewriteRequest,
    QuickRewriteResult,
    QuickRewriteRisk,
)
from app.services.quick_rewrite import quick_rewrite


router = APIRouter(tags=["quick-rewrite"])


def _safe_after_score(original_before_score: int, candidate_after_score: int) -> int:
    ceiling = max(0, original_before_score - 1)
    return max(0, min(candidate_after_score, ceiling))


def _risk_level(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 42:
        return "medium"
    if score >= 20:
        return "low"
    return "normal"


@router.post("/api/quick-rewrite", response_model=QuickRewriteResult)
async def create_quick_rewrite(
    payload: QuickRewriteRequest,
    llm_service=Depends(get_llm_rewrite_service),
) -> QuickRewriteResult:
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="请输入需要检测的论文内容")

    result = quick_rewrite(text, payload.mode)
    rewritten_text = result.rewritten_text
    after_score = _safe_after_score(result.before_score, result.after_score)
    improved_phrases = [
        QuickRewritePhrase(
            text=item.text,
            reason=item.reason,
            start=item.start,
            end=item.end,
        )
        for item in result.improved_phrases
    ]
    summary = result.summary

    if getattr(llm_service, "enabled", False):
        requested_mode = (
            result.recommended_mode if payload.mode == "auto" else payload.mode
        )
        risk_type = {
            "aigc": "aigc",
            "similarity": "duplication",
            "polish": "mixed",
            "auto": "mixed",
        }.get(requested_mode, "mixed")
        llm_result = await llm_service.rewrite_paragraph(
            text=text,
            risk_type=risk_type,
            reasons=[item.reason for item in result.risky_phrases[:4]],
        )
        candidate = str(llm_result.get("rewritten_paragraph") or "").strip()
        if candidate and candidate != text:
            rewritten_text = candidate
            rescored = quick_rewrite(candidate, requested_mode)
            after_score = _safe_after_score(result.before_score, rescored.after_score)
            summary = str(llm_result.get("diagnosis") or summary).strip() or summary
            improved_phrases = [
                QuickRewritePhrase(
                    text=str(item.get("rewritten") or "").strip(),
                    reason=str(item.get("explanation") or "").strip(),
                    start=None,
                    end=None,
                )
                for item in llm_result.get("sentences", [])
                if isinstance(item, dict) and str(item.get("rewritten") or "").strip()
            ] or improved_phrases

    after_level = _risk_level(after_score)

    return QuickRewriteResult(
        originalText=result.original_text,
        rewrittenText=rewritten_text,
        beforeRisk=QuickRewriteRisk(
            score=result.before_score,
            level=result.before_level,
        ),
        afterRisk=QuickRewriteRisk(
            score=after_score,
            level=after_level,
        ),
        riskyPhrases=[
            QuickRewritePhrase(
                text=item.text,
                reason=item.reason,
                start=item.start,
                end=item.end,
            )
            for item in result.risky_phrases
        ],
        improvedPhrases=improved_phrases,
        rewritePrinciples=result.rewrite_principles,
        summary=summary,
        recommendedMode=result.recommended_mode,
        remainingFreeUses=None,
    )
