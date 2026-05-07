"""管理员认证依赖。

简单实现：通过环境变量 AI_RATE_ADMIN_TOKEN 配置管理员令牌。
生产环境应替换为 RBAC 权限系统。
"""
from __future__ import annotations

import os

from fastapi import Depends, HTTPException, Request


def get_admin_token() -> str | None:
    return os.environ.get("AI_RATE_ADMIN_TOKEN")


def require_admin(request: Request) -> None:
    """要求请求携带有效的管理员令牌。

    通过 Header `X-Admin-Token` 或 `Authorization: Bearer <token>` 传递。
    未配置 AI_RATE_ADMIN_TOKEN 时返回 403（失败关闭）。
    """
    expected = get_admin_token()
    if not expected:
        raise HTTPException(status_code=403, detail="admin authentication not configured")

    authorization = request.headers.get("Authorization", "")
    admin_header = request.headers.get("X-Admin-Token", "")

    token = ""
    if admin_header:
        token = admin_header.strip()
    elif authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()

    if not token or token != expected:
        raise HTTPException(status_code=403, detail="admin authentication required")
