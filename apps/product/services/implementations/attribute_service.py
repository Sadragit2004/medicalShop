from typing import List, Dict, Any, Optional
from django.db import transaction
from django.core.exceptions import ValidationError

# IMPORT ها - اینها درست هستند:
from ..interfaces.attribute_service_interface import AttributeServiceInterface
from ...repositories.implementations.attribute_repository import AttributeRepository
from ...repositories.implementations.product_repository import ProductRepository

# import مدل‌ها
from ...models.attribute import Attribute, ProductAttributeValue
from ...models.product import Product

class AttributeService(AttributeServiceInterface):

    def __init__(self):
        self.attribute_repository = AttributeRepository()
        self.product_repository = ProductRepository()

    def create_attribute(self, data: Dict[str, Any]) -> Attribute:
        """ایجاد ویژگی جدید"""
        # اعتبارسنجی ساده
        if 'title' not in data or not data['title'].strip():
            raise ValidationError("عنوان ویژگی الزامی است")

        # ایجاد ویژگی
        return self.attribute_repository.create(**data)

    def update_attribute(self, attribute_id: int, data: Dict[str, Any]) -> Optional[Attribute]:
        """بروزرسانی ویژگی"""
        attribute = self.attribute_repository.get_by_id(attribute_id)
        if not attribute:
            return None

        # بروزرسانی ویژگی
        return self.attribute_repository.update(attribute_id, **data)

    def delete_attribute(self, attribute_id: int) -> bool:
        """حذف ویژگی"""
        return self.attribute_repository.delete(attribute_id)

    def get_attribute_by_id(self, attribute_id: int) -> Optional[Attribute]:
        """دریافت ویژگی بر اساس ID"""
        return self.attribute_repository.get_by_id(attribute_id)

    def get_all_attributes(self) -> List[Attribute]:
        """دریافت تمام ویژگی‌ها"""
        return self.attribute_repository.get_all()

    def get_active_attributes(self) -> List[Attribute]:
        """دریافت ویژگی‌های فعال"""
        return self.attribute_repository.get_active_attributes()

    def get_visible_attributes(self) -> List[Attribute]:
        """دریافت ویژگی‌های قابل نمایش"""
        return self.attribute_repository.get_visible_attributes()

    def get_filterable_attributes(self) -> List[Attribute]:
        """دریافت ویژگی‌های قابل فیلتر"""
        return self.attribute_repository.get_filterable_attributes()

    def set_product_attribute_value(
        self,
        product_id: int,
        attribute_id: int,
        value: Any
    ) -> ProductAttributeValue:
        """
        تنظیم مقدار ویژگی برای محصول
        """
        product = self.product_repository.get_by_id(product_id)
        if not product:
            raise ValidationError("محصول یافت نشد")

        attribute = self.attribute_repository.get_by_id(attribute_id)
        if not attribute:
            raise ValidationError("ویژگی یافت نشد")

        # اعتبارسنجی مقدار بر اساس نوع داده ویژگی
        self._validate_attribute_value(attribute, value)

        # ایجاد یا بروزرسانی مقدار
        attribute_value, created = ProductAttributeValue.objects.get_or_create(
            product=product,
            attribute=attribute,
            defaults={}
        )

        # تنظیم مقدار
        attribute_value.set_value(value)
        attribute_value.save()

        return attribute_value

    def get_product_attributes(self, product_id: int) -> List[Dict[str, Any]]:
        """
        دریافت ویژگی‌ها و مقادیر یک محصول
        """
        product = self.product_repository.get_by_id(product_id)
        if not product:
            return []

        # دریافت ویژگی‌های قابل نمایش
        attributes = self.get_visible_attributes()

        result = []
        for attribute in attributes:
            try:
                attribute_value = ProductAttributeValue.objects.get(
                    product=product,
                    attribute=attribute
                )
                value = attribute_value.get_value()
            except ProductAttributeValue.DoesNotExist:
                value = None

            result.append({
                'attribute': attribute,
                'value': value,
                'unit': attribute.unit,
                'data_type': attribute.data_type,
            })

        return result

    def _validate_attribute_value(self, attribute: Attribute, value: Any):
        """
        اعتبارسنجی مقدار بر اساس نوع داده ویژگی
        """
        if attribute.is_required and value in [None, '', []]:
            raise ValidationError(f"ویژگی '{attribute.title}' اجباری است")

        try:
            attribute.validate_value(value)
        except ValueError as e:
            raise ValidationError(str(e))

    @transaction.atomic
    def save_product_attributes(self, product_id: int, attribute_values: Dict[int, Any]) -> bool:
        """
        ذخیره مقادیر ویژگی‌های یک محصول
        """
        product = self.product_repository.get_by_id(product_id)
        if not product:
            return False

        for attribute_id, value in attribute_values.items():
            attribute = self.attribute_repository.get_by_id(attribute_id)
            if not attribute:
                continue

            # اگر مقدار خالی است و ویژگی اجباری نیست، حذف کن
            if value in [None, '', []] and not attribute.is_required:
                ProductAttributeValue.objects.filter(
                    product=product,
                    attribute=attribute
                ).delete()
                continue

            # تنظیم مقدار
            self.set_product_attribute_value(product_id, attribute_id, value)

        return True