import json
import logging
import os
import signal
import sys
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.config import Settings, get_settings
from app.db import close_connection_pool
from app.middleware import RateLimitMiddleware, StrictRateLimitMiddleware
from app.middleware.audit_log import AuditLogMiddleware
from app.routes import (
    auth_router,
    billing_router,
    documents_router,
    feedback_router,
    legacy_router,
    models_router,
    providers_router,
)


# ---------------------------------------------------------------------------
# 日志配置（生产环境支持 JSON 格式）
# ---------------------------------------------------------------------------
class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


_log_format = os.environ.get("LOG_FORMAT", "text")
if _log_format.lower() == "json":
    _formatter: logging.Formatter = _JsonFormatter()
else:
    _formatter = logging.Formatter(
        "%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(_formatter)
logging.basicConfig(level=logging.INFO, handlers=[_handler])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 信号处理：记录优雅关闭
# ---------------------------------------------------------------------------
_shutdown_event = threading.Event()


def _handle_signal(signum: int, _frame: Any) -> None:
    sig_name = signal.Signals(signum).name
    logger.info("Received %s, initiating graceful shutdown...", sig_name)
    _shutdown_event.set()


try:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
except ValueError:
    # 在某些线程上下文中无法设置信号
    pass


# ---------------------------------------------------------------------------
# 应用生命周期
# ---------------------------------------------------------------------------
def _start_cleanup_thread(settings: Settings):
    """启动后台数据清理线程。"""
    import threading

    def _cleanup_loop():
        from app.services.cleanup import run_data_cleanup

        while not _shutdown_event.is_set():
            _shutdown_event.wait(timeout=3600 * 6)  # 每 6 小时执行一次
            if not _shutdown_event.is_set():
                try:
                    run_data_cleanup(settings)
                except Exception as exc:
                    logger.warning("Background cleanup failed: %s", exc)

    t = threading.Thread(target=_cleanup_loop, daemon=True, name="cleanup")
    t.start()
    return t


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    logger.info("Starting %s v%s", settings.service_name, settings.service_version)
    # 启动安全校验
    if not settings.payment_callback_secret:
        logger.error(
            "PAYMENT_CALLBACK_SECRET is not set. Mock/Prod billing endpoints disabled."
        )
    if settings.cors_origins == "*" and settings.service_env != "dev":
        logger.warning(
            "CORS_ORIGINS is wildcard in non-dev environment. This is insecure."
        )
    # 恢复因进程崩溃而卡在 processing 的任务
    try:
        from app.db import get_repository

        repo = get_repository()
        recovered = repo.recover_stale_tasks(max_age_minutes=30)
        if recovered:
            logger.warning("Recovered %d stale analysis tasks", recovered)
    except Exception:
        logger.debug("Task recovery skipped (DB may not be ready)")
    # 启动数据清理后台线程
    _start_cleanup_thread(settings)
    yield
    close_connection_pool()
    logger.info("Shutdown complete")


# ---------------------------------------------------------------------------
# FastAPI 实例
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AI Rate Detector Service",
    version="0.3.0",
    description="中文论文 AIGC 疑似风险与知网区间预测服务。",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def _generic_exception_handler(_request, exc):
    """全局兜底：生产环境绝不暴露内部异常详情给客户端。"""
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "internal server error"},
    )


# ---------------------------------------------------------------------------
# 中间件（注册顺序：后注册先执行）
# ---------------------------------------------------------------------------
settings = get_settings()

# CORS
cors_origins = getattr(settings, "cors_origins", "*")
if isinstance(cors_origins, str):
    cors_origins = [o.strip() for o in cors_origins.split(",") if o.strip()]

# 开发模式下若未配置 origins，自动加入常用本地地址，避免空列表阻断跨域
if not cors_origins and settings.service_env == "dev":
    cors_origins = [
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 审计日志
app.add_middleware(AuditLogMiddleware)

# 速率限制：全局 120/min，认证端点 10/min
app.add_middleware(RateLimitMiddleware, requests_per_minute=120)
app.add_middleware(StrictRateLimitMiddleware, requests_per_minute=10)

# ---------------------------------------------------------------------------
# 注册路由
# ---------------------------------------------------------------------------
app.include_router(auth_router)
app.include_router(billing_router)
app.include_router(documents_router)
app.include_router(providers_router)
app.include_router(feedback_router)
app.include_router(models_router)
app.include_router(legacy_router)


# ---------------------------------------------------------------------------
# 监控与探针
# ---------------------------------------------------------------------------
@app.get("/health", include_in_schema=False)
async def health_check() -> JSONResponse:
    """健康探针：验证数据库连接、关键目录权限等。"""
    from app.db import get_repository

    status: dict[str, Any] = {
        "status": "ok",
        "database": "unknown",
        "version": get_settings().service_version,
    }
    http_status = 200

    try:
        repo = get_repository()
        repo.health_check()
        status["database"] = "connected"
    except Exception as exc:
        status["status"] = "degraded"
        status["database"] = f"unavailable: {exc}"
        http_status = 503

    # 检查上传目录可写
    try:
        upload_dir = Path(get_settings().upload_storage_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        test_file = upload_dir / ".health_check_write"
        test_file.write_text("ok")
        test_file.unlink()
    except Exception as exc:
        status["status"] = "degraded"
        status["storage"] = f"unavailable: {exc}"
        http_status = 503

    return JSONResponse(content=status, status_code=http_status)


@app.get("/metrics", include_in_schema=False)
async def metrics() -> PlainTextResponse:
    return PlainTextResponse(
        content=generate_latest().decode("utf-8"), media_type=CONTENT_TYPE_LATEST
    )


# ---------------------------------------------------------------------------
# 前端静态文件托管
# ---------------------------------------------------------------------------
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if FRONTEND_DIST.is_dir():
    # 静态资源（JS/CSS/图片等）
    app.mount(
        "/assets",
        StaticFiles(directory=str(FRONTEND_DIST / "assets")),
        name="frontend-assets",
    )

    # SPA fallback: 所有非 API 路径返回 index.html
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(request: Request, full_path: str):
        # API 路径不走这里（已被上面的 router 匹配）
        file_path = FRONTEND_DIST / full_path
        if full_path and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(FRONTEND_DIST / "index.html"))

    logger.info("Frontend served from %s", FRONTEND_DIST)
else:
    logger.warning("Frontend dist not found at %s, SPA not served", FRONTEND_DIST)


# ---------------------------------------------------------------------------
# 向后兼容导入（测试文件中 from app.main import get_calibrator, get_job_store）
# ---------------------------------------------------------------------------
from app.routes.deps import get_calibrator, get_job_store  # noqa: E402, F401
