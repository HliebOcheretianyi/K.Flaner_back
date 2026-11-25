from dataclasses import dataclass

from kflaner.utils.serialization import SerializableMixin

TOKEN_TYPE = "Bearer"


@dataclass(frozen=True)
class TokenPair(SerializableMixin):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = TOKEN_TYPE
