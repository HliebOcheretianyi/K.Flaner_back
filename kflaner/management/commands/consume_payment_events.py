import signal
from typing import Any

from django.core.management.base import BaseCommand

from kflaner.utils.payment_event_consumer import PaymentEventConsumer


class Command(BaseCommand):
    help = "Consume payment-manager payment status events and record purchases of successful payments."

    def handle(self, *args: Any, **options: Any) -> None:
        consumer = PaymentEventConsumer()
        signal.signal(signal.SIGTERM, consumer.stop)
        signal.signal(signal.SIGINT, consumer.stop)
        consumer.run()
