from typing import Protocol
from uuid import UUID

from kflaner.domain.users import Registration, User


class AccessTokenIssuer(Protocol):
    @property
    def lifetime_seconds(self) -> int: ...

    def issue(self, user: User) -> str: ...


class RefreshTokenRepository(Protocol):
    def issue(self, user_id: UUID) -> str: ...

    def consume(self, raw_token: str) -> UUID | None: ...

    def revoke(self, raw_token: str) -> None: ...


class PasswordPolicy(Protocol):
    def validate(self, password: str, registration: Registration) -> None: ...
