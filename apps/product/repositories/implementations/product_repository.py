from typing import List, Optional
from ...models.product import Product

class ProductRepository:

    def get_by_id(self, product_id: int) -> Optional[Product]:
        try:
            return Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return None

    def get_by_slug(self, slug: str) -> Optional[Product]:
        try:
            return Product.objects.get(slug=slug, is_active=True)
        except Product.DoesNotExist:
            return None

    def get_all(self) -> List[Product]:
        return Product.objects.all()

    def get_active_products(self) -> List[Product]:
        return Product.objects.filter(is_active=True)

    def create(self, **kwargs) -> Product:
        return Product.objects.create(**kwargs)

    def update(self, product_id: int, **kwargs) -> Optional[Product]:
        try:
            product = Product.objects.get(id=product_id)
            for key, value in kwargs.items():
                setattr(product, key, value)
            product.save()
            return product
        except Product.DoesNotExist:
            return None

    def delete(self, product_id: int) -> bool:
        try:
            product = Product.objects.get(id=product_id)
            product.delete()
            return True
        except Product.DoesNotExist:
            return False

    def filter_products(self, **kwargs) -> List[Product]:
        return Product.objects.filter(**kwargs)