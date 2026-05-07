from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class PaymentPackage:
    code: str
    title: str
    description: str
    amount_cents: int
    credits: int


@dataclass(frozen=True)
class PaymentOrderRequest:
    order_no: str
    user_id: str
    package: PaymentPackage
    public_base_url: str


@dataclass(frozen=True)
class PaymentChannelSummary:
    code: str
    title: str
    description: str
    enabled: bool
    ready: bool
    mode: str


@dataclass(frozen=True)
class PaymentIntent:
    provider: str
    provider_label: str
    provider_ready: bool
    payment_url: str | None = None
    qr_content: str | None = None
    mock_pay_supported: bool = False
    pay_hint: str | None = None
    payment_payload: dict[str, Any] = field(default_factory=dict)


class PaymentProvider(Protocol):
    code: str

    def describe_channel(self) -> PaymentChannelSummary: ...

    def create_intent(self, order: PaymentOrderRequest) -> PaymentIntent: ...

    def hydrate_order(self, order: dict[str, Any]) -> PaymentIntent: ...
