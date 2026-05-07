"""认证相关路由。"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.config import Settings, get_settings
from app.routes.deps import AuthContext, get_account_service, get_auth_context, get_current_user
from app.schemas_unified import AuthLoginRequest, AuthRegisterRequest, AuthSessionResponse, UserSummary
from app.services.account import AccountService

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/register", response_model=AuthSessionResponse)
def register_account(
    response: Response,
    payload: AuthRegisterRequest,
    account_service: AccountService = Depends(get_account_service),
) -> AuthSessionResponse:
    # 速率限制由全局 limiter 处理 (120/min)
    try:
        session = account_service.register(
            email=payload.email,
            password=payload.password,
            display_name=payload.display_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _set_session_cookie(response, session.token)
    return AuthSessionResponse(token=session.token, user=UserSummary.model_validate(session.user))


@router.post("/login", response_model=AuthSessionResponse)
def login_account(
    response: Response,
    payload: AuthLoginRequest,
    account_service: AccountService = Depends(get_account_service),
) -> AuthSessionResponse:
    try:
        session = account_service.login(email=payload.email, password=payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _set_session_cookie(response, session.token)
    return AuthSessionResponse(token=session.token, user=UserSummary.model_validate(session.user))


@router.get("/me", response_model=UserSummary)
def get_current_account(user: dict[str, Any] = Depends(get_current_user)) -> UserSummary:
    return UserSummary.model_validate(user)


@router.delete("/me")
def delete_current_account(
    response: Response,
    user: dict[str, Any] = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
) -> dict[str, bool]:
    """删除当前用户账户（GDPR/个人信息保护法删除权）。"""
    account_service.delete_account(str(user["id"]))
    _clear_session_cookie(response)
    return {"deleted": True}


@router.get("/me/export")
def export_current_account_data(
    user: dict[str, Any] = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service),
) -> dict[str, Any]:
    """导出当前用户全部个人数据（GDPR/个人信息保护法查阅权）。"""
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
