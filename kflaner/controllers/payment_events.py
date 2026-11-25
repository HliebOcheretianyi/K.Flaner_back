import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from kflaner.controllers.products import purchase_use_cases
from kflaner.domain.purchases import PaymentEvent, PaymentEventItem

logger = logging.getLogger(__name__)


class MalformedPaymentEvent(ValueError):
    pass


def parse_payment_event(raw: bytes) -> PaymentEvent:
    try:
        data: dict[str, Any] = json.loads(raw)
        return PaymentEvent(
            payment_id=str(data["paymentId"]),
            user_id=UUID(data["userId"]),
            status=str(data["status"]),
            currency=str(data["currency"]),
            items=tuple(
                PaymentEventItem(
                    product_id=UUID(item["productId"]),
                    quantity=int(item["quantity"]),
                    unit_amount=int(item["unitAmount"]),
                )
                for item in data["items"] or []
            ),
            modified_at=datetime.fromisoformat(data["modifiedAt"]),
        )
    except (ValueError, KeyError, TypeError) as error:
        raise MalformedPaymentEvent(str(error)) from error


def handle_payment_message(raw: bytes) -> int:
    try:
        event = parse_payment_event(raw)
    except MalformedPaymentEvent as error:
        # Retrying can never fix a malformed message and would block the partition, so it is dropped.
        logger.error("Dropping malformed payment event %r: %s", raw[:500], error)
        return 0
    recorded = purchase_use_cases.handle_payment_event(event)
    if recorded:
        logger.info("Payment %s: recorded %d purchase(s) for user %s.", event.payment_id, recorded, event.user_id)
    return recorded
