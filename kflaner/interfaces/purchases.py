from typing import Protocol
from uuid import UUID

from kflaner.domain.purchases import OwnedProduct, PaymentEvent


class PurchaseRepository(Protocol):
    def record_payment(self, event: PaymentEvent) -> int: ...

    def owned_by(self, user_id: UUID) -> list[OwnedProduct]: ...
