import logging
from typing import Any

from confluent_kafka import Consumer, KafkaException, Message
from django.conf import settings
from django.db import close_old_connections

from kflaner.controllers.payment_events import handle_payment_message

logger = logging.getLogger(__name__)

POLL_TIMEOUT_SECONDS = 1.0


class PaymentEventConsumer:
    def __init__(self) -> None:
        self._consumer = Consumer(
            {
                "bootstrap.servers": ",".join(settings.KAFKA_BROKERS),
                "group.id": settings.KAFKA_CONSUMER_GROUP,
                "enable.auto.commit": False,
                "auto.offset.reset": "earliest",
            }
        )
        self._running = False

    def run(self) -> None:
        self._running = True
        self._consumer.subscribe([settings.KAFKA_PAYMENT_STATUS_TOPIC])
        logger.info("Consuming %s as group %s.", settings.KAFKA_PAYMENT_STATUS_TOPIC, settings.KAFKA_CONSUMER_GROUP)
        try:
            while self._running:
                self._consume_next()
        finally:
            self._consumer.close()

    def stop(self, *_signal_args: Any) -> None:
        self._running = False

    def _consume_next(self) -> None:
        message = self._consumer.poll(POLL_TIMEOUT_SECONDS)
        if message is None:
            return
        if message.error():
            raise KafkaException(message.error())
        self._process(message)
        self._consumer.commit(message=message, asynchronous=False)

    def _process(self, message: Message) -> None:
        close_old_connections()
        handle_payment_message(message.value())
