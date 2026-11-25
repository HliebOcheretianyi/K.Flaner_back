from typing import Any

from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from kflaner import models
from kflaner.domain.users import (
    MAX_EMAIL_LENGTH,
    MAX_PASSWORD_LENGTH,
    Credentials,
    Registration,
    normalize_email,
)
from kflaner.use_cases.auth import AuthUseCases
from kflaner.utils.access_tokens import JWTAccessTokens
from kflaner.utils.password_policy import DjangoPasswordPolicy

auth_use_cases = AuthUseCases(
    users=models.User,
    refresh_tokens=models.RefreshToken,
    access_tokens=JWTAccessTokens(),
    password_policy=DjangoPasswordPolicy(),
)


class RegisterRequest(serializers.Serializer):
    email = serializers.EmailField(max_length=MAX_EMAIL_LENGTH)
    password = serializers.CharField(max_length=MAX_PASSWORD_LENGTH, trim_whitespace=False)
    first_name = serializers.CharField(allow_blank=True)
    last_name = serializers.CharField(allow_blank=True)

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        values = super().to_internal_value(data)
        registration = Registration(
            email=normalize_email(values["email"]),
            first_name=values["first_name"],
            last_name=values["last_name"],
        )
        return {"registration": registration, "password": values["password"]}


class LoginRequest(serializers.Serializer):
    email = serializers.CharField(max_length=MAX_EMAIL_LENGTH)
    password = serializers.CharField(max_length=MAX_PASSWORD_LENGTH, trim_whitespace=False)

    def to_internal_value(self, data: Any) -> Credentials:
        values = super().to_internal_value(data)
        return Credentials(email=normalize_email(values["email"]), password=values["password"])


class RefreshTokenRequest(serializers.Serializer):
    refresh_token = serializers.CharField()


class PublicAuthController(APIView):
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class RegisterController(PublicAuthController):
    def post(self, request: Request) -> Response:
        body = RegisterRequest(data=request.data)
        body.is_valid(raise_exception=True)
        tokens = auth_use_cases.register(**body.validated_data)
        return Response(tokens.serialize(), status=status.HTTP_201_CREATED)


class LoginController(PublicAuthController):
    def post(self, request: Request) -> Response:
        body = LoginRequest(data=request.data)
        body.is_valid(raise_exception=True)
        return Response(auth_use_cases.login(body.validated_data).serialize())


class RefreshController(PublicAuthController):
    def post(self, request: Request) -> Response:
        body = RefreshTokenRequest(data=request.data)
        body.is_valid(raise_exception=True)
        return Response(auth_use_cases.refresh(**body.validated_data).serialize())


class LogoutController(PublicAuthController):
    def post(self, request: Request) -> Response:
        body = RefreshTokenRequest(data=request.data)
        body.is_valid(raise_exception=True)
        auth_use_cases.logout(**body.validated_data)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeController(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return Response(auth_use_cases.get_profile(request.user.id).serialize())
