from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from hmac import compare_digest
from pathlib import Path
from secrets import token_urlsafe
from typing import Any

from app.config import Settings
from app.db.repositories import UnifiedRepository
from app.payments.base import PaymentChannelSummary, PaymentOrderRequest, PaymentPackage
from app.payments.registry import PaymentProviderRegistry
from app.services.mailer import MailDeliveryError, send_email, smtp_configured


MOCK_PACKAGES: list[dict[str, Any]] = [
    {
        "code": "starter_5",
        "title": "预检 5 次包",
        "description": "适合首次送检前集中预检和一次复检。",
        "amount_cents": 990,
        "credits": 5,
    },
    {
        "code": "standard_15",
        "title": "预检 15 次包",
        "description": "适合毕业季连续改稿、复检和多版本对比。",
        "amount_cents": 2990,
        "credits": 15,
    },
    {
        "code": "pro_40",
        "title": "预检 40 次包",
        "description": "适合工作室、辅导团队或高频论文服务场景。",
        "amount_cents": 6990,
        "credits": 40,
    },
]


@dataclass(frozen=True)
class SessionIdentity:
    token: str
    user: dict[str, Any]


@dataclass(frozen=True)
class AuthOutcome:
    status: str
    token: str | None = None
    user: dict[str, Any] | None = None
    email: str | None = None
    verification_sent: bool = False
    message: str | None = None
    dev_verification_url: str | None = None


@dataclass(frozen=True)
class VerifyEmailOutcome:
    email: str
    already_verified: bool
    message: str


class AccountService:
    def __init__(self, settings: Settings, repository: UnifiedRepository) -> None:
        self.settings = settings
        self.repository = repository
        self.payment_registry = PaymentProviderRegistry(settings)

    def delete_account(self, user_id: str) -> bool:
        """删除用户账户（GDPR/个人信息保护法删除权）。"""
        user = self.repository.get_user(user_id)
        if user is None:
            raise ValueError("user not found")
        # 撤销所有会话
        self.repository.revoke_all_user_sessions(user_id)
        return self.repository.delete_user(user_id)

    def register(
        self, *, email: str, password: str, display_name: str | None
    ) -> AuthOutcome:
        normalized_email = _normalize_email(email)
        if self.repository.get_user_by_email(normalized_email) is not None:
            raise ValueError("email already registered")
        if len(password) < 6:
            raise ValueError("password must be at least 6 characters")

        user = self.repository.create_user(
            email=normalized_email,
            password_hash=hash_password(password),
            display_name=(display_name or "").strip()
            or _default_display_name(normalized_email),
            email_verified_at=(
                None if self.settings.email_verification_required else datetime.now(UTC)
            ),
        )
        if self.settings.email_verification_required:
            return self._build_pending_verification(user)
        self._grant_starter_credits_if_applicable(str(user["id"]))
        return self._create_authenticated_outcome(user)

    def login(self, *, email: str, password: str) -> AuthOutcome:
        normalized_email = _normalize_email(email)
        user = self.repository.get_user_by_email(normalized_email)
        if user is None or not verify_password(password, str(user["password_hash"])):
            raise ValueError("invalid email or password")
        if user.get("status") != "active":
            raise ValueError("account is not active")
        if self.settings.email_verification_required and not user.get(
            "email_verified_at"
        ):
            return self._build_pending_verification(user)
        return self._create_authenticated_outcome(user)

    def resend_verification_email(self, *, email: str) -> AuthOutcome:
        normalized_email = _normalize_email(email)
        user = self.repository.get_user_by_email(normalized_email)
        if user is None:
            raise ValueError("email not registered")
        if user.get("email_verified_at"):
            raise ValueError("email already verified")
        return self._build_pending_verification(user, enforce_cooldown=True)

    def verify_email(self, *, token: str) -> VerifyEmailOutcome:
        raw_token = (token or "").strip()
        if not raw_token:
            raise ValueError("verification token required")

        token_record = self.repository.get_email_verification_token(hash_token(raw_token))
        if token_record is None:
            raise ValueError("verification link is invalid or expired")

        if token_record.get("email_verified_at"):
            if token_record.get("used_at") is None:
                self.repository.mark_email_verification_token_used(
                    str(token_record["token_hash"]), datetime.now(UTC)
                )
            return VerifyEmailOutcome(
                email=str(token_record["email"]),
                already_verified=True,
                message="email already verified",
            )

        if token_record.get("used_at") is not None:
            return VerifyEmailOutcome(
                email=str(token_record["email"]),
                already_verified=True,
                message="email already verified",
            )

        expires_at = token_record.get("expires_at")
        if expires_at is None or expires_at <= datetime.now(UTC):
            raise ValueError("verification link expired, please request a new email")

        now = datetime.now(UTC)
        self.repository.mark_email_verification_token_used(
            str(token_record["token_hash"]), now
        )
        user = self.repository.mark_user_email_verified(
            str(token_record["user_id"]), now
        )
        self.repository.revoke_active_email_verification_tokens(
            str(token_record["user_id"])
        )
        self._grant_starter_credits_if_applicable(str(token_record["user_id"]))
        verified_user = user or self.repository.get_user(str(token_record["user_id"]))
        return VerifyEmailOutcome(
            email=str(verified_user["email"] if verified_user else token_record["email"]),
            already_verified=False,
            message="email verified successfully",
        )

    def get_user_by_token(self, token: str | None) -> dict[str, Any] | None:
        if not token:
            return None
        token_hash = hash_token(token)
        session = self.repository.get_user_session(token_hash)
        if session is None:
            return None
        self.repository.touch_user_session(token_hash)
        return {
            "id": str(session["user_id"]),
            "email": session["email"],
            "display_name": session.get("display_name"),
            "status": session.get("status"),
            "email_verified": bool(session.get("email_verified_at")),
            "email_verified_at": session.get("email_verified_at"),
            "credits_balance": int(session.get("credits_balance", 0)),
            "created_at": session.get("user_created_at"),
        }

    def logout(self, token: str | None) -> None:
        if token:
            self.repository.revoke_user_session(hash_token(token))

    def get_billing_summary(self, user_id: str) -> dict[str, Any]:
        user = self.repository.get_user(user_id)
        if user is None:
            raise ValueError("user not found")
        return {
            "user": _sanitize_user(user),
            "recent_orders": self.repository.list_user_orders(user_id, limit=8),
            "recent_ledger": self.repository.list_credit_ledger(user_id, limit=12),
            "recent_tasks": [
                {
                    "task_id": item["id"],
                    "document_id": item["document_id"],
                    "run_id": item.get("run_id"),
                    "title": item.get("title"),
                    "filename": item.get("filename"),
                    "status": item["status"],
                    "progress": int(item.get("progress", 0)),
                    "created_at": item["created_at"],
                    "finished_at": item.get("finished_at"),
                }
                for item in self.repository.list_user_analysis_tasks(user_id, limit=8)
            ],
            "packages": MOCK_PACKAGES,
            "payment_channels": [
                _serialize_payment_channel(item)
                for item in self.payment_registry.list_channels()
            ],
        }

    def create_checkout_order(
        self, *, user_id: str, package_code: str, provider: str
    ) -> dict[str, Any]:
        package = _get_package(package_code)
        if self.repository.get_user(user_id) is None:
            raise ValueError("user not found")

        order_no = _make_order_no()
        payment_intent = self.payment_registry.get(provider).create_intent(
            PaymentOrderRequest(
                order_no=order_no,
                user_id=user_id,
                package=PaymentPackage(
                    code=str(package["code"]),
                    title=str(package["title"]),
                    description=str(package["description"]),
                    amount_cents=int(package["amount_cents"]),
                    credits=int(package["credits"]),
                ),
                public_base_url=self.settings.payment_public_base_url.rstrip("/"),
            )
        )

        order = self.repository.create_billing_order(
            user_id=user_id,
            order_no=order_no,
            package_code=package["code"],
            credits=int(package["credits"]),
            amount_cents=int(package["amount_cents"]),
            status="pending",
            provider=payment_intent.provider,
            paid_at=None,
            payment_payload=payment_intent.payment_payload,
            provider_trade_no=None,
            notified_at=None,
        )
        return self._build_order_detail(order)

    def get_order_detail(self, *, user_id: str, order_no: str) -> dict[str, Any]:
        order = self.repository.get_user_billing_order(user_id, order_no)
        if order is None:
            raise ValueError("order not found")
        return self._build_order_detail(order)

    def pay_order(
        self, *, user_id: str, order_no: str, provider: str
    ) -> dict[str, Any]:
        order = self.repository.get_user_billing_order(user_id, order_no)
        if order is None:
            raise ValueError("order not found")
        if int(order["amount_cents"]) < 0:
            raise ValueError("invalid order amount")

        order_provider = str(order.get("provider") or "")
        try:
            order_provider = self.payment_registry.get(order_provider).code
        except ValueError:
            pass
        allowed_providers = {provider}
        if provider == "mock_qr":
            allowed_providers.add("mock_qr_callback")
            allowed_providers.add("mock")
        if order_provider and order_provider not in allowed_providers:
            raise ValueError("order provider does not support this payment action")

        result = self.repository.pay_billing_order_if_unpaid(
            order_no=order_no,
            provider=provider,
            note=f"{provider} payment for {order_no}",
        )
        return {
            "order": result["order"],
            "balance_after": result["balance_after"],
            "credited": bool(result["credited"]),
            "packages": MOCK_PACKAGES,
        }

    def handle_mock_payment_callback(
        self, *, order_no: str, paid_amount_cents: int, signature: str
    ) -> dict[str, Any]:
        order = self.repository.get_billing_order(order_no)
        if order is None:
            raise ValueError("order not found")

        expected_signature = self.build_mock_callback_signature(
            order_no=order_no,
            paid_amount_cents=paid_amount_cents,
        )
        if not compare_digest(signature, expected_signature):
            raise ValueError("invalid payment signature")

        expected_amount = int(order["amount_cents"])
        if expected_amount != int(paid_amount_cents):
            raise ValueError("paid amount mismatch")

        result = self.repository.pay_billing_order_if_unpaid(
            order_no=order_no,
            provider="mock_qr",
            note=f"mock callback payment for {order_no}",
            provider_trade_no=f"mock-callback-{order_no}",
            payment_payload={
                "callback_confirmed": True,
                "callback_amount_cents": int(paid_amount_cents),
                "callback_signature": signature,
            },
            notified_at=datetime.now(UTC),
        )
        return {
            "accepted": True,
            "order": result["order"],
            "balance_after": result["balance_after"],
            "credited": bool(result["credited"]),
        }

    def mock_checkout(self, *, user_id: str, package_code: str) -> dict[str, Any]:
        created = self.create_checkout_order(
            user_id=user_id, package_code=package_code, provider="mock_qr"
        )
        return self.pay_order(
            user_id=user_id, order_no=created["order"]["order_no"], provider="mock_qr"
        )

    def _create_session(self, user: dict[str, Any]) -> SessionIdentity:
        token = token_urlsafe(32)
        token_hash = hash_token(token)
        expires_at = datetime.now(UTC) + timedelta(
            hours=self.settings.auth_session_ttl_hours
        )
        self.repository.create_user_session(
            user_id=str(user["id"]),
            token_hash=token_hash,
            expires_at=expires_at,
        )
        refreshed_user = self.repository.get_user(str(user["id"])) or user
        return SessionIdentity(token=token, user=_sanitize_user(refreshed_user))

    def _create_authenticated_outcome(self, user: dict[str, Any]) -> AuthOutcome:
        session = self._create_session(user)
        return AuthOutcome(
            status="authenticated",
            token=session.token,
            user=session.user,
        )

    def _build_pending_verification(
        self, user: dict[str, Any], *, enforce_cooldown: bool = False
    ) -> AuthOutcome:
        verification_url = self._issue_email_verification(user, enforce_cooldown=enforce_cooldown)
        return AuthOutcome(
            status="pending_verification",
            email=str(user["email"]),
            verification_sent=True,
            message="please verify your email before signing in",
            dev_verification_url=verification_url
            if self.settings.service_env == "dev"
            else None,
        )

    def _issue_email_verification(
        self, user: dict[str, Any], *, enforce_cooldown: bool = False
    ) -> str | None:
        user_id = str(user["id"])
        now = datetime.now(UTC)
        last_sent_at = user.get("verification_email_sent_at")
        cooldown = max(0, int(self.settings.email_verification_resend_cooldown_seconds))
        if (
            enforce_cooldown
            and cooldown > 0
            and last_sent_at is not None
            and (now - last_sent_at).total_seconds() < cooldown
        ):
            raise ValueError(f"please wait {cooldown} seconds before requesting again")

        raw_token = token_urlsafe(32)
        token_hash = hash_token(raw_token)
        expires_at = now + timedelta(
            minutes=self.settings.email_verification_token_ttl_minutes
        )
        self.repository.revoke_active_email_verification_tokens(user_id)
        self.repository.create_email_verification_token(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.repository.update_user_verification_email_sent_at(user_id, now)

        verification_url = self._build_verification_url(raw_token)
        subject = "请验证你的 PataFix 邮箱"
        text_body = (
            f"你好，\n\n"
            f"请点击下面的链接完成邮箱验证：\n{verification_url}\n\n"
            f"该链接将在 {self.settings.email_verification_token_ttl_minutes} 分钟后失效。"
        )
        html_body = (
            "<div style=\"font-family:Arial,'PingFang SC','Microsoft YaHei',sans-serif;"
            "line-height:1.7;color:#172033\">"
            "<h2 style=\"margin:0 0 12px\">验证你的 PataFix 邮箱</h2>"
            "<p>请点击下面的按钮完成邮箱验证，验证后才能正常使用邮箱登录。</p>"
            f"<p><a href=\"{verification_url}\" "
            "style=\"display:inline-block;padding:12px 18px;border-radius:10px;"
            "background:#0f8f4f;color:#fff;text-decoration:none;font-weight:700\">"
            "立即验证邮箱</a></p>"
            f"<p>如果按钮无法打开，也可以复制这个链接：<br>{verification_url}</p>"
            f"<p>链接有效期：{self.settings.email_verification_token_ttl_minutes} 分钟。</p>"
            "</div>"
        )

        if smtp_configured(self.settings):
            send_email(
                settings=self.settings,
                to_email=str(user["email"]),
                subject=subject,
                text_body=text_body,
                html_body=html_body,
            )
            return None

        if self.settings.service_env == "dev":
            Path("data").mkdir(exist_ok=True)
            preview_path = Path("data") / "last_email_verification_link.txt"
            preview_path.write_text(verification_url, encoding="utf-8")
            return verification_url

        raise MailDeliveryError("smtp not configured")

    def _build_verification_url(self, raw_token: str) -> str:
        base = self.settings.public_web_base_url.rstrip("/")
        return f"{base}/email-verification/complete?token={raw_token}"

    def _grant_starter_credits_if_applicable(self, user_id: str) -> None:
        if self.settings.starter_credits <= 0:
            return
        user = self.repository.get_user(user_id)
        if user is None:
            return
        if int(user.get("credits_balance", 0)) > 0:
            return
        self.repository.change_user_credits(
            user_id=user_id,
            delta=self.settings.starter_credits,
            source_type="starter_bonus",
            source_id=None,
            note="starter credits",
        )

    def _build_order_detail(self, order: dict[str, Any]) -> dict[str, Any]:
        order_summary = _serialize_order(order)
        intent = self.payment_registry.hydrate_order(order)
        is_pending = str(order.get("status") or "") in {"pending", "created"}
        mock_supported = bool(intent.mock_pay_supported and is_pending)
        return {
            "order": order_summary,
            "payment_url": intent.payment_url if is_pending else None,
            "qr_content": intent.qr_content if is_pending else None,
            "mock_pay_supported": mock_supported,
            "pay_hint": intent.pay_hint,
            "provider_label": intent.provider_label,
            "provider_ready": intent.provider_ready,
        }

    def build_mock_callback_signature(
        self, *, order_no: str, paid_amount_cents: int
    ) -> str:
        import hmac as _hmac

        message = f"{order_no}:{paid_amount_cents}".encode("utf-8")
        key = self.settings.payment_callback_secret.encode("utf-8")
        return _hmac.new(key, message, "sha256").hexdigest()


def hash_password(password: str) -> str:
    from base64 import urlsafe_b64encode
    from hashlib import pbkdf2_hmac
    from os import urandom

    salt = urandom(16)
    iterations = 120_000
    digest = pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return (
        "pbkdf2_sha256"
        f"${iterations}"
        f"${urlsafe_b64encode(salt).decode('ascii')}"
        f"${urlsafe_b64encode(digest).decode('ascii')}"
    )


def verify_password(password: str, encoded: str) -> bool:
    from base64 import urlsafe_b64decode
    from hashlib import pbkdf2_hmac
    from hmac import compare_digest

    try:
        algorithm, iterations, salt_value, digest_value = encoded.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    digest = pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        urlsafe_b64decode(salt_value.encode("ascii")),
        int(iterations),
    )
    return compare_digest(digest, urlsafe_b64decode(digest_value.encode("ascii")))


def hash_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def _normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", normalized):
        raise ValueError("invalid email")
    return normalized


def _default_display_name(email: str) -> str:
    return email.split("@", 1)[0]


def _get_package(package_code: str) -> dict[str, Any]:
    package = next(
        (item for item in MOCK_PACKAGES if item["code"] == package_code), None
    )
    if package is None:
        raise ValueError("package not found")
    return package


def _make_order_no() -> str:
    return f"ORD-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"


def _serialize_order(order: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(order["id"]),
        "order_no": order["order_no"],
        "package_code": order["package_code"],
        "credits": int(order["credits"]),
        "amount_cents": int(order["amount_cents"]),
        "status": order["status"],
        "provider": order["provider"],
        "created_at": order["created_at"],
        "paid_at": order.get("paid_at"),
    }


def _serialize_payment_channel(channel: PaymentChannelSummary) -> dict[str, Any]:
    return {
        "code": channel.code,
        "title": channel.title,
        "description": channel.description,
        "enabled": channel.enabled,
        "ready": channel.ready,
        "mode": channel.mode,
    }


def _sanitize_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(user["id"]),
        "email": user["email"],
        "display_name": user.get("display_name"),
        "status": user.get("status"),
        "email_verified": bool(user.get("email_verified_at")),
        "email_verified_at": user.get("email_verified_at"),
        "credits_balance": int(user.get("credits_balance", 0)),
        "created_at": user.get("created_at"),
    }
