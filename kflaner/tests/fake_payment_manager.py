import json
from uuid import uuid4

import httpx
from django.conf import settings


class FakePaymentManager:
    def __init__(self) -> None:
        self.products: dict[str, dict] = {}
        self.fail_with: int | None = None
        self.received_authorization: str | None = None
        self.service_token = settings.PAYMENT_MANAGER_SERVICE_TOKEN
        self.transport = httpx.MockTransport(self.handle)

    def add(self, name: str = "Issue #1", amount: int = 15000) -> dict:
        product = {"id": str(uuid4()), "name": name, "description": "", "price": {"amount": amount, "currency": "UAH"}}
        self.products[product["id"]] = product
        return product

    def handle(self, request: httpx.Request) -> httpx.Response:
        if self.fail_with:
            return httpx.Response(self.fail_with, json={"error": "internal error"})
        parts = request.url.path.strip("/").split("/")
        product_id = parts[1] if len(parts) > 1 else None
        if request.method == "GET":
            product = self.products.get(product_id)
            return httpx.Response(200, json=product) if product else self.not_found()
        if not self.is_admin(request):
            return httpx.Response(403, json={"error": "insufficient role for this action"})
        if request.method == "DELETE":
            return httpx.Response(204) if self.products.pop(product_id, None) else self.not_found()
        body = json.loads(request.content)
        if body["price"]["amount"] < 0:
            return httpx.Response(400, json={"error": "price amount must not be negative"})
        if request.method == "PUT" and product_id not in self.products:
            return self.not_found()
        product = {"id": product_id or str(uuid4()), **body, "name": body["name"].strip()}
        self.products[product["id"]] = product
        return httpx.Response(200 if product_id else 201, json=product)

    def is_admin(self, request: httpx.Request) -> bool:
        self.received_authorization = request.headers.get("Authorization")
        return request.headers.get("X-Service-Token") == self.service_token

    def not_found(self) -> httpx.Response:
        return httpx.Response(404, json={"error": "not found"})
