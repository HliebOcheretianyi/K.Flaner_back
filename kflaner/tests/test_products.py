import json
from unittest.mock import patch
from uuid import UUID, uuid4

from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from kflaner.controllers.payment_events import handle_payment_message
from kflaner.controllers.products import product_catalog
from kflaner.models import Product, Purchase, User
from kflaner.tests.fake_payment_manager import FakePaymentManager

JWT_SETTINGS = {
    "JWT_SECRET": "test-secret-that-is-at-least-32-bytes-long",
    "JWT_ISSUER": "kflaner-back",
    "JWT_AUDIENCE": "kflaner",
}
PASSWORD = "correct-horse-battery-staple"


class FakePaymentManagerMixin:
    def setUp(self) -> None:
        super().setUp()
        self.payment_manager = FakePaymentManager()
        patcher = patch.object(product_catalog, "_transport", self.payment_manager.transport)
        patcher.start()
        self.addCleanup(patcher.stop)


@override_settings(**JWT_SETTINGS)
class ProductAdminTests(FakePaymentManagerMixin, APITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.client.force_login(User.objects.create_superuser(email="admin@example.com", password=PASSWORD))

    def submit(self, url: str, **overrides):
        data = {"name": "  Випуск #1 ", "description": "Перший випуск", "price": "150.50", "currency": "UAH"}
        return self.client.post(url, {**data, **overrides}, format="multipart")

    def test_create_registers_product_in_payment_manager_first_and_reuses_its_id(self) -> None:
        response = self.submit("/admin/kflaner/product/add/")

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        [remote] = self.payment_manager.products.values()
        local = Product.objects.get()
        self.assertEqual(local.id, UUID(remote["id"]))
        self.assertEqual(remote["price"], {"amount": 15050, "currency": "UAH"})
        self.assertEqual(local.name, "Випуск #1")
        self.assertEqual(local.price_amount, 15050)
        self.assertIsNone(self.payment_manager.received_authorization)

    @override_settings(PAYMENT_MANAGER_SERVICE_TOKEN="wrong-token-that-is-at-least-32-bytes-long")
    def test_create_fails_on_form_when_service_token_is_rejected(self) -> None:
        response = self.submit("/admin/kflaner/product/add/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Payment manager")
        self.assertFalse(Product.objects.exists())

    def test_create_saves_nothing_locally_when_payment_manager_fails(self) -> None:
        self.payment_manager.fail_with = 500

        response = self.submit("/admin/kflaner/product/add/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Payment manager")
        self.assertFalse(Product.objects.exists())

    def test_edit_updates_both_sides(self) -> None:
        self.submit("/admin/kflaner/product/add/")
        product = Product.objects.get()

        response = self.submit(f"/admin/kflaner/product/{product.id}/change/", name="Випуск #1 (друк)", price="200")

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        product.refresh_from_db()
        self.assertEqual(product.name, "Випуск #1 (друк)")
        self.assertEqual(product.price_amount, 20000)
        self.assertEqual(self.payment_manager.products[str(product.id)]["price"]["amount"], 20000)

    def test_delete_removes_product_from_both_sides(self) -> None:
        self.submit("/admin/kflaner/product/add/")
        product = Product.objects.get()

        response = self.client.post(f"/admin/kflaner/product/{product.id}/delete/", {"post": "yes"})

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertFalse(Product.objects.exists())
        self.assertEqual(self.payment_manager.products, {})


def payment_message(user_id: UUID, product_id: str, status: str = "success", payment_id: str | None = None) -> bytes:
    return json.dumps({
        "paymentId": payment_id or str(uuid4()),
        "provider": "mono",
        "invoiceId": "inv-1",
        "userId": str(user_id),
        "status": status,
        "amount": 30000,
        "finalAmount": 30000,
        "currency": "UAH",
        "items": [{"productId": product_id, "quantity": 2, "unitAmount": 15000}],
        "modifiedAt": "2026-11-25T10:00:00.123456789Z",
    }).encode()


@override_settings(**JWT_SETTINGS)
class PaymentEventTests(FakePaymentManagerMixin, APITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.user = User.objects.create_user(email="reader@example.com", password=PASSWORD)
        remote = self.payment_manager.add()
        Product.objects.create(id=remote["id"], name=remote["name"], price_amount=15000, currency="UAH")
        self.product_id = remote["id"]

    def test_successful_payment_records_owned_products(self) -> None:
        recorded = handle_payment_message(payment_message(self.user.id, self.product_id))

        self.assertEqual(recorded, 1)
        purchase = Purchase.objects.get()
        self.assertEqual((purchase.user_id, str(purchase.product_id)), (self.user.id, self.product_id))
        self.assertEqual((purchase.quantity, purchase.unit_amount, purchase.currency), (2, 15000, "UAH"))

    def test_only_successful_payments_are_recorded(self) -> None:
        for payment_status in ("pending", "processing", "failure", "reversed"):
            handle_payment_message(payment_message(self.user.id, self.product_id, status=payment_status))

        self.assertFalse(Purchase.objects.exists())

    def test_redelivered_event_is_recorded_once(self) -> None:
        message = payment_message(self.user.id, self.product_id, payment_id="pay-1")

        handle_payment_message(message)
        self.assertEqual(handle_payment_message(message), 0)

        self.assertEqual(Purchase.objects.count(), 1)

    def test_product_created_directly_in_payment_manager_is_mirrored_on_first_sale(self) -> None:
        remote = self.payment_manager.add(name="Мерч: худі", amount=90000)

        handle_payment_message(payment_message(self.user.id, remote["id"]))

        self.assertEqual(Product.objects.get(id=remote["id"]).name, "Мерч: худі")
        self.assertTrue(Purchase.objects.filter(product_id=remote["id"]).exists())

    def test_unknown_product_and_user_and_malformed_messages_are_skipped(self) -> None:
        self.assertEqual(handle_payment_message(payment_message(self.user.id, str(uuid4()))), 0)
        self.assertEqual(handle_payment_message(payment_message(uuid4(), self.product_id)), 0)
        self.assertEqual(handle_payment_message(b"not json"), 0)
        self.assertEqual(handle_payment_message(b'{"paymentId": "x"}'), 0)

        self.assertFalse(Purchase.objects.exists())

    def test_owned_products_endpoint_lists_only_current_users_purchases(self) -> None:
        other = User.objects.create_user(email="other@example.com", password=PASSWORD)
        handle_payment_message(payment_message(self.user.id, self.product_id))
        handle_payment_message(payment_message(other.id, self.product_id))
        login = self.client.post(
            reverse("auth-login"), {"email": "reader@example.com", "password": PASSWORD}, format="json"
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access_token']}")

        response = self.client.get(reverse("owned-products"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        [item] = response.data["items"]
        self.assertEqual(str(item["id"]), self.product_id)
        self.assertEqual(item["quantity"], 2)

    def test_owned_products_requires_authentication(self) -> None:
        self.assertEqual(self.client.get(reverse("owned-products")).status_code, status.HTTP_401_UNAUTHORIZED)
