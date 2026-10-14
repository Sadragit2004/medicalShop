# apps/product/signals.py
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.core.cache import cache

from .models import (
    Product,
    ProductGallery,
    ProductSaleType,
    ProductFeature,
    Brand,
    Category,
    Feature,
    FeatureValue,
    TypeProductTitle,
    Rating,
    Comment,
)


# ========================
# کلیدهای کش
# ========================
CACHE_KEYS = [
    "product_app:latest_products:v1",
    "product_app:popular_brands:v1",
    "product_app:rich_categories:v1",
]


def clear_all_product_caches():
    """پاک کردن تمام کلیدهای کش مرتبط با محصول"""
    for key in CACHE_KEYS:
        cache.delete(key)

    # اگر از versioning استفاده می‌کنید، نسخه رو هم افزایش بدید
    try:
        cache.incr("product_app:cache_version")
    except ValueError:
        cache.set("product_app:cache_version", 1, None)


# ========================
# ۱. محصول (Product)
# ========================
@receiver([post_save, post_delete], sender=Product, dispatch_uid="clear_cache_product")
def clear_cache_on_product_change(sender, instance, **kwargs):
    clear_all_product_caches()


# ========================
# ۲. گالری محصول (ProductGallery)
# ========================
@receiver([post_save, post_delete], sender=ProductGallery, dispatch_uid="clear_cache_gallery")
def clear_cache_on_gallery_change(sender, instance, **kwargs):
    clear_all_product_caches()


# ========================
# ۳. نوع فروش محصول (ProductSaleType)
# ========================
@receiver([post_save, post_delete], sender=ProductSaleType, dispatch_uid="clear_cache_saletype")
def clear_cache_on_saletype_change(sender, instance, **kwargs):
    clear_all_product_caches()


# ========================
# ۴. ویژگی محصول (ProductFeature)
# ========================
@receiver([post_save, post_delete], sender=ProductFeature, dispatch_uid="clear_cache_productfeature")
def clear_cache_on_productfeature_change(sender, instance, **kwargs):
    clear_all_product_caches()


# ========================
# ۵. برند (Brand)
# ========================
@receiver([post_save, post_delete], sender=Brand, dispatch_uid="clear_cache_brand")
def clear_cache_on_brand_change(sender, instance, **kwargs):
    clear_all_product_caches()


# ========================
# ۶. دسته‌بندی (Category)
# ========================
@receiver([post_save, post_delete], sender=Category, dispatch_uid="clear_cache_category")
def clear_cache_on_category_change(sender, instance, **kwargs):
    clear_all_product_caches()


# ========================
# ۷. ویژگی (Feature)
# ========================
@receiver([post_save, post_delete], sender=Feature, dispatch_uid="clear_cache_feature")
def clear_cache_on_feature_change(sender, instance, **kwargs):
    clear_all_product_caches()


# ========================
# ۸. مقدار ویژگی (FeatureValue)
# ========================
@receiver([post_save, post_delete], sender=FeatureValue, dispatch_uid="clear_cache_featurevalue")
def clear_cache_on_featurevalue_change(sender, instance, **kwargs):
    clear_all_product_caches()


# ========================
# ۹. نوع بسته‌بندی (TypeProductTitle)
# ========================
@receiver([post_save, post_delete], sender=TypeProductTitle, dispatch_uid="clear_cache_typetitle")
def clear_cache_on_typetitle_change(sender, instance, **kwargs):
    clear_all_product_caches()


# ========================
# ۱۰. امتیاز (Rating)
# ========================
@receiver([post_save, post_delete], sender=Rating, dispatch_uid="clear_cache_rating")
def clear_cache_on_rating_change(sender, instance, **kwargs):
    clear_all_product_caches()


# ========================
# ۱۱. کامنت (Comment)
# ========================
@receiver([post_save, post_delete], sender=Comment, dispatch_uid="clear_cache_comment")
def clear_cache_on_comment_change(sender, instance, **kwargs):
    clear_all_product_caches()


# ========================
# ۱۲. تغییرات ManyToMany محصول (category)
# ========================
@receiver(m2m_changed, sender=Product.category.through, dispatch_uid="clear_cache_product_m2m")
def clear_cache_on_product_m2m_change(sender, instance, action, **kwargs):
    if action in ("post_add", "post_remove", "post_clear"):
        clear_all_product_caches()


# ========================
# ۱۳. تغییرات ManyToMany ویژگی (categories)
# ========================
@receiver(m2m_changed, sender=Feature.categories.through, dispatch_uid="clear_cache_feature_m2m")
def clear_cache_on_feature_m2m_change(sender, instance, action, **kwargs):
    if action in ("post_add", "post_remove", "post_clear"):
        clear_all_product_caches()