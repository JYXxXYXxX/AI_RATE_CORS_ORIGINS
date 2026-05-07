"""审计日志中间件，记录关键写入操作。"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.db.connection import get_connection_pool

logger = logging.getLogger(__name__)

# 需要记录审计日志的端点
_AUDITED_METHODS = {"POST", "PUT", "DELETE"}
_AUDITED_PATHS = {
    "/v1/auth/register",
    "/v1/auth/login",
    "/v1/auth/logout",
    "/v1/documents/upload",
    "/v1/cnki-feedback",
    "/v1/provider-results/manual",
    "/v1/provider-results/fetch",
    "/v1/billing/orders",
    "/v1/models/train-proxy",
}


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any):
        response = await call_next(request)

        if request.method not in _AUDITED_METHODS:
            return response

        path = request.url.path
        if not any(path.startswith(p) for p in _AUDITED_PATHS):
            return response

        # 异步记录审计日志（不阻塞响应）
        try:
            self._log_async(request, response.status_code)
        except Exception:
            logger.debug("Audit log skipped")

        return response

    def _log_async(self, request: Request, status_code: int) -> None:
        user_id = None
        try:
            auth = request.scope.get("auth_context")
            if auth and auth.user:
                user_id = str(auth.user["id"])
        except Exception:
            pass

        action = self._action_from_request(request)
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent")

        try:
            pool = get_connection_pool()
            with pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO audit_logs (user_id, action, resource_type, resource_id, ip_address, user_agent)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            user_id,
                            action,
                            "api",
                            request.url.path,
                            ip,
                            ua,
                        ),
                    )
                conn.commit()
        except Exception:
            pass

    def _action_from_request(self, request: Request) -> str:
        method = request.method
        path = request.url.path
        if path.startswith("/v1/auth/register"):
            return "register"
        if path.startswith("/v1/auth/login"):
            return "login"
        if path.startswith("/v1/auth/logout"):
            return "logout"
        if path.startswith("/v1/documents/upload"):
            return "document_upload"
        if path.startswith("/v1/cnki-feedback"):
            return "cnki_feedback"
        if path.startswith("/v1/provider-results"):
            return "provider_result"
        if path.startswith("/v1/billing/orders"):
            return "billing_order"
        if path.startswith("/v1/models/train-proxy"):
            return "model_train"
        return f"{method.lower()}_{path.replace('/', '_').strip('_')}"
