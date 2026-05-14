"""Landing-page quick rewrite endpoint."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.db import get_repository
from app.routes.deps import AuthContext, get_auth_context
from app.schemas_unified import (
    QuickRewritePhrase,
    QuickRewriteRequest,
    QuickRewriteResult,
    QuickRewriteRisk,
)
from app.services.quick_rewrite import quick_rewrite


router = APIRouter(tags=["quick-rewrite"])

FREE_DAILY_LIMIT = 3
FREE_MAX_CHARS = 300
PAID_MAX_CHARS = 3000

_usage_by_day: dict[str, tuple[str, int]] = {}


@router.post("/api/quick-rewrite", response_model=QuickRewriteResult)
def create_quick_rewrite(
    payload: QuickRewriteRequest,
    request: Request,
    auth: AuthContext = Depends(get_auth_context),
) -> QuickRewriteResult:
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="请输入需要检测的论文内容")

    is_paid = _is_paid_user(auth.user)
    max_chars = PAID_MAX_CHARS if is_paid else FREE_MAX_CHARS
    if len(text) > max_chars:
        raise HTTPException(
            status_code=400,
            detail=(
                f"免费试用每次最多 {FREE_MAX_CHARS} 字，付费用户可提交更长文本。"
                if not is_paid
                else f"单次短句优化最多支持 {PAID_MAX_CHARS} 字"
            ),
        )

    remaining = None
    if not is_paid:
        remaining = _consume_free_use(_usage_key(request, auth))

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
        remainingFreeUses=remaining,
    )


def _usage_key(request: Request, auth: AuthContext) -> str:
    if auth.user is not None:
        return f"user:{auth.user['id']}"
    client_ip = request.client.host if request.client else "unknown"
    return f"ip:{client_ip}"


def _consume_free_use(key: str) -> int:
    today = datetime.now(UTC).date().isoformat()
    usage_day, count = _usage_by_day.get(key, (today, 0))
    if usage_day != today:
        count = 0
        usage_day = today
    if count >= FREE_DAILY_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="免费用户每天可试用 3 次，请明天再试或上传全文继续检测。",
        )
    count += 1
    _usage_by_day[key] = (usage_day, count)
    return max(0, FREE_DAILY_LIMIT - count)


def _is_paid_user(user: dict[str, Any] | None) -> bool:
    if user is None:
        return False
    try:
        orders = get_repository().list_user_orders(str(user["id"]), limit=20)
    except Exception:
        return False
    return any(
        order.get("status") == "paid" and int(order.get("amount_cents") or 0) > 0
        for order in orders
    )
