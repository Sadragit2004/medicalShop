from django.db import models
import os
from .base import BaseModel,BaseManager
from .category import ProductCategory
from django.core.exceptions import ValidationError

def brand_image_path(instance, filename):
    """مسیر ذخیره لوگوی برند"""
    ext = filename.split('.')[-1]
    filename = f"{instance.slug}.{ext}"
    return os.path.join('brands', filename)


class BrandManager(BaseManager):
    """
    Manager مخصوص برندها
    """

    def get_brands_with_product_count(self):
        """دریافت برندها همراه با تعداد محصولات"""
        from .product import Product

        brands = self.get_active()

        for brand in brands:
            brand.product_count = Product.objects.filter(
                brand=brand,
                is_active=True
            ).count()

        return brands

    def get_popular_brands(self, limit=10):
        """دریافت محبوب‌ترین برندها (بر اساس تعداد محصولات)"""
        from django.db.models import Count

        return self.filter(
            is_active=True,
            products__is_active=True
        ).annotate(
            product_count=Count('products')
        ).order_by('-product_count')[:limit]

    def create_brand(self, title, **extra_fields):
        """ایجاد برند جدید با اعتبارسنجی"""
        # بررسی وجود برند با همین عنوان
        if self.filter(title=title, is_active=True).exists():
            raise ValidationError(f"برند '{title}' از قبل وجود دارد")

        return self.create_record(title=title, **extra_fields)


class Brand(BaseModel):
    """
    برند محصولات
    """
    description = models.TextField(
        blank=True,
        verbose_name="توضیحات",
        help_text="توضیحات کامل برند، تاریخچه، و اطلاعات دیگر"
    )

    image = models.ImageField(
        upload_to=brand_image_path,
        null=True,
        blank=True,
        verbose_name="لوگوی برند",
        help_text="لوگوی برند با پس زمینه شفاف (PNG)"
    )

    website = models.URLField(
        blank=True,
        verbose_name="وب‌سایت",
        help_text="آدرس وب‌سایت رسمی برند"
    )

    # استفاده از Manager مخصوص
    objects = BrandManager()

    class Meta:
        verbose_name = "برند"
        verbose_name_plural = "برندها"
        ordering = ['title']

    # ========== CRUD OPERATIONS (اضافه بر BaseModel) ==========

    def get_products(self, **filters):
        """دریافت محصولات این برند"""
        from .product import Product

        queryset = Product.objects.filter(
            brand=self,
            is_active=True
        )

        if filters:
            queryset = queryset.filter(**filters)

        return queryset

    def get_products_count(self):
        """تعداد محصولات این برند"""
        return self.get_products().count()

    def get_categories(self):
        """دریافت دسته‌بندی‌هایی که این برند محصول دارد"""
        from .product import Product

        # گرفتن دسته‌بندی‌های متمایز از طریق محصولات
        return ProductCategory.objects.filter(
            products__brand=self,
            products__is_active=True,
            is_active=True
        ).distinct()

    def to_dict(self, fields=None, exclude=None):
        """
        تبدیل به دیکشنری (override از BaseModel)
        - اضافه کردن اطلاعات محصولات و دسته‌بندی‌ها
        """
        data = super().to_dict(fields, exclude)

        # اضافه کردن تعداد محصولات
        if 'products_count' not in data:
            data['products_count'] = self.get_products_count()

        # اضافه کردن دسته‌بندی‌ها
        if 'categories' not in data:
            categories = self.get_categories()
            data['categories'] = [
                {
                    'id': cat.id,
                    'title': cat.title,
                    'slug': cat.slug,
                }
                for cat in categories
            ]

        return data

    def get_absolute_url(self):
        """دریافت URL این برند"""
        from django.urls import reverse
        return reverse('product:brand_detail', kwargs={'slug': self.slug})

    def __str__(self):
        return self.title