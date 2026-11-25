from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from kflaner import models
from kflaner.use_cases.products import ProductUseCases
from kflaner.use_cases.purchases import PurchaseUseCases
from kflaner.utils.payment_manager import PaymentManagerProducts

product_catalog = PaymentManagerProducts()
product_use_cases = ProductUseCases(catalog=product_catalog, products=models.Product)
purchase_use_cases = PurchaseUseCases(
    purchases=models.Purchase,
    products=models.Product,
    catalog=product_catalog,
    users=models.User,
)


class OwnedProductCollectionController(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        owned = purchase_use_cases.list_owned_products(request.user.id)
        return Response({"items": [product.serialize() for product in owned]})
