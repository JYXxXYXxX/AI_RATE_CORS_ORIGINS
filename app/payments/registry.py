from __future__ import annotations

from app.config import Settings
from app.payments.alipay import AlipayPaymentProvider
from app.payments.base import PaymentChannelSummary, PaymentIntent, PaymentProvider
from app.payments.mock import MockQrPaymentProvider
from app.payments.wechat import WechatPaymentProvider


class PaymentProviderRegistry:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._aliases = {
            "mock": "mock_qr",
            "mock_qr_callback": "mock_qr",
        }
        self._providers: dict[str, PaymentProvider] = {
            "mock_qr": MockQrPaymentProvider(),
            "alipay": AlipayPaymentProvider(settings),
            "wechat": WechatPaymentProvider(settings),
        }

    def get(self, provider: str) -> PaymentProvider:
        normalized_provider = self._aliases.get(provider, provider)
        selected = self._providers.get(normalized_provider)
        if selected is None:
            raise ValueError("unsupported payment provider")
        return selected

    def list_channels(self) -> list[PaymentChannelSummary]:
        return [self._providers[key].describe_channel() for key in ("mock_qr", "alipay", "wechat")]

    def hydrate_order(self, order: dict[str, object]) -> PaymentIntent:
        provider = str(order.get("provider") or "mock_qr")
        return self.get(provider).hydrate_order(order)
