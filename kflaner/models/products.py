from uuid import UUID

from django.db import models

from kflaner.domain.products import MAX_PRODUCT_NAME_LENGTH, SUPPORTED_CURRENCIES
from kflaner.domain.products import Product as ProductEntity


class Product(models.Model):
    # No default: the id is assigned by payment-manager, which owns the product.
    id = models.UUIDField(primary_key=True, editable=False)
    name = models.CharField(max_length=MAX_PRODUCT_NAME_LENGTH)
    description = models.TextField(blank=True)
    price_amount = models.PositiveBigIntegerField(help_text="In minor units (kopecks).")
    currency = models.CharField(max_length=3, choices=[(code, code) for code in SUPPORTED_CURRENCIES])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @classmethod
    def save_mirror(cls, product: ProductEntity) -> None:
        cls.objects.update_or_create(
            id=product.id,
            defaults={
                "name": product.name,
                "description": product.description,
                "price_amount": product.price_amount,
                "currency": product.currency,
            },
        )

    @classmethod
    def delete_mirror(cls, product_id: UUID) -> None:
        cls.objects.filter(id=product_id).delete()

    @classmethod
    def find_mirror(cls, product_id: UUID) -> ProductEntity | None:
        record = cls.objects.filter(id=product_id).first()
        return record.to_entity() if record else None

    def to_entity(self) -> ProductEntity:
        return ProductEntity(
            id=self.id,
            name=self.name,
            description=self.description,
            price_amount=self.price_amount,
            currency=self.currency,
        )
