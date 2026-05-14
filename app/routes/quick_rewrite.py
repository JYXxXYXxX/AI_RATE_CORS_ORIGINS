"""Landing-page quick rewrite endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from app.schemas_unified import (
    QuickRewritePhrase,
    QuickRewriteRequest,
    QuickRewriteResult,
    QuickRewriteRisk,
)
from app.services.quick_rewrite import quick_rewrite


router = APIRouter(tags=["quick-rewrite"])

@router.post("/api/quick-rewrite", response_model=QuickRewriteResult)
def create_quick_rewrite(
    payload: QuickRewriteRequest,
) -> QuickRewriteResult:
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="请输入需要检测的论文内容")

    result = quick_rewrite(text, payload.mode)
    return QuickRewriteResult(
        originalText=result.original_text,
        rewrittenText=result.rewritten_text,
        beforeRisk=QuickRewriteRisk(
            score=result.before_score,
            level=result.before_level,
        ),
        afterRisk=QuickRewriteRisk(
            score=result.after_score,
            level=result.after_level,
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
        improvedPhrases=[
            QuickRewritePhrase(
                text=item.text,
                reason=item.reason,
                start=item.start,
                end=item.end,
            )
            for item in result.improved_phrases
        ],
        rewritePrinciples=result.rewrite_principles,
        summary=result.summary,
        recommendedMode=result.recommended_mode,
        remainingFreeUses=None,
    )
