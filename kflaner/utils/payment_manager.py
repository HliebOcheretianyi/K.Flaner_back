from typing import Any
from uuid import UUID

import httpx
from django.conf import settings

from kflaner.domain.errors import ExternalServiceError, NotFoundError, ValidationError
from kflaner.domain.products import Product, ProductDraft

SERVICE_TOKEN_HEADER = "X-Service-Token"


class PaymentManagerProducts:
    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self._transport = transport

    def create(self, draft: ProductDraft) -> Product:
        return to_product(self._request("POST", "/products", json=to_payload(draft)).json())

    def edit(self, product_id: UUID, draft: ProductDraft) -> Product:
        return to_product(self._request("PUT", f"/products/{product_id}", json=to_payload(draft)).json())

    def delete(self, product_id: UUID) -> None:
        try:
            self._request("DELETE", f"/products/{product_id}")
        except NotFoundError:
            pass

    def find(self, product_id: UUID) -> Product | None:
        try:
            return to_product(self._request("GET", f"/products/{product_id}").json())
        except NotFoundError:
            return None

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        headers = {SERVICE_TOKEN_HEADER: settings.PAYMENT_MANAGER_SERVICE_TOKEN}
        try:
            with httpx.Client(
                base_url=settings.PAYMENT_MANAGER_URL,
                timeout=settings.PAYMENT_MANAGER_TIMEOUT_SECONDS,
                transport=self._transport,
            ) as client:
                response = client.request(method, path, headers=headers, **kwargs)
        except httpx.HTTPError as error:
            raise ExternalServiceError(f"Payment manager is unreachable: {error}") from error
        raise_for_status(response)
        return response


def raise_for_status(response: httpx.Response) -> None:
    if response.is_success:
        return
    message = error_message(response)
    if response.status_code == httpx.codes.NOT_FOUND:
        raise NotFoundError(message)
    if response.status_code == httpx.codes.BAD_REQUEST:
        raise ValidationError(field_for(message), message)
    raise ExternalServiceError(f"Payment manager responded {response.status_code}: {message}")


def error_message(response: httpx.Response) -> str:
    try:
        return str(response.json()["error"])
    except (ValueError, KeyError, TypeError):
        return response.text or response.reason_phrase


def field_for(message: str) -> str:
    lowered = message.lower()
    if "price" in lowered or "currency" in lowered:
        return "price_amount"
    return "name" if "name" in lowered else ""


def to_payload(draft: ProductDraft) -> dict[str, Any]:
    return {
        "name": draft.name,
        "description": draft.description,
        "price": {"amount": draft.price_amount, "currency": draft.currency},
    }


def to_product(data: dict[str, Any]) -> Product:
    try:
        return Product(
            id=UUID(data["id"]),
            name=data["name"],
            description=data["description"],
            price_amount=int(data["price"]["amount"]),
            currency=data["price"]["currency"],
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ExternalServiceError(f"Payment manager returned an unexpected product: {data!r}") from error
