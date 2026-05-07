"""简单的速率限制中间件，基于内存计数器。

不依赖 slowapi/starlette.config，避免 .env 编码问题。
生产环境可替换为 Redis 后端。
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """基于 IP 的滑动窗口速率限制。"""

    def __init__(self, app, *, requests_per_minute: int = 120):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window = 60.0  # 1 minute
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _cleanup(self, now: float) -> None:
        """清理过期记录，防止内存无限增长（防御 DDoS 构造大量 IP）。"""
        cutoff = now - self.window
        # 只保留窗口内的记录
        for ip in list(self._requests.keys()):
            self._requests[ip] = [ts for ts in self._requests[ip] if ts > cutoff]
            if not self._requests[ip]:
                del self._requests[ip]
        # 限制总 IP 数量（超过 10000 时清理最旧的）
        if len(self._requests) > 10000:
            sorted_ips = sorted(
                self._requests.items(), key=lambda x: max(x[1]) if x[1] else 0
            )
            for ip, _ in sorted_ips[: len(sorted_ips) - 10000]:
                del self._requests[ip]

    async def dispatch(self, request: Request, call_next: Callable):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        self._cleanup(now)
        cutoff = now - self.window
        self._requests[client_ip] = [
            ts for ts in self._requests[client_ip] if ts > cutoff
        ]

        if len(self._requests[client_ip]) >= self.requests_per_minute:
            return JSONResponse(
                status_code=429,
                content={"detail": "请求过于频繁，请稍后重试"},
            )

        self._requests[client_ip].append(now)
        response = await call_next(request)
        return response


# 针对特定路径的更严格限制
class StrictRateLimitMiddleware(BaseHTTPMiddleware):
    """对认证端点施加更严格的限制（10/min）。"""

    STRICT_PATHS = {"/v1/auth/register", "/v1/auth/login"}

    def __init__(self, app, *, requests_per_minute: int = 10):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window = 60.0
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _cleanup(self, now: float) -> None:
        """清理过期记录，防止内存无限增长。"""
        cutoff = now - self.window
        for key in list(self._requests.keys()):
            self._requests[key] = [ts for ts in self._requests[key] if ts > cutoff]
            if not self._requests[key]:
                del self._requests[key]
        if len(self._requests) > 10000:
            sorted_keys = sorted(
                self._requests.items(), key=lambda x: max(x[1]) if x[1] else 0
            )
            for key, _ in sorted_keys[: len(sorted_keys) - 10000]:
                del self._requests[key]

    async def dispatch(self, request: Request, call_next: Callable):
        if request.url.path not in self.STRICT_PATHS:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"{client_ip}:{request.url.path}"
        now = time.time()

        self._cleanup(now)
        cutoff = now - self.window
        self._requests[key] = [ts for ts in self._requests[key] if ts > cutoff]

        if len(self._requests[key]) >= self.requests_per_minute:
            return JSONResponse(
                status_code=429,
                content={"detail": "请求过于频繁，请稍后重试"},
            )

        self._requests[key].append(now)
        response = await call_next(request)
        return response
