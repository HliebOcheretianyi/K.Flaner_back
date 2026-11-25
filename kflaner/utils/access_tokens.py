from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import jwt
from django.conf import settings

from kflaner.domain.errors import AuthenticationError
from kflaner.domain.users import User

ALGORITHM = "HS256"
CLOCK_SKEW_LEEWAY_SECONDS = 30


class JWTAccessTokens:
    """HS256 tokens in the format payment-manager verifies: {id, role, exp[, iss, aud]}."""

    @property
    def lifetime_seconds(self) -> int:
        return int(settings.ACCESS_TOKEN_LIFETIME.total_seconds())

    def issue(self, user: User) -> str:
        now = datetime.now(UTC)
        claims: dict[str, Any] = {
            "id": str(user.id),
            "role": user.role.payment_role,
            "iat": now,
            "exp": now + settings.ACCESS_TOKEN_LIFETIME,
        }
        if settings.JWT_ISSUER:
            claims["iss"] = settings.JWT_ISSUER
        if settings.JWT_AUDIENCE:
            claims["aud"] = settings.JWT_AUDIENCE
        return jwt.encode(claims, settings.JWT_SECRET, algorithm=ALGORITHM)

    def verify(self, raw_token: str) -> UUID:
        try:
            claims = jwt.decode(
                raw_token,
                settings.JWT_SECRET,
                algorithms=[ALGORITHM],
                issuer=settings.JWT_ISSUER or None,
                audience=settings.JWT_AUDIENCE or None,
                leeway=CLOCK_SKEW_LEEWAY_SECONDS,
                options={"require": ["exp", "id"]},
            )
            return UUID(claims["id"])
        except (jwt.InvalidTokenError, ValueError) as error:
            raise AuthenticationError("Access token is invalid or expired.") from error
