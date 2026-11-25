from uuid import UUID

from kflaner.domain.products import Product, ProductDraft
from kflaner.interfaces.products import ProductCatalog, ProductRepository


class ProductUseCases:
    def __init__(self, catalog: ProductCatalog, products: ProductRepository) -> None:
        self._catalog = catalog
        self._products = products

    def create_product(self, draft: ProductDraft) -> Product:
        draft.validate()
        product = self._catalog.create(draft)
        self._products.save_mirror(product)
        return product

    def edit_product(self, product_id: UUID, draft: ProductDraft) -> Product:
        draft.validate()
        product = self._catalog.edit(product_id, draft)
        self._products.save_mirror(product)
        return product

    def delete_product(self, product_id: UUID) -> None:
        self._catalog.delete(product_id)
        self._products.delete_mirror(product_id)
