from typing import List, Optional
from ...models.attribute import Attribute

class AttributeRepository:

    def get_by_id(self, attribute_id: int) -> Optional[Attribute]:
        try:
            return Attribute.objects.get(id=attribute_id)
        except Attribute.DoesNotExist:
            return None

    def get_by_slug(self, slug: str) -> Optional[Attribute]:
        try:
            return Attribute.objects.get(slug=slug)
        except Attribute.DoesNotExist:
            return None

    def get_all(self) -> List[Attribute]:
        return Attribute.objects.all()

    def get_active_attributes(self) -> List[Attribute]:
        return Attribute.objects.filter(is_active=True)

    def get_visible_attributes(self) -> List[Attribute]:
        return Attribute.objects.filter(is_active=True, is_visible=True)

    def get_filterable_attributes(self) -> List[Attribute]:
        return Attribute.objects.filter(is_active=True, is_filterable=True)

    def create(self, **kwargs) -> Attribute:
        return Attribute.objects.create(**kwargs)

    def update(self, attribute_id: int, **kwargs) -> Optional[Attribute]:
        try:
            attribute = Attribute.objects.get(id=attribute_id)
            for key, value in kwargs.items():
                setattr(attribute, key, value)
            attribute.save()
            return attribute
        except Attribute.DoesNotExist:
            return None

    def delete(self, attribute_id: int) -> bool:
        try:
            attribute = Attribute.objects.get(id=attribute_id)
            attribute.delete()
            return True
        except Attribute.DoesNotExist:
            return False

    def filter(self, **kwargs) -> List[Attribute]:
        return Attribute.objects.filter(**kwargs)

    def exists(self, **kwargs) -> bool:
        return Attribute.objects.filter(**kwargs).exists()