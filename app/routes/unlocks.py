"""运行解锁订单路由（私域付款 + 人工确认）。"""

from __future__ import annotations

import os
import random
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)

from app.config import Settings, get_settings
from app.db import get_repository
from app.routes.admin import require_admin
from app.routes.deps import get_auth_context, get_current_user
from app.schemas_unified import (
    AdminUnlockOrderListResponse,
    UnlockOrderResponse,
    UnlockPackage,
    UnlockStatusResponse,
)

router = APIRouter(prefix="/v1/unlocks", tags=["unlocks"])

# ---------------------------------------------------------------------------
# 解锁套餐配置
# ---------------------------------------------------------------------------
UNLOCK_PACKAGES: list[UnlockPackage] = [
    UnlockPackage(
        code="unlock_report",
        title="解锁全文检测报告",
        description="查看完整风险分析、章节热力图、导师批注建议、修改计划等详细报告内容",
        amount_cents=2990,
        amount_yuan="29.90",
    ),
    UnlockPackage(
        code="unlock_rewrite",
        title="解锁全文改写建议",
        description="查看全部段落的 AI 改写建议和句子级润色卡片，支持在线对比修改",
        amount_cents=3990,
        amount_yuan="39.90",
    ),
    UnlockPackage(
        code="export_docx",
        title="导出改写稿",
        description="将已改写的段落合并为完整文档，保留原格式，直接下载 DOCX 文件",
        amount_cents=1990,
        amount_yuan="19.90",
    ),
]

_PACKAGE_MAP = {p.code: p for p in UNLOCK_PACKAGES}


def _generate_order_no() -> str:
    now = datetime.now(UTC)
    rand = random.randint(10, 99)
    return f"PF{now.strftime('%Y%m%d%H%M')}{rand}"


def _ensure_screenshots_dir(settings: Settings) -> Path:
    screenshots_dir = Path(settings.upload_storage_dir) / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    return screenshots_dir


def _screenshot_public_url(settings: Settings, filename: str) -> str:
    base = settings.payment_public_base_url.rstrip("/")
    return f"{base}/v1/unlocks/screenshots/{filename}"


# ---------------------------------------------------------------------------
# 用户端接口
# ---------------------------------------------------------------------------

@router.get("/packages", response_model=list[UnlockPackage])
def list_unlock_packages() -> list[UnlockPackage]:
    return UNLOCK_PACKAGES


@router.post("/runs/{run_id}/orders", response_model=UnlockOrderResponse)
def create_unlock_order(
    run_id: str,
    package_code: str = Form(...),
    user: dict[str, Any] = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> UnlockOrderResponse:
    pkg = _PACKAGE_MAP.get(package_code)
    if not pkg:
        raise HTTPException(status_code=400, detail="invalid package code")

    repo = get_repository()
    # 检查是否已有有效解锁记录
    existing = repo.get_run_unlock(str(user["id"]), run_id, package_code)
    if existing and existing.get("status") == "unlocked":
        return UnlockOrderResponse.model_validate(existing)

    order_no = _generate_order_no()
    # 避免 order_no 冲突时重试一次
    for _ in range(3):
        dup = repo.get_run_unlock_by_order_no(order_no)
        if not dup:
            break
        order_no = _generate_order_no()

    record = repo.create_run_unlock(
        user_id=str(user["id"]),
        run_id=run_id,
        order_no=order_no,
        package_code=package_code,
        amount_cents=pkg.amount_cents,
    )
    if not record:
        raise HTTPException(status_code=500, detail="failed to create unlock order")
    return UnlockOrderResponse.model_validate(record)


@router.get("/runs/{run_id}/status", response_model=UnlockStatusResponse)
def get_unlock_status(
    run_id: str,
    package_code: str | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> UnlockStatusResponse:
    repo = get_repository()
    if package_code:
        order = repo.get_run_unlock(str(user["id"]), run_id, package_code)
        if order and order.get("status") == "unlocked":
            return UnlockStatusResponse(
                unlocked=True,
                order=UnlockOrderResponse.model_validate(order),
                package_code=package_code,
            )
        return UnlockStatusResponse(
            unlocked=False,
            order=UnlockOrderResponse.model_validate(order) if order else None,
            package_code=package_code,
        )

    # 未指定 package_code 时，返回所有该 run 的解锁记录
    orders = repo.list_run_unlocks_by_user(str(user["id"]), run_id)
    unlocked = [o for o in orders if o.get("status") == "unlocked"]
    latest = orders[0] if orders else None
    return UnlockStatusResponse(
        unlocked=len(unlocked) > 0,
        order=UnlockOrderResponse.model_validate(latest) if latest else None,
        package_code=None,
    )


@router.post("/runs/{run_id}/orders/{order_no}/screenshot", response_model=UnlockOrderResponse)
async def upload_payment_screenshot(
    run_id: str,
    order_no: str,
    payment_method: str = Form(...),
    screenshot: UploadFile = File(...),
    user: dict[str, Any] = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> UnlockOrderResponse:
    if payment_method not in ("alipay", "wechat"):
        raise HTTPException(status_code=400, detail="payment_method must be alipay or wechat")

    repo = get_repository()
    order = repo.get_run_unlock_by_order_no(order_no)
    if not order:
        raise HTTPException(status_code=404, detail="order not found")
    if str(order["user_id"]) != str(user["id"]):
        raise HTTPException(status_code=403, detail="order access denied")
    if str(order["run_id"]) != run_id:
        raise HTTPException(status_code=400, detail="run_id mismatch")
    if order["status"] not in ("pending_payment", "rejected"):
        raise HTTPException(status_code=400, detail=f"cannot upload screenshot for status {order['status']}")

    # 保存截图文件
    ext = Path(screenshot.filename or "screenshot.png").suffix
    if ext.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
        ext = ".png"
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    filename = f"{order_no}_{timestamp}{ext}"
    screenshots_dir = _ensure_screenshots_dir(settings)
    file_path = screenshots_dir / filename

    try:
        with file_path.open("wb") as f:
            shutil.copyfileobj(screenshot.file, f)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"failed to save screenshot: {exc}") from exc
    finally:
        screenshot.file.close()

    screenshot_url = _screenshot_public_url(settings, filename)
    updated = repo.update_run_unlock_screenshot(
        order_no=order_no,
        payment_method=payment_method,
        screenshot_path=str(file_path),
        screenshot_url=screenshot_url,
    )
    if not updated:
        raise HTTPException(status_code=500, detail="failed to update order")
    return UnlockOrderResponse.model_validate(updated)


# ---------------------------------------------------------------------------
# 管理员接口
# ---------------------------------------------------------------------------

@router.get("/admin/orders", response_model=AdminUnlockOrderListResponse)
def admin_list_unlock_orders(
    request: Request,
    status: str | None = None,
    limit: int = 100,
) -> AdminUnlockOrderListResponse:
    require_admin(request)
    repo = get_repository()
    if status:
        # 按状态过滤
        all_orders = repo.list_pending_run_unlocks(limit=limit * 2)
        orders = [o for o in all_orders if o.get("status") == status][:limit]
    else:
        orders = repo.list_pending_run_unlocks(limit=limit)
    return AdminUnlockOrderListResponse(
        orders=[UnlockOrderResponse.model_validate(o) for o in orders],
        total=len(orders),
    )


@router.post("/admin/orders/{order_no}/approve", response_model=UnlockOrderResponse)
def admin_approve_unlock_order(
    order_no: str,
    request: Request,
) -> UnlockOrderResponse:
    require_admin(request)
    repo = get_repository()
    order = repo.get_run_unlock_by_order_no(order_no)
    if not order:
        raise HTTPException(status_code=404, detail="order not found")
    if order["status"] not in ("pending_payment", "pending_review"):
        raise HTTPException(status_code=400, detail=f"cannot approve order with status {order['status']}")

    token = request.headers.get("X-Admin-Token", "")
    if not token and request.headers.get("Authorization", "").lower().startswith("bearer "):
        token = request.headers.get("Authorization", "")[7:].strip()
    reviewed_by = token[:50] if token else "admin"

    updated = repo.approve_run_unlock(order_no, reviewed_by)
    if not updated:
        raise HTTPException(status_code=500, detail="failed to approve order")
    return UnlockOrderResponse.model_validate(updated)


@router.post("/admin/orders/{order_no}/reject", response_model=UnlockOrderResponse)
def admin_reject_unlock_order(
    order_no: str,
    request: Request,
) -> UnlockOrderResponse:
    require_admin(request)
    repo = get_repository()
    order = repo.get_run_unlock_by_order_no(order_no)
    if not order:
        raise HTTPException(status_code=404, detail="order not found")
    if order["status"] not in ("pending_payment", "pending_review"):
        raise HTTPException(status_code=400, detail=f"cannot reject order with status {order['status']}")

    token = request.headers.get("X-Admin-Token", "")
    if not token and request.headers.get("Authorization", "").lower().startswith("bearer "):
        token = request.headers.get("Authorization", "")[7:].strip()
    reviewed_by = token[:50] if token else "admin"

    updated = repo.reject_run_unlock(order_no, reviewed_by)
    if not updated:
        raise HTTPException(status_code=500, detail="failed to reject order")
    return UnlockOrderResponse.model_validate(updated)
