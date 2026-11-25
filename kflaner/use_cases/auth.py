from uuid import UUID

from kflaner.domain.auth import TokenPair
from kflaner.domain.errors import AuthenticationError, ConflictError, NotFoundError
from kflaner.domain.users import Credentials, Registration, User
from kflaner.interfaces.auth import AccessTokenIssuer, PasswordPolicy, RefreshTokenRepository
from kflaner.interfaces.users import UserRepository


class AuthUseCases:
    def __init__(
        self,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
        access_tokens: AccessTokenIssuer,
        password_policy: PasswordPolicy,
    ) -> None:
        self._users = users
        self._refresh_tokens = refresh_tokens
        self._access_tokens = access_tokens
        self._password_policy = password_policy

    def register(self, registration: Registration, password: str) -> TokenPair:
        registration.validate()
        self._password_policy.validate(password, registration)
        if self._users.email_taken(registration.email):
            raise ConflictError("A user with this email already exists.")
        return self._issue_tokens(self._users.register(registration, password))

    def login(self, credentials: Credentials) -> TokenPair:
        user = self._users.find_by_credentials(credentials)
        if user is None:
            raise AuthenticationError("Invalid email or password.")
        return self._issue_tokens(user)

    def refresh(self, refresh_token: str) -> TokenPair:
        user_id = self._refresh_tokens.consume(refresh_token)
        user = self._users.find_active(user_id) if user_id else None
        if user is None:
            raise AuthenticationError("Refresh token is invalid or expired.")
        return self._issue_tokens(user)

    def logout(self, refresh_token: str) -> None:
        self._refresh_tokens.revoke(refresh_token)

    def get_profile(self, user_id: UUID) -> User:
        user = self._users.find_active(user_id)
        if user is None:
            raise NotFoundError(f"User {user_id} does not exist.")
        return user

    def _issue_tokens(self, user: User) -> TokenPair:
        return TokenPair(
            access_token=self._access_tokens.issue(user),
            refresh_token=self._refresh_tokens.issue(user.id),
            expires_in=self._access_tokens.lifetime_seconds,
        )
