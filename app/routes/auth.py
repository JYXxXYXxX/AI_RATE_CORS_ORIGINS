"""Authentication routes."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response

from app.config import get_settings
from app.routes.deps import (
    AuthContext,
    get_account_service,
    get_auth_context,
    get_current_user,
)
from app.schemas_unified import (
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthResendVerificationRequest,
    AuthResendVerificationResponse,
    AuthSessionResponse,
    AuthVerifyEmailRequest,
    AuthVerifyEmailResponse,
    UserSummary,
)
from app.services.account import AccountService
from app.services.mailer import MailDeliveryError

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/register", response_model=AuthSessionResponse)
def register_account(
    response: Response,
    payload: AuthRegisterRequest,
    account_service: AccountService = Depends(get_account_service),
) -> AuthSessionResponse:
    try:
        result = account_service.register(
            email=payload.email,
            password=payload.password,
            display_name=payload.display_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MailDeliveryError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _auth_response(response, result)


@router.post("/login", response_model=AuthSessionResponse)
def login_account(
    response: Response,
    payload: AuthLoginRequest,
    account_service: AccountService = Depends(get_account_service),
) -> AuthSessionResponse:
    try:
        result = account_service.login(email=payload.email, password=payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MailDeliveryError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return _auth_response(response, result)


@router.post("/email/resend", response_model=AuthResendVerificationResponse)
def resend_verification_email(
    payload: AuthResendVerificationRequest,
    account_service: AccountService = Depends(get_account_service),
) -> AuthResendVerificationResponse:
    try:
        result = account_service.resend_verification_email(email=payload.email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MailDeliveryError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return AuthResendVerificationResponse(
        ok=True,
        email=result.email or payload.email,
        verification_sent=result.verification_sent,
        message=result.message,
        dev_verification_url=result.dev_verification_url,
    )


@router.post("/email/verify", response_model=AuthVerifyEmailResponse)
def verify_email(
    payload: AuthVerifyEmailRequest,
    account_service: AccountService = Depends(get_account_service),
) -> AuthVerifyEmailResponse:
    try:
        result = account_service.verify_email(token=payload.token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AuthVerifyEmailResponse(
        ok=True,
        email=result.email,
        already_verified=result.already_verified,
        message=result.message,
    )


@router.get("/me", response_model=UserSummary)
def get_current_account(
    user: dict[str, Any] = Depends(get_current_user),
) -> UserSummary:
    return UserSummary.model_validate(user)


@router.delete("/me")
def delete_current_account(
    response: Response,
    user: dict[str, Any] = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
) -> dict[str, bool]:
    account_service.delete_account(str(user["id"]))
    _clear_session_cookie(response)
    return {"deleted": True}


@router.get("/me/export")
def export_current_account_data(
    user: dict[str, Any] = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
) -> dict[str, Any]:
    return account_service.repository.export_user_data(str(user["id"]))


@router.post("/logout")
def logout_account(
    response: Response,
    auth: AuthContext = Depends(get_auth_context),
    account_service: AccountService = Depends(get_account_service),
) -> dict[str, bool]:
    account_service.logout(auth.token)
    _clear_session_cookie(response)
    return {"ok": True}


def _auth_response(response: Response, result: Any) -> AuthSessionResponse:
    if result.status == "authenticated" and result.token:
        _set_session_cookie(response, result.token)
    else:
        _clear_session_cookie(response)
    return AuthSessionResponse(
        status=result.status,
        token=result.token,
        user=UserSummary.model_validate(result.user) if result.user else None,
        requires_email_verification=result.status == "pending_verification",
        email=result.email,
        verification_sent=result.verification_sent,
        message=result.message,
        dev_verification_url=result.dev_verification_url,
    )


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.cookie_max_age_seconds,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key="session", path="/")

