from dataclasses import dataclass
from uuid import UUID

from kflaner.domain.errors import ValidationError
from kflaner.utils.serialization import SerializableMixin
from kflaner.utils.validation import require_text

MAX_PRODUCT_NAME_LENGTH = 255
SUPPORTED_CURRENCIES = ("UAH",)


@dataclass(frozen=True)
class ProductDraft:
    name: str
    description: str
    price_amount: int
    currency: str

    def validate(self) -> None:
        require_text("name", self.name, MAX_PRODUCT_NAME_LENGTH)
        if self.price_amount < 0:
            raise ValidationError("price_amount", "Price must not be negative.")
        if self.currency not in SUPPORTED_CURRENCIES:
            raise ValidationError("currency", f"Currency must be one of: {', '.join(SUPPORTED_CURRENCIES)}.")


@dataclass(frozen=True)
class Product(SerializableMixin):
    id: UUID
    name: str
    description: str
    price_amount: int
    currency: str
