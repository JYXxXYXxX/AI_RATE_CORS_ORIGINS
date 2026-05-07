"""计费相关路由。"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.config import get_settings
from app.routes.deps import get_account_service, get_current_user
from app.schemas_unified import (
    BillingCallbackResponse,
    BillingOrderCreateRequest,
    BillingOrderDetailResponse,
    BillingOrderPaymentResponse,
    BillingSummaryResponse,
    MockCheckoutRequest,
    MockCheckoutResponse,
    MockPaymentCallbackRequest,
)
from app.services.account import AccountService

router = APIRouter(prefix="/v1/billing", tags=["billing"])


@router.get("/summary", response_model=BillingSummaryResponse)
def get_billing_summary(
    user: dict[str, Any] = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
) -> BillingSummaryResponse:
    try:
        summary = account_service.get_billing_summary(str(user["id"]))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return BillingSummaryResponse.model_validate(summary)


@router.post("/mock-checkout", response_model=MockCheckoutResponse)
def create_mock_checkout(
    payload: MockCheckoutRequest,
    user: dict[str, Any] = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
    settings=Depends(get_settings),
) -> MockCheckoutResponse:
    if not settings.mock_payment_enabled:
        raise HTTPException(status_code=404, detail="not found")
    try:
        result = account_service.mock_checkout(user_id=str(user["id"]), package_code=payload.package_code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MockCheckoutResponse.model_validate(result)


@router.post("/orders", response_model=BillingOrderDetailResponse)
def create_billing_order(
    payload: BillingOrderCreateRequest,
    user: dict[str, Any] = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
) -> BillingOrderDetailResponse:
    try:
        result = account_service.create_checkout_order(
            user_id=str(user["id"]),
            package_code=payload.package_code,
            provider=payload.provider,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return BillingOrderDetailResponse.model_validate(result)


@router.get("/orders/{order_no}", response_model=BillingOrderDetailResponse)
def get_billing_order_detail(
    order_no: str,
    user: dict[str, Any] = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
) -> BillingOrderDetailResponse:
    try:
        result = account_service.get_order_detail(user_id=str(user["id"]), order_no=order_no)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    return BillingOrderDetailResponse.model_validate(result)


@router.post("/orders/{order_no}/mock-pay", response_model=BillingOrderPaymentResponse)
def pay_billing_order_in_mock_mode(
    order_no: str,
    user: dict[str, Any] = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
    settings=Depends(get_settings),
) -> BillingOrderPaymentResponse:
    if not settings.mock_payment_enabled:
        raise HTTPException(status_code=404, detail="not found")
    try:
        result = account_service.pay_order(
            user_id=str(user["id"]),
            order_no=order_no,
            provider="mock_qr",
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    return BillingOrderPaymentResponse.model_validate(result)


@router.post("/callback/mock", response_model=BillingCallbackResponse)
def handle_mock_payment_callback(
    payload: MockPaymentCallbackRequest,
    account_service: AccountService = Depends(get_account_service),
    settings=Depends(get_settings),
) -> BillingCallbackResponse:
    if not settings.mock_payment_enabled:
        raise HTTPException(status_code=404, detail="not found")
    try:
        result = account_service.handle_mock_payment_callback(
            order_no=payload.order_no,
            paid_amount_cents=payload.paid_amount_cents,
            signature=payload.signature,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    return BillingCallbackResponse.model_validate(result)
