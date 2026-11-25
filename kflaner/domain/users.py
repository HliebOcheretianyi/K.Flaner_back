from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from kflaner.utils.serialization import SerializableMixin
from kflaner.utils.validation import require_text

MAX_EMAIL_LENGTH = 254
MAX_NAME_LENGTH = 150
MAX_PASSWORD_LENGTH = 128


class Role(StrEnum):
    USER = "user"
    EDITOR = "editor"
    ADMIN = "admin"

    @property
    def payment_role(self) -> str:
        # payment-manager only knows "user" and "admin"; editors pay like regular users.
        return Role.ADMIN.value if self is Role.ADMIN else Role.USER.value


def normalize_email(email: str) -> str:
    return email.strip().lower()


@dataclass(frozen=True)
class User(SerializableMixin):
    id: UUID
    email: str
    first_name: str
    last_name: str
    role: Role


@dataclass(frozen=True)
class Registration:
    email: str
    first_name: str
    last_name: str

    def validate(self) -> None:
        require_text("email", self.email, MAX_EMAIL_LENGTH)
        require_text("first_name", self.first_name, MAX_NAME_LENGTH)
        require_text("last_name", self.last_name, MAX_NAME_LENGTH)


@dataclass(frozen=True)
class Credentials:
    email: str
    password: str
