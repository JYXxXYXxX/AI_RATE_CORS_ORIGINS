from __future__ import annotations

from typing import Any

from app.payments.base import PaymentChannelSummary, PaymentIntent, PaymentOrderRequest, PaymentPackage


class MockQrPaymentProvider:
    code = "mock_qr"
    title = "模拟支付"

    def describe_channel(self) -> PaymentChannelSummary:
        return PaymentChannelSummary(
            code=self.code,
            title=self.title,
            description="开发环境与联调推荐，点击一次即可完成额度入账。",
            enabled=True,
            ready=True,
            mode="mock",
        )

    def create_intent(self, order: PaymentOrderRequest) -> PaymentIntent:
        payment_url = f"/v1/billing/orders/{order.order_no}/mock-pay"
        qr_content = f"mockpay://{order.order_no}"
        pay_hint = (
            f"当前为开发环境模拟支付订单，订单号 {order.order_no}，金额 ¥{order.package.amount_cents / 100:.2f}。"
            "可以直接点击“模拟支付入账”完成额度充值。"
        )
        payload = {
            "provider_label": self.title,
            "provider_ready": True,
            "payment_url": payment_url,
            "qr_content": qr_content,
            "mock_pay_supported": True,
            "pay_hint": pay_hint,
            "mode": "mock",
        }
        return PaymentIntent(
            provider=self.code,
            provider_label=self.title,
            provider_ready=True,
            payment_url=payment_url,
            qr_content=qr_content,
            mock_pay_supported=True,
            pay_hint=pay_hint,
            payment_payload=payload,
        )

    def hydrate_order(self, order: dict[str, Any]) -> PaymentIntent:
        payload = _normalize_payload(order.get("payment_payload"))
        if payload:
            return PaymentIntent(
                provider=self.code,
                provider_label=str(payload.get("provider_label") or self.title),
                provider_ready=bool(payload.get("provider_ready", True)),
                payment_url=_as_optional_str(payload.get("payment_url")),
                qr_content=_as_optional_str(payload.get("qr_content")),
                mock_pay_supported=bool(payload.get("mock_pay_supported", False)),
                pay_hint=_as_optional_str(payload.get("pay_hint")),
                payment_payload=payload,
            )
        return self.create_intent(
            PaymentOrderRequest(
                order_no=str(order["order_no"]),
                user_id=str(order["user_id"]),
                package=_package_from_order(order),
                public_base_url="",
            )
        )


def _package_from_order(order: dict[str, Any]) -> PaymentPackage:
    return PaymentPackage(
        code=str(order["package_code"]),
        title=str(order["package_code"]),
        description="",
        amount_cents=int(order["amount_cents"]),
        credits=int(order["credits"]),
    )


def _normalize_payload(payload: Any) -> dict[str, Any]:
    return payload if isinstance(payload, dict) else {}


def _as_optional_str(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)
