from __future__ import annotations

from typing import Any

from app.config import Settings
from app.payments.base import PaymentChannelSummary, PaymentIntent, PaymentOrderRequest, PaymentPackage


class AlipayPaymentProvider:
    code = "alipay"
    title = "支付宝"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def describe_channel(self) -> PaymentChannelSummary:
        ready = self._is_ready()
        return PaymentChannelSummary(
            code=self.code,
            title=self.title,
            description="面向正式上线预留的支付宝收银台通道。",
            enabled=True,
            ready=ready,
            mode="gateway" if ready else "placeholder",
        )

    def create_intent(self, order: PaymentOrderRequest) -> PaymentIntent:
        ready = self._is_ready()
        pay_hint = self._build_hint(order=order, ready=ready)
        payload = {
            "provider_label": self.title,
            "provider_ready": ready,
            "payment_url": None,
            "qr_content": None,
            "mock_pay_supported": False,
            "pay_hint": pay_hint,
            "mode": "gateway" if ready else "placeholder",
            "notify_url": self.settings.alipay_notify_url,
            "sandbox_enabled": self.settings.alipay_sandbox_enabled,
            "gateway_url": self.settings.alipay_gateway_url,
        }
        return PaymentIntent(
            provider=self.code,
            provider_label=self.title,
            provider_ready=ready,
            payment_url=None,
            qr_content=None,
            mock_pay_supported=False,
            pay_hint=pay_hint,
            payment_payload=payload,
        )

    def hydrate_order(self, order: dict[str, Any]) -> PaymentIntent:
        payload = order.get("payment_payload") if isinstance(order.get("payment_payload"), dict) else {}
        if payload:
            return PaymentIntent(
                provider=self.code,
                provider_label=str(payload.get("provider_label") or self.title),
                provider_ready=bool(payload.get("provider_ready", False)),
                payment_url=_optional_str(payload.get("payment_url")),
                qr_content=_optional_str(payload.get("qr_content")),
                mock_pay_supported=bool(payload.get("mock_pay_supported", False)),
                pay_hint=_optional_str(payload.get("pay_hint")),
                payment_payload=payload,
            )
        return self.create_intent(
            PaymentOrderRequest(
                order_no=str(order["order_no"]),
                user_id=str(order["user_id"]),
                package=PaymentPackage(
                    code=str(order["package_code"]),
                    title=str(order["package_code"]),
                    description="",
                    amount_cents=int(order["amount_cents"]),
                    credits=int(order["credits"]),
                ),
                public_base_url="",
            )
        )

    def _is_ready(self) -> bool:
        return bool(
            self.settings.alipay_app_id
            and self.settings.alipay_private_key_path
            and self.settings.alipay_public_key_path
        )

    def _build_hint(self, *, order: PaymentOrderRequest, ready: bool) -> str:
        amount = f"¥{order.package.amount_cents / 100:.2f}"
        if ready:
            return (
                f"支付宝订单 {order.order_no} 已创建，金额 {amount}。当前版本已经预留正式下单与回调接入位，"
                "补齐网关签名和下单请求后，这里会返回真实收银台链接或二维码。"
            )
        return (
            f"支付宝订单 {order.order_no} 已创建，金额 {amount}。当前环境尚未配置 app_id 与密钥，"
            "所以这里只保留占位链路，方便你先完成订单、额度和回填闭环联调。"
        )


def _optional_str(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)
