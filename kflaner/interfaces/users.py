from typing import Protocol
from uuid import UUID

from kflaner.domain.users import Credentials, Registration, User


class UserRepository(Protocol):
    def email_taken(self, email: str) -> bool: ...

    def register(self, registration: Registration, password: str) -> User: ...

    def find_by_credentials(self, credentials: Credentials) -> User | None: ...

    def find_active(self, user_id: UUID) -> User | None: ...
