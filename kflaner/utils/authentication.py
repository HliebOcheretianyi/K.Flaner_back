from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.request import Request

from kflaner import models
from kflaner.domain.auth import TOKEN_TYPE
from kflaner.domain.errors import AuthenticationError
from kflaner.utils.access_tokens import JWTAccessTokens


class BearerTokenAuthentication(BaseAuthentication):
    def authenticate(self, request: Request) -> tuple[models.User, str] | None:
        scheme, _, token = get_authorization_header(request).decode(errors="replace").partition(" ")
        token = token.strip()
        if scheme.lower() != TOKEN_TYPE.lower() or not token:
            return None
        try:
            user_id = JWTAccessTokens().verify(token)
        except AuthenticationError as error:
            raise exceptions.AuthenticationFailed(error.message) from error
        user = models.User.objects.filter(id=user_id, is_active=True).first()
        if user is None:
            raise exceptions.AuthenticationFailed("User is inactive or does not exist.")
        return user, token

    def authenticate_header(self, request: Request) -> str:
        return TOKEN_TYPE
