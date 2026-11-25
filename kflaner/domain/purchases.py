from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from kflaner.domain.products import Product
from kflaner.utils.serialization import SerializableMixin

PAYMENT_SUCCESS = "success"


@dataclass(frozen=True)
class PaymentEventItem:
    product_id: UUID
    quantity: int
    unit_amount: int


@dataclass(frozen=True)
class PaymentEvent:
    payment_id: str
    user_id: UUID
    status: str
    currency: str
    items: tuple[PaymentEventItem, ...]
    modified_at: datetime

    @property
    def succeeded(self) -> bool:
        return self.status == PAYMENT_SUCCESS


@dataclass(frozen=True)
class OwnedProduct(SerializableMixin):
    product: Product
    quantity: int
    purchased_at: datetime

    def serialize(self) -> dict[str, Any]:
        return {**self.product.serialize(), "quantity": self.quantity, "purchased_at": self.purchased_at}
