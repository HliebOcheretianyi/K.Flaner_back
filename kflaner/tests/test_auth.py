from unittest.mock import patch
from uuid import UUID

import jwt
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle

from kflaner.domain.users import Role
from kflaner.models import User

JWT_SETTINGS = {
    "JWT_SECRET": "test-secret-that-is-at-least-32-bytes-long",
    "JWT_ISSUER": "kflaner-back",
    "JWT_AUDIENCE": "kflaner",
}
PASSWORD = "correct-horse-battery-staple"


@override_settings(**JWT_SETTINGS)
class AuthTests(APITestCase):
    def setUp(self) -> None:
        cache.clear()

    def register(self, email: str = "reader@example.com", password: str = PASSWORD):
        return self.client.post(
            reverse("auth-register"),
            {"email": email, "password": password, "first_name": "Taras", "last_name": "Shevchenko"},
            format="json",
        )

    def login(self, email: str = "reader@example.com", password: str = PASSWORD):
        return self.client.post(reverse("auth-login"), {"email": email, "password": password}, format="json")

    def decode_like_payment_manager(self, token: str) -> dict:
        return jwt.decode(
            token,
            JWT_SETTINGS["JWT_SECRET"],
            algorithms=["HS256"],
            issuer=JWT_SETTINGS["JWT_ISSUER"],
            audience=JWT_SETTINGS["JWT_AUDIENCE"],
            options={"require": ["exp", "id", "role"]},
        )

    def test_register_returns_token_pair_accepted_by_payment_manager(self) -> None:
        response = self.register()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["token_type"], "Bearer")
        claims = self.decode_like_payment_manager(response.data["access_token"])
        user = User.objects.get(email="reader@example.com")
        self.assertEqual(UUID(claims["id"]), user.id)
        self.assertEqual(claims["role"], "user")

    def test_register_rejects_duplicate_email_case_insensitively(self) -> None:
        self.register()

        response = self.register(email="Reader@Example.com")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["error"]["code"], "conflict")

    def test_register_rejects_weak_password(self) -> None:
        response = self.register(password="123")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"]["field"], "password")

    def test_register_rejects_blank_name(self) -> None:
        response = self.client.post(
            reverse("auth-register"),
            {"email": "a@example.com", "password": PASSWORD, "first_name": " ", "last_name": "X"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"]["field"], "first_name")

    def test_login_succeeds_with_any_email_case(self) -> None:
        self.register()

        response = self.login(email="READER@example.com")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("refresh_token", response.data)

    def test_login_rejects_wrong_password_and_unknown_email(self) -> None:
        self.register()

        for response in (self.login(password="wrong-password"), self.login(email="nobody@example.com")):
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
            self.assertEqual(response.data["error"]["code"], "authentication_failed")

    def test_login_rejects_inactive_user(self) -> None:
        self.register()
        User.objects.filter(email="reader@example.com").update(is_active=False)

        self.assertEqual(self.login().status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_ignores_stale_authorization_header(self) -> None:
        self.register()
        self.client.credentials(HTTP_AUTHORIZATION="Bearer expired.or.garbage")

        self.assertEqual(self.login().status_code, status.HTTP_200_OK)

    def test_me_requires_valid_bearer_token(self) -> None:
        access_token = self.register().data["access_token"]

        self.assertEqual(self.client.get(reverse("auth-me")).status_code, status.HTTP_401_UNAUTHORIZED)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer garbage")
        self.assertEqual(self.client.get(reverse("auth-me")).status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = self.client.get(reverse("auth-me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "reader@example.com")
        self.assertEqual(response.data["role"], "user")

    def test_me_rejects_token_signed_with_other_secret(self) -> None:
        self.register()
        user_id = User.objects.get().id
        forged = jwt.encode(
            {"id": str(user_id), "role": "admin", "exp": 9999999999, "iss": "kflaner-back", "aud": "kflaner"},
            "some-other-secret-that-is-32-bytes-long",
            algorithm="HS256",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {forged}")

        self.assertEqual(self.client.get(reverse("auth-me")).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_rotates_token_and_rejects_reuse(self) -> None:
        refresh_token = self.register().data["refresh_token"]

        response = self.client.post(reverse("auth-refresh"), {"refresh_token": refresh_token}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data["refresh_token"], refresh_token)

        reused = self.client.post(reverse("auth-refresh"), {"refresh_token": refresh_token}, format="json")
        self.assertEqual(reused.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_revokes_refresh_token(self) -> None:
        refresh_token = self.register().data["refresh_token"]

        response = self.client.post(reverse("auth-logout"), {"refresh_token": refresh_token}, format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        refreshed = self.client.post(reverse("auth-refresh"), {"refresh_token": refresh_token}, format="json")
        self.assertEqual(refreshed.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_payment_role_claim_maps_editor_to_user_and_keeps_admin(self) -> None:
        for role, expected in ((Role.EDITOR, "user"), (Role.ADMIN, "admin")):
            email = f"{role}@example.com"
            User.objects.create_user(email=email, password=PASSWORD, role=role)

            claims = self.decode_like_payment_manager(self.login(email=email).data["access_token"])

            self.assertEqual(claims["role"], expected)

    @patch.object(ScopedRateThrottle, "THROTTLE_RATES", {"auth": "2/min"})
    def test_auth_endpoints_are_throttled(self) -> None:
        responses = [self.login().status_code for _ in range(3)]

        self.assertEqual(responses[-1], status.HTTP_429_TOO_MANY_REQUESTS)


class AdminTests(APITestCase):
    def test_superuser_is_admin_and_can_open_user_admin_pages(self) -> None:
        superuser = User.objects.create_superuser(email="Admin@Example.com", password=PASSWORD)
        self.client.force_login(superuser)

        self.assertEqual(superuser.role, Role.ADMIN)
        self.assertEqual(superuser.email, "admin@example.com")
        for url in ("/admin/kflaner/user/", "/admin/kflaner/user/add/", f"/admin/kflaner/user/{superuser.id}/change/"):
            self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK, url)
