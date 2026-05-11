"""路由模块：将 API 端点按功能域拆分为独立的 Router。"""

from app.routes.auth import router as auth_router
from app.routes.billing import router as billing_router
from app.routes.documents import router as documents_router
from app.routes.providers import router as providers_router
from app.routes.feedback import router as feedback_router
from app.routes.models import router as models_router
from app.routes.legacy import router as legacy_router
from app.routes.unlocks import router as unlocks_router

__all__ = [
    "auth_router",
    "billing_router",
    "documents_router",
    "providers_router",
    "feedback_router",
    "models_router",
    "legacy_router",
    "unlocks_router",
]
