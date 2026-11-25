import logging
from dataclasses import replace
from uuid import UUID

from kflaner.domain.purchases import OwnedProduct, PaymentEvent, PaymentEventItem
from kflaner.interfaces.products import ProductCatalog, ProductRepository
from kflaner.interfaces.purchases import PurchaseRepository
from kflaner.interfaces.users import UserRepository

logger = logging.getLogger(__name__)


class PurchaseUseCases:
    def __init__(
        self,
        purchases: PurchaseRepository,
        products: ProductRepository,
        catalog: ProductCatalog,
        users: UserRepository,
    ) -> None:
        self._purchases = purchases
        self._products = products
        self._catalog = catalog
        self._users = users

    def handle_payment_event(self, event: PaymentEvent) -> int:
        if not event.succeeded:
            return 0
        if not self._users.exists(event.user_id):
            logger.error("Payment %s belongs to unknown user %s; skipped.", event.payment_id, event.user_id)
            return 0
        items = tuple(item for item in event.items if self._is_mirrored(event.payment_id, item))
        return self._purchases.record_payment(replace(event, items=items))

    def list_owned_products(self, user_id: UUID) -> list[OwnedProduct]:
        return self._purchases.owned_by(user_id)

    def _is_mirrored(self, payment_id: str, item: PaymentEventItem) -> bool:
        if self._products.find_mirror(item.product_id) is not None:
            return True
        # Created directly in payment-manager, so not mirrored yet: fetch it on first sale.
        product = self._catalog.find(item.product_id)
        if product is None:
            logger.error("Payment %s has product %s unknown to payment-manager; item skipped.", payment_id, item.product_id)
            return False
        self._products.save_mirror(product)
        return True
