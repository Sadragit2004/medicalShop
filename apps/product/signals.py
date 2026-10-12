
from django.apps import apps
from django.core.cache import cache
from django.db.models.signals import (
    post_save,
    post_delete,
    m2m_changed,
)
from django.dispatch import receiver


POPULAR_BRANDS_CACHE_KEY = "product_app:popular_brands:v1"
RICH_CATEGORIES_CACHE_KEY = "product_app:rich_categories:v1"
LATEST_PRODUCTS_CACHE_KEY = "product_app:latest_products:v1"


def invalidate_product_app_cache(**kwargs):
    cache.delete_many([
        POPULAR_BRANDS_CACHE_KEY,
        RICH_CATEGORIES_CACHE_KEY,
        LATEST_PRODUCTS_CACHE_KEY,
    ])


PRODUCT_CACHE_MODEL_NAMES = {
    "Product",
    "ProductSaleType",
    "ProductGallery",
    "ProductFeature",
    "Category",
    "Brand",
    "Feature",
    "FeatureValue",
    "Rating",
    "Comment",
    "DiscountBasket",
    "DiscountDetail",
    "Copon",
    "ProductPriceHistory",
    "ProductStockHistory",
}


def connect_product_cache_signals():
    for model in apps.get_models():
        if model.__name__ not in PRODUCT_CACHE_MODEL_NAMES:
            continue

        post_save.connect(
            invalidate_product_app_cache,
            sender=model,
            dispatch_uid=f"product_cache_save_{model._meta.label_lower}",
            weak=False,
        )

        post_delete.connect(
            invalidate_product_app_cache,
            sender=model,
            dispatch_uid=f"product_cache_delete_{model._meta.label_lower}",
            weak=False,
        )


@receiver(m2m_changed)
def invalidate_product_cache_on_m2m_change(
    sender,
    action,
    **kwargs,
):
    if action not in {"post_add", "post_remove", "post_clear"}:
        return

    model_names = {
        "Product",
        "Category",
        "Brand",
        "Feature",
        "FeatureValue",
        "DiscountBasket",
        "DiscountDetail",
    }

    if (
        sender._meta.app_label in {"product", "discount"}
        and (
            sender._meta.object_name in model_names
            or sender._meta.model_name in {
                "product_category",
                "feature_categories",
            }
        )
    ):
        invalidate_product_app_cache()