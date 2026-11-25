from uuid import UUID, uuid4

from django.db import models, transaction

from kflaner.domain.purchases import OwnedProduct, PaymentEvent
from kflaner.models.products import Product
from kflaner.models.users import User


class Purchase(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="purchases")
    # PROTECT: a product people have paid for cannot be deleted out from under them.
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="purchases")
    payment_id = models.CharField(max_length=64)
    quantity = models.PositiveIntegerField()
    unit_amount = models.PositiveBigIntegerField(help_text="Price paid per unit, in minor units.")
    currency = models.CharField(max_length=3)
    purchased_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "purchases"
        ordering = ["-purchased_at"]
        constraints = [
            models.UniqueConstraint(fields=["payment_id", "product"], name="unique_purchase_per_payment_product"),
        ]

    @classmethod
    def record_payment(cls, event: PaymentEvent) -> int:
        records = [
            cls(
                user_id=event.user_id,
                product_id=item.product_id,
                payment_id=event.payment_id,
                quantity=item.quantity,
                unit_amount=item.unit_amount,
                currency=event.currency,
                purchased_at=event.modified_at,
            )
            for item in event.items
        ]
        with transaction.atomic():
            already_recorded = set(
                cls.objects.filter(payment_id=event.payment_id).values_list("product_id", flat=True)
            )
            new_records = [record for record in records if record.product_id not in already_recorded]
            # ignore_conflicts covers a concurrent consumer inserting the same rows in between.
            cls.objects.bulk_create(new_records, ignore_conflicts=True)
        return len(new_records)

    @classmethod
    def owned_by(cls, user_id: UUID) -> list[OwnedProduct]:
        return [
            OwnedProduct(product=record.product.to_entity(), quantity=record.quantity, purchased_at=record.purchased_at)
            for record in cls.objects.filter(user_id=user_id).select_related("product")
        ]
