from django.db import models
import os
import uuid
from django.utils import timezone
from .base import BaseModel, BaseManager

def gallery_image_path(instance, filename):
    """
    تولید مسیر فایل تصویر
    - محصول/اسلاگ-محصول/گالری/ترتیب-تصویر.extension
    """
    ext = filename.split('.')[-1]

    # استفاده از timestamp
    if hasattr(instance, 'created_at') and instance.created_at:
        timestamp = instance.created_at
    else:
        timestamp = timezone.now()

    # نام فایل: slug-timestamp-random
    unique_name = f"{instance.product.slug}-{timestamp.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"

    return os.path.join(
        'products',
        instance.product.slug,
        'gallery',
        f"{unique_name}.{ext}"
    )


class ProductGalleryManager(BaseManager):
    """
    Manager مخصوص گالری محصولات
    """

    def get_by_product(self, product_slug=None, product_id=None):
        """
        دریافت تصاویر گالری یک محصول
        """
        query = self.filter(is_active=True)

        if product_slug:
            from .product import Product
            try:
                product = Product.objects.get(slug=product_slug)
                query = query.filter(product=product)
            except Product.DoesNotExist:
                return self.none()
        elif product_id:
            query = query.filter(product_id=product_id)

        return query.order_by('sort_order', '-created_at')

    def get_main_images(self, product_slug=None, product_id=None):
        """دریافت تصاویر اصلی محصولات"""
        query = self.filter(is_active=True, is_main=True)

        if product_slug:
            from .product import Product
            try:
                product = Product.objects.get(slug=product_slug)
                query = query.filter(product=product)
            except Product.DoesNotExist:
                return self.none()
        elif product_id:
            query = query.filter(product_id=product_id)

        return query

    def create_gallery_image(self, product, image, title=None, is_main=False, sort_order=0):
        """
        ایجاد تصویر جدید در گالری
        """
        if is_main:
            self.filter(product=product, is_main=True).update(is_main=False)

        if not title:
            title = f"تصویر {self.filter(product=product).count() + 1}"

        gallery_image = self.create(
            product=product,
            title=title,
            image=image,
            is_main=is_main,
            sort_order=sort_order
        )

        return gallery_image

    def set_main_image(self, gallery_image_id):
        """
        تنظیم یک تصویر به عنوان تصویر اصلی
        """
        try:
            gallery_image = self.get(id=gallery_image_id)

            self.filter(
                product=gallery_image.product,
                is_main=True
            ).exclude(id=gallery_image_id).update(is_main=False)

            gallery_image.is_main = True
            gallery_image.save()

            return gallery_image
        except self.model.DoesNotExist:
            return None

    def reorder_images(self, product, new_order):
        """
        تغییر ترتیب تصاویر گالری
        """
        for index, gallery_id in enumerate(new_order):
            try:
                gallery_image = self.get(id=gallery_id, product=product)
                gallery_image.sort_order = index
                gallery_image.save()
            except self.model.DoesNotExist:
                continue

        return True


class ProductGallery(BaseModel):
    """
    گالری تصاویر محصول
    """
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='gallery_images',
        verbose_name="محصول",
        help_text="محصولی که این تصویر متعلق به آن است"
    )

    title = models.CharField(
        max_length=200,
        verbose_name="عنوان تصویر",
        blank=True,
        help_text="عنوان اختیاری برای تصویر"
    )

    image = models.ImageField(
        upload_to=gallery_image_path,
        verbose_name="تصویر",
        help_text="حداکثر سایز: 5MB، فرمت‌های مجاز: JPG, PNG, WEBP"
    )

    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name="ترتیب نمایش",
        help_text="تصاویر بر اساس این عدد مرتب می‌شوند (اعداد کوچکتر اول)"
    )

    is_main = models.BooleanField(
        default=False,
        verbose_name="تصویر اصلی",
        help_text="اگر فعال باشد، این تصویر به عنوان تصویر شاخص محصول نمایش داده می‌شود"
    )

    objects = ProductGalleryManager()

    class Meta:
        verbose_name = "تصویر گالری"
        verbose_name_plural = "تصاویر گالری"
        ordering = ['sort_order', '-created_at']

    def clean(self):
        """اعتبارسنجی سفارشی"""
        from django.core.exceptions import ValidationError

        if self.is_main and self.product_id:
            main_images = ProductGallery.objects.filter(
                product=self.product,
                is_main=True,
                is_active=True
            ).exclude(id=self.id)

            if main_images.exists():
                raise ValidationError(
                    "این محصول قبلاً یک تصویر اصلی دارد. "
                    "ابتدا تصویر اصلی فعلی را غیرفعال کنید."
                )

    def set_as_main(self):
        """
        تنظیم این تصویر به عنوان تصویر اصلی محصول
        """
        return ProductGallery.objects.set_main_image(self.id)

    def get_image_url(self, size=None):
        """
        دریافت URL تصویر
        """
        if not self.image:
            return None
        return self.image.url

    def get_next_image(self):
        """دریافت تصویر بعدی در گالری"""
        try:
            return ProductGallery.objects.filter(
                product=self.product,
                sort_order__gt=self.sort_order,
                is_active=True
            ).order_by('sort_order').first()
        except:
            return None

    def get_previous_image(self):
        """دریافت تصویر قبلی در گالری"""
        try:
            return ProductGallery.objects.filter(
                product=self.product,
                sort_order__lt=self.sort_order,
                is_active=True
            ).order_by('-sort_order').first()
        except:
            return None

    def move_up(self):
        """جابجایی تصویر به ترتیب بالاتر"""
        previous = self.get_previous_image()
        if previous:
            current_order = self.sort_order
            self.sort_order = previous.sort_order
            previous.sort_order = current_order
            self.save()
            previous.save()
        return self

    def move_down(self):
        """جابجایی تصویر به ترتیب پایین‌تر"""
        next_img = self.get_next_image()
        if next_img:
            current_order = self.sort_order
            self.sort_order = next_img.sort_order
            next_img.sort_order = current_order
            self.save()
            next_img.save()
        return self

    def __str__(self):
        if self.title:
            return f"{self.product.title} - {self.title}"
        return f"{self.product.title} - تصویر {self.id}"