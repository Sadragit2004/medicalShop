import json
from decimal import Decimal

from django.core.cache import cache
from django.db import models, transaction
from django.db.models import Avg, Count, Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, user_passes_test

from .models import (
    ProductPriceHistory,
    ProductStockHistory,
)

from apps.user.models.user import CustomUser

from apps.product.models import (
    Product,
    ProductSaleType,
    Category,
)

from apps.discount.models import (
    DiscountBasket,
    DiscountDetail,
)

from .cache import (
    cache,
    build_price_panel_cache_key,
    invalidate_price_panel_cache,
    PRODUCT_LIST_CACHE_TIMEOUT,
    PRODUCT_DETAIL_CACHE_TIMEOUT,
    HISTORY_CACHE_TIMEOUT,
    DASHBOARD_CACHE_TIMEOUT,
    CATEGORIES_CACHE_TIMEOUT,
)


def is_superuser(user):
    return user.is_authenticated and user.is_superuser


def is_staff_or_superuser(user):
    return user.is_authenticated and (
        user.is_staff or user.is_superuser
    )


def json_error(message, status=400):
    return JsonResponse(
        {
            "success": False,
            "error": message,
        },
        status=status,
    )


def parse_json_body(request):
    try:
        return json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return None


def get_user_name(user):
    mobile = getattr(user, "mobileNumber", None)

    if mobile:
        return str(mobile)

    return getattr(user, "username", str(user))


def safe_image_url(image):
    if not image:
        return None

    try:
        return image.url
    except (ValueError, AttributeError):
        return None


@login_required
@user_passes_test(is_superuser)
def showUiPrice(request):
    return render(
        request,
        "price_app/price.html",
    )


@csrf_exempt
@require_http_methods(["GET"])
@login_required
@user_passes_test(is_superuser)
def get_products_list(request):
    """
    Optimized product list.

    The important difference from the previous implementation is:
    - select_related for FK/OneToOne relations
    - Prefetch with to_attr
    - no Query inside product loop
    - current price history loaded in bulk
    - active discounts loaded in bulk
    - categories loaded in bulk
    - response cached
    """

    category_id = request.GET.get("category")
    search = request.GET.get("search", "").strip()

    cache_key = build_price_panel_cache_key(
        "products",
        category_id or "",
        search,
    )

    cached_data = cache.get(cache_key)

    if cached_data is not None:
        return JsonResponse(
            cached_data,
            json_dumps_params={
                "ensure_ascii": False,
            },
        )

    now = timezone.now()

    current_history_queryset = (
        ProductPriceHistory.objects
        .filter(is_current=True)
        .only(
            "id",
            "product_id",
            "sale_type_id",
            "price_old",
            "price_new",
            "percent_change",
        )
    )

    active_sale_types_queryset = (
        ProductSaleType.objects
        .filter(isActive=True)
        .only(
            "id",
            "product_id",
            "typeSale",
            "price",
            "finalPrice",
            "memberCarton",
            "limitedSale",
            "title",
        )
    )

    active_discount_queryset = (
        DiscountDetail.objects
        .filter(
            discountBasket__isActive=True,
            discountBasket__startDate__lte=now,
            discountBasket__endDate__gte=now,
        )
        .select_related("discountBasket")
        .only(
            "id",
            "product_id",
            "discountBasket_id",
            "discountBasket__id",
            "discountBasket__discount",
            "discountBasket__startDate",
            "discountBasket__endDate",
        )
    )

    products = (
        Product.objects
        .filter(isActive=True)
        .select_related(
            "brand",
            "typetitle",
        )
        .prefetch_related(
            Prefetch(
                "saleTypes",
                queryset=active_sale_types_queryset,
                to_attr="price_panel_sale_types",
            ),
            Prefetch(
                "category",
                queryset=Category.objects.only(
                    "id",
                    "title",
                ),
                to_attr="price_panel_categories",
            ),
            Prefetch(
                "price_history",
                queryset=current_history_queryset,
                to_attr="price_panel_current_history",
            ),
            Prefetch(
                "productOfDiscount",
                queryset=active_discount_queryset,
                to_attr="price_panel_discounts",
            ),
        )
        .only(
            "id",
            "title",
            "slug",
            "mainImage",
            "stock",
            "isActive",
            "brand_id",
            "brand__id",
            "brand__title",
            "typetitle_id",
            "typetitle__id",
            "typetitle__title",
        )
    )

    if category_id:
        products = products.filter(
            category__id=category_id
        )

    if search:
        products = products.filter(
            title__icontains=search
        )

    products = products.distinct()

    data = []

    for product in products:
        sale_types = []

        for sale in product.price_panel_sale_types:
            sale_types.append(
                {
                    "id": sale.id,
                    "typeSale": sale.typeSale,
                    "typeSale_display": sale.get_typeSale_display(),
                    "price": sale.price,
                    "finalPrice": sale.finalPrice,
                    "memberCarton": sale.memberCarton,
                    "limitedSale": sale.limitedSale,
                    "title": sale.title or "پایه",
                }
            )

        categories = [
            {
                "id": category.id,
                "title": category.title,
            }
            for category in product.price_panel_categories
        ]

        current_history = (
            product.price_panel_current_history[0]
            if product.price_panel_current_history
            else None
        )

        original_price = (
            sale_types[0]["price"]
            if sale_types
            else 0
        )

        discounted_price = original_price
        discount_percent = 0
        has_active_discount = False
        discount_basket_id = None
        discount_detail_id = None

        if product.price_panel_discounts:
            discount_detail = product.price_panel_discounts[0]
            basket = discount_detail.discountBasket

            has_active_discount = True
            discount_percent = basket.discount

            discounted_price = (
                original_price
                - int(
                    (
                        original_price
                        * discount_percent
                    )
                    / 100
                )
            )

            discount_basket_id = basket.id
            discount_detail_id = discount_detail.id

        data.append(
            {
                "id": product.id,
                "title": product.title,
                "slug": product.slug,
                "mainImage": safe_image_url(
                    product.mainImage
                ),
                "stock": product.stock,
                "isActive": product.isActive,
                "category": categories,
                "brand": (
                    product.brand.title
                    if product.brand
                    else None
                ),
                "sale_types": sale_types,
                "product_type_title": (
                    product.typetitle.title
                    if product.typetitle
                    else "فیزیکی"
                ),
                "original_price": original_price,
                "discounted_price": discounted_price,
                "discount_percent": discount_percent,
                "has_active_discount": has_active_discount,
                "discount_basket_id": discount_basket_id,
                "discount_detail_id": discount_detail_id,
                "last_price": (
                    {
                        "price_old": current_history.price_old,
                        "price_new": current_history.price_new,
                        "percent_change": (
                            float(
                                current_history.percent_change
                            )
                            if current_history.percent_change
                            else 0
                        ),
                    }
                    if current_history
                    else None
                ),
            }
        )

    response_data = {
        "success": True,
        "count": len(data),
        "products": data,
    }

    cache.set(
        cache_key,
        response_data,
        timeout=PRODUCT_LIST_CACHE_TIMEOUT,
    )

    return JsonResponse(
        response_data,
        json_dumps_params={
            "ensure_ascii": False,
        },
    )


@csrf_exempt
@require_http_methods(["GET"])
@login_required
@user_passes_test(is_staff_or_superuser)
def get_product_detail(request, product_id):
    cache_key = build_price_panel_cache_key(
        "product-detail",
        product_id,
    )

    cached_data = cache.get(cache_key)

    if cached_data is not None:
        return JsonResponse(
            cached_data,
            json_dumps_params={
                "ensure_ascii": False,
            },
        )

    try:
        product = (
            Product.objects
            .filter(
                id=product_id,
                isActive=True,
            )
            .select_related()
            .prefetch_related(
                Prefetch(
                    "saleTypes",
                    queryset=ProductSaleType.objects.filter(
                        isActive=True
                    ).only(
                        "id",
                        "product_id",
                        "typeSale",
                        "price",
                        "finalPrice",
                        "memberCarton",
                        "limitedSale",
                        "title",
                    ),
                    to_attr="price_panel_sale_types",
                )
            )
            .only(
                "id",
                "title",
                "slug",
                "mainImage",
                "description",
                "shortDescription",
                "stock",
                "isActive",
            )
            .first()
        )
    except Product.DoesNotExist:
        product = None

    if not product:
        return json_error(
            "محصول یافت نشد",
            status=404,
        )

    sale_types = []

    for sale in product.price_panel_sale_types:
        sale_types.append(
            {
                "id": sale.id,
                "typeSale": sale.typeSale,
                "typeSale_display": sale.get_typeSale_display(),
                "price": sale.price,
                "finalPrice": sale.finalPrice,
                "memberCarton": sale.memberCarton,
                "limitedSale": sale.limitedSale,
                "title": sale.title or "پایه",
            }
        )

    price_history = (
        ProductPriceHistory.objects
        .filter(product_id=product_id)
        .select_related("sale_type")
        .only(
            "id",
            "product_id",
            "sale_type_id",
            "price_old",
            "price_new",
            "percent_change",
            "change_type",
            "created_at",
            "source",
            "note",
        )
        .order_by("-created_at")[:20]
    )

    stock_history = (
        ProductStockHistory.objects
        .filter(product_id=product_id)
        .only(
            "id",
            "product_id",
            "stock_old",
            "stock_new",
            "change_type",
            "created_at",
            "changed_by_name",
        )
        .order_by("-created_at")[:10]
    )

    history_data = [
        {
            "id": hist.id,
            "price_old": hist.price_old,
            "price_new": hist.price_new,
            "percent_change": (
                float(hist.percent_change)
                if hist.percent_change
                else 0
            ),
            "change_type": hist.change_type,
            "created_at": hist.created_at.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "source": hist.get_source_display(),
            "note": hist.note,
        }
        for hist in price_history
    ]

    stock_history_data = [
        {
            "id": stock.id,
            "stock_old": stock.stock_old,
            "stock_new": stock.stock_new,
            "change_type": stock.get_change_type_display(),
            "created_at": stock.created_at.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "changed_by": stock.changed_by_name,
        }
        for stock in stock_history
    ]

    now = timezone.now()

    discount_detail = (
        DiscountDetail.objects
        .filter(
            product_id=product_id,
            discountBasket__isActive=True,
            discountBasket__startDate__lte=now,
            discountBasket__endDate__gte=now,
        )
        .select_related("discountBasket")
        .only(
            "id",
            "product_id",
            "discountBasket_id",
            "discountBasket__id",
            "discountBasket__discount",
            "discountBasket__startDate",
            "discountBasket__endDate",
        )
        .first()
    )

    discount_info = None

    if discount_detail:
        basket = discount_detail.discountBasket

        original_price = (
            sale_types[0]["price"]
            if sale_types
            else 0
        )

        discount_info = {
            "discount_percent": basket.discount,
            "original_price": original_price,
            "discounted_price": (
                original_price
                - int(
                    (
                        original_price
                        * basket.discount
                    )
                    / 100
                )
            ),
            "start_date": basket.startDate.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "end_date": basket.endDate.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "discount_basket_id": basket.id,
            "discount_detail_id": discount_detail.id,
        }

    response_data = {
        "success": True,
        "product": {
            "id": product.id,
            "title": product.title,
            "slug": product.slug,
            "mainImage": safe_image_url(
                product.mainImage
            ),
            "description": product.description,
            "shortDescription": product.shortDescription,
            "stock": product.stock,
            "isActive": product.isActive,
            "sale_types": sale_types,
            "price_history": history_data,
            "stock_history": stock_history_data,
            "discount_info": discount_info,
        },
    }

    cache.set(
        cache_key,
        response_data,
        timeout=PRODUCT_DETAIL_CACHE_TIMEOUT,
    )

    return JsonResponse(
        response_data,
        json_dumps_params={
            "ensure_ascii": False,
        },
    )


@csrf_exempt
@require_http_methods(["POST"])
@login_required
@user_passes_test(is_superuser)
def update_product_price(request):
    data = parse_json_body(request)

    if data is None:
        return json_error(
            "داده نامعتبر",
            status=400,
        )

    product_id = data.get("product_id")
    sale_type_id = data.get("sale_type_id")
    new_price = data.get("price")

    source = data.get(
        "source",
        "manual_phone",
    )

    source_detail = data.get(
        "source_detail",
        "",
    )

    note = data.get(
        "note",
        "",
    )

    if product_id is None or new_price is None:
        return json_error(
            "product_id و price الزامی هستند",
            status=400,
        )

    try:
        new_price_int = int(new_price)

        if new_price_int < 0:
            raise ValueError

    except (TypeError, ValueError):
        return json_error(
            "قیمت نامعتبر است",
            status=400,
        )

    now = timezone.now()
    user = request.user
    user_name = get_user_name(user)

    with transaction.atomic():

        try:
            product = (
                Product.objects
                .select_for_update()
                .get(id=product_id)
            )
        except Product.DoesNotExist:
            return json_error(
                "محصول یافت نشد",
                status=404,
            )

        if sale_type_id:
            try:
                sale_type = (
                    ProductSaleType.objects
                    .select_for_update()
                    .get(
                        id=sale_type_id,
                        product_id=product_id,
                    )
                )
            except ProductSaleType.DoesNotExist:
                return json_error(
                    "نوع فروش یافت نشد",
                    status=404,
                )
        else:
            sale_type = (
                ProductSaleType.objects
                .select_for_update()
                .filter(
                    product_id=product_id,
                    isActive=True,
                )
                .first()
            )

            if not sale_type:
                return json_error(
                    "نوع فروشی برای این محصول تعریف نشده",
                    status=400,
                )

        old_price = sale_type.price

        if old_price == new_price_int:
            return JsonResponse(
                {
                    "success": True,
                    "message": "قیمت تغییری نکرده است",
                    "data": {
                        "product_id": product_id,
                        "old_price": old_price,
                        "new_price": new_price_int,
                        "percent_change": 0,
                    },
                },
                json_dumps_params={
                    "ensure_ascii": False,
                },
            )

        percent_change = (
            round(
                (
                    (new_price_int - old_price)
                    / old_price
                )
                * 100,
                2,
            )
            if old_price > 0
            else 0
        )

        change_type = (
            "increase"
            if new_price_int > old_price
            else "decrease"
        )

        sale_type.price = new_price_int
        sale_type.finalPrice = new_price_int
        sale_type.updatedAt = now

        sale_type.save(
            update_fields=[
                "price",
                "finalPrice",
                "updatedAt",
            ]
        )

        ProductPriceHistory.objects.filter(
            product_id=product_id,
            sale_type_id=sale_type.id,
            is_current=True,
        ).update(
            is_current=False
        )

        price_history = ProductPriceHistory.objects.create(
            product_id=product_id,
            sale_type_id=sale_type.id,
            price_old=old_price,
            price_new=new_price_int,
            percent_change=Decimal(
                str(percent_change)
            ),
            change_type=change_type,
            changed_by=user,
            changed_by_name=user_name,
            source=source,
            source_detail=source_detail,
            note=note,
            is_current=True,
            created_at=now,
        )

    invalidate_price_panel_cache()

    return JsonResponse(
        {
            "success": True,
            "message": "قیمت با موفقیت به روز شد",
            "data": {
                "id": price_history.id,
                "product_id": product_id,
                "product_title": product.title,
                "sale_type_id": sale_type.id,
                "old_price": old_price,
                "new_price": new_price_int,
                "percent_change": float(
                    percent_change
                ),
                "change_type": change_type,
                "created_at": price_history.created_at.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            },
        },
        json_dumps_params={
            "ensure_ascii": False,
        },
    )


@csrf_exempt
@require_http_methods(["POST"])
@login_required
@user_passes_test(is_superuser)
def toggle_product_with_stock_management(
    request,
    product_id,
):
    with transaction.atomic():

        try:
            product = (
                Product.objects
                .select_for_update()
                .get(id=product_id)
            )
        except Product.DoesNotExist:
            return json_error(
                "محصول یافت نشد",
                status=404,
            )

        old_stock = product.stock
        user = request.user
        user_name = get_user_name(user)

        if old_stock > 0:

            ProductStockHistory.objects.create(
                product_id=product_id,
                stock_old=old_stock,
                stock_new=0,
                change_type="stock_off",
                saved_stock_before_disable=old_stock,
                changed_by=user,
                changed_by_name=user_name,
                note=(
                    f"موجودی از {old_stock} "
                    "به صفر تنظیم شد."
                ),
            )

            product.stock = 0

            product.save(
                update_fields=["stock"]
            )

            new_stock = 0
            message = "موجودی به صفر رسید"

        else:

            last_record = (
                ProductStockHistory.objects
                .filter(
                    product_id=product_id,
                    change_type="stock_off",
                    saved_stock_before_disable__isnull=False,
                    saved_stock_before_disable__gt=0,
                )
                .order_by("-created_at")
                .only(
                    "saved_stock_before_disable"
                )
                .first()
            )

            restored_stock = (
                last_record.saved_stock_before_disable
                if last_record
                else 1
            )

            ProductStockHistory.objects.create(
                product_id=product_id,
                stock_old=old_stock,
                stock_new=restored_stock,
                change_type="stock_on",
                saved_stock_before_disable=None,
                changed_by=user,
                changed_by_name=user_name,
                note=(
                    f"موجودی از {old_stock} "
                    f"به {restored_stock} بازیابی شد"
                ),
            )

            product.stock = restored_stock

            product.save(
                update_fields=["stock"]
            )

            new_stock = restored_stock
            message = (
                f"موجودی به {restored_stock} بازگشت"
            )

    invalidate_price_panel_cache()

    return JsonResponse(
        {
            "success": True,
            "product_id": product_id,
            "isActive": product.isActive,
            "stock": new_stock,
            "old_stock": old_stock,
            "restored_from": (
                new_stock
                if old_stock == 0
                else None
            ),
            "message": message,
        },
        json_dumps_params={
            "ensure_ascii": False,
        },
    )


@csrf_exempt
@require_http_methods(["POST"])
@login_required
@user_passes_test(is_superuser)
def set_product_discount(request):
    data = parse_json_body(request)

    if data is None:
        return json_error(
            "داده نامعتبر",
            status=400,
        )

    product_id = data.get("product_id")
    discount_percent = data.get(
        "discount_percent"
    )

    if not product_id:
        return json_error(
            "product_id الزامی است",
            status=400,
        )

    if discount_percent is None:
        return json_error(
            "درصد تخفیف الزامی است",
            status=400,
        )

    try:
        discount_percent = int(
            discount_percent
        )
    except (TypeError, ValueError):
        return json_error(
            "درصد تخفیف نامعتبر است",
            status=400,
        )

    if not 0 <= discount_percent <= 100:
        return json_error(
            "درصد تخفیف باید بین 0 تا 100 باشد",
            status=400,
        )

    now = timezone.now()

    with transaction.atomic():

        try:
            product = (
                Product.objects
                .select_for_update()
                .get(id=product_id)
            )
        except Product.DoesNotExist:
            return json_error(
                "محصول یافت نشد",
                status=404,
            )

        sale_type = (
            ProductSaleType.objects
            .filter(
                product_id=product_id,
                isActive=True,
            )
            .only(
                "id",
                "price",
            )
            .first()
        )

        if not sale_type:
            return json_error(
                "نوع فروشی برای این محصول تعریف نشده",
                status=400,
            )

        original_price = sale_type.price

        existing_detail = (
            DiscountDetail.objects
            .select_for_update()
            .filter(
                product_id=product_id,
                discountBasket__isActive=True,
            )
            .select_related("discountBasket")
            .first()
        )

        if discount_percent == 0:

            if existing_detail:
                basket = (
                    existing_detail.discountBasket
                )

                basket.isActive = False

                basket.save(
                    update_fields=["isActive"]
                )

                existing_detail.delete()

            invalidate_price_panel_cache()

            return JsonResponse(
                {
                    "success": True,
                    "message": (
                        "تخفیف محصول با موفقیت حذف شد"
                        if existing_detail
                        else "محصول تخفیفی ندارد"
                    ),
                    "data": {
                        "product_id": product_id,
                        "product_title": product.title,
                        "discount_percent": 0,
                        "original_price": original_price,
                        "discounted_price": original_price,
                        "has_discount": False,
                    },
                },
                json_dumps_params={
                    "ensure_ascii": False,
                },
            )

        discounted_price = (
            original_price
            - int(
                (
                    original_price
                    * discount_percent
                )
                / 100
            )
        )

        if existing_detail:

            basket = existing_detail.discountBasket

            basket.discount = discount_percent
            basket.startDate = now
            basket.endDate = (
                now + timezone.timedelta(days=30)
            )
            basket.isActive = True
            basket.discountTitle = (
                f"تخفیف ویژه "
                f"{product.title} - "
                f"{discount_percent}%"
            )

            basket.save(
                update_fields=[
                    "discount",
                    "startDate",
                    "endDate",
                    "isActive",
                    "discountTitle",
                ]
            )

            detail_id = existing_detail.id
            basket_id = basket.id

        else:

            basket = DiscountBasket.objects.create(
                discountTitle=(
                    f"تخفیف ویژه "
                    f"{product.title} - "
                    f"{discount_percent}%"
                ),
                startDate=now,
                endDate=(
                    now + timezone.timedelta(days=30)
                ),
                discount=discount_percent,
                isActive=True,
                isamzing=False,
            )

            detail = DiscountDetail.objects.create(
                discountBasket=basket,
                product_id=product_id,
            )

            detail_id = detail.id
            basket_id = basket.id

    invalidate_price_panel_cache()

    return JsonResponse(
        {
            "success": True,
            "message": (
                "تخفیف محصول با موفقیت "
                "به‌روزرسانی شد"
                if existing_detail
                else "تخفیف محصول با موفقیت ایجاد شد"
            ),
            "data": {
                "product_id": product_id,
                "product_title": product.title,
                "discount_percent": discount_percent,
                "original_price": original_price,
                "discounted_price": discounted_price,
                "discount_basket_id": basket_id,
                "discount_detail_id": detail_id,
                "has_discount": True,
                "start_date": basket.startDate.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "end_date": basket.endDate.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            },
        },
        json_dumps_params={
            "ensure_ascii": False,
        },
    )


@csrf_exempt
@require_http_methods(["GET"])
@login_required
@user_passes_test(is_staff_or_superuser)
def get_product_discount_info(
    request,
    product_id,
):
    cache_key = build_price_panel_cache_key(
        "product-discount",
        product_id,
    )

    cached_data = cache.get(cache_key)

    if cached_data is not None:
        return JsonResponse(
            cached_data,
            json_dumps_params={
                "ensure_ascii": False,
            },
        )

    try:
        product = (
            Product.objects
            .only(
                "id",
            )
            .get(id=product_id)
        )
    except Product.DoesNotExist:
        return json_error(
            "محصول یافت نشد",
            status=404,
        )

    sale_type = (
        ProductSaleType.objects
        .filter(
            product_id=product_id,
            isActive=True,
        )
        .only("price")
        .first()
    )

    if not sale_type:
        return json_error(
            "نوع فروشی برای این محصول تعریف نشده",
            status=400,
        )

    original_price = sale_type.price
    now = timezone.now()

    discount_detail = (
        DiscountDetail.objects
        .filter(
            product_id=product_id,
            discountBasket__isActive=True,
            discountBasket__startDate__lte=now,
            discountBasket__endDate__gte=now,
        )
        .select_related("discountBasket")
        .only(
            "id",
            "discountBasket_id",
            "discountBasket__discount",
            "discountBasket__startDate",
            "discountBasket__endDate",
            "discountBasket__isActive",
        )
        .first()
    )

    if discount_detail:
        basket = discount_detail.discountBasket

        discounted_price = (
            original_price
            - int(
                (
                    original_price
                    * basket.discount
                )
                / 100
            )
        )

        response_data = {
            "success": True,
            "has_discount": True,
            "data": {
                "discount_percent": basket.discount,
                "original_price": original_price,
                "discounted_price": discounted_price,
                "start_date": basket.startDate.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "end_date": basket.endDate.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "discount_basket_id": basket.id,
                "discount_detail_id": discount_detail.id,
                "is_active": basket.isActive,
            },
        }

    else:

        response_data = {
            "success": True,
            "has_discount": False,
            "data": {
                "original_price": original_price,
                "discounted_price": original_price,
                "discount_percent": 0,
            },
        }

    cache.set(
        cache_key,
        response_data,
        timeout=PRODUCT_DETAIL_CACHE_TIMEOUT,
    )

    return JsonResponse(
        response_data,
        json_dumps_params={
            "ensure_ascii": False,
        },
    )


@csrf_exempt
@require_http_methods(["POST"])
@login_required
@user_passes_test(is_superuser)
def set_product_stock_to_zero(
    request,
    product_id,
):
    with transaction.atomic():

        try:
            product = (
                Product.objects
                .select_for_update()
                .get(id=product_id)
            )
        except Product.DoesNotExist:
            return json_error(
                "محصول یافت نشد",
                status=404,
            )

        old_stock = product.stock

        if old_stock == 0:
            return JsonResponse(
                {
                    "success": True,
                    "message": (
                        "موجودی محصول در حال حاضر صفر است"
                    ),
                    "product_id": product_id,
                    "stock": 0,
                    "isActive": product.isActive,
                },
                json_dumps_params={
                    "ensure_ascii": False,
                },
            )

        user = request.user
        user_name = get_user_name(user)

        ProductStockHistory.objects.create(
            product_id=product_id,
            stock_old=old_stock,
            stock_new=0,
            change_type="set_to_zero",
            saved_stock_before_disable=old_stock,
            changed_by=user,
            changed_by_name=user_name,
            note=(
                f"موجودی از {old_stock} "
                "به صفر تنظیم شد. "
                "محصول فعال باقی ماند."
            ),
        )

        product.stock = 0

        product.save(
            update_fields=["stock"]
        )

    invalidate_price_panel_cache()

    return JsonResponse(
        {
            "success": True,
            "product_id": product_id,
            "isActive": product.isActive,
            "stock": 0,
            "old_stock": old_stock,
            "message": (
                "موجودی محصول با موفقیت به صفر رسید"
            ),
        },
        json_dumps_params={
            "ensure_ascii": False,
        },
    )


@csrf_exempt
@require_http_methods(["POST"])
@login_required
@user_passes_test(is_superuser)
def restore_product_stock(
    request,
    product_id,
):
    with transaction.atomic():

        try:
            product = (
                Product.objects
                .select_for_update()
                .get(id=product_id)
            )
        except Product.DoesNotExist:
            return json_error(
                "محصول یافت نشد",
                status=404,
            )

        old_stock = product.stock

        last_zero_record = (
            ProductStockHistory.objects
            .filter(
                product_id=product_id,
                change_type="set_to_zero",
                saved_stock_before_disable__isnull=False,
                saved_stock_before_disable__gt=0,
            )
            .order_by("-created_at")
            .only(
                "saved_stock_before_disable"
            )
            .first()
        )

        if not last_zero_record:
            return json_error(
                "هیچ موجودی قبلی برای بازیابی یافت نشد",
                status=400,
            )

        restored_stock = (
            last_zero_record.saved_stock_before_disable
        )

        user = request.user
        user_name = get_user_name(user)

        ProductStockHistory.objects.create(
            product_id=product_id,
            stock_old=old_stock,
            stock_new=restored_stock,
            change_type="restore_stock",
            saved_stock_before_disable=None,
            changed_by=user,
            changed_by_name=user_name,
            note=(
                f"موجودی از {old_stock} "
                f"به {restored_stock} بازیابی شد"
            ),
        )

        product.stock = restored_stock

        product.save(
            update_fields=["stock"]
        )

    invalidate_price_panel_cache()

    return JsonResponse(
        {
            "success": True,
            "product_id": product_id,
            "isActive": product.isActive,
            "stock": product.stock,
            "old_stock": old_stock,
            "restored_from": restored_stock,
            "message": (
                f"موجودی محصول با موفقیت "
                f"به {restored_stock} بازیابی شد"
            ),
        },
        json_dumps_params={
            "ensure_ascii": False,
        },
    )


@csrf_exempt
@require_http_methods(["POST"])
@login_required
@user_passes_test(is_superuser)
def update_product_stock(
    request,
    product_id,
):
    data = parse_json_body(request)

    if data is None:
        return json_error(
            "داده نامعتبر",
            status=400,
        )

    new_stock = data.get("stock")
    change_type = data.get(
        "change_type",
        "manual",
    )
    note = data.get(
        "note",
        "",
    )

    if new_stock is None:
        return json_error(
            "مقدار stock الزامی است",
            status=400,
        )

    try:
        new_stock = int(new_stock)

        if new_stock < 0:
            raise ValueError

    except (TypeError, ValueError):
        return json_error(
            "مقدار stock نامعتبر است",
            status=400,
        )

    with transaction.atomic():

        try:
            product = (
                Product.objects
                .select_for_update()
                .get(id=product_id)
            )
        except Product.DoesNotExist:
            return json_error(
                "محصول یافت نشد",
                status=404,
            )

        old_stock = product.stock

        if old_stock == new_stock:
            return JsonResponse(
                {
                    "success": True,
                    "message": (
                        "موجودی تغییری نکرده است"
                    ),
                },
                json_dumps_params={
                    "ensure_ascii": False,
                },
            )

        user = request.user
        user_name = get_user_name(user)

        ProductStockHistory.objects.create(
            product_id=product_id,
            stock_old=old_stock,
            stock_new=new_stock,
            change_type=change_type,
            saved_stock_before_disable=None,
            changed_by=user,
            changed_by_name=user_name,
            note=note,
        )

        product.stock = new_stock

        product.save(
            update_fields=["stock"]
        )

    invalidate_price_panel_cache()

    return JsonResponse(
        {
            "success": True,
            "product_id": product_id,
            "product_title": product.title,
            "old_stock": old_stock,
            "new_stock": product.stock,
            "message": (
                "موجودی با موفقیت به روز شد"
            ),
        },
        json_dumps_params={
            "ensure_ascii": False,
        },
    )


@csrf_exempt
@require_http_methods(["GET"])
@login_required
@user_passes_test(is_staff_or_superuser)
def get_product_stock_history(
    request,
    product_id,
):
    try:
        limit = int(
            request.GET.get(
                "limit",
                20,
            )
        )
    except ValueError:
        limit = 20

    limit = max(
        1,
        min(limit, 100),
    )

    cache_key = build_price_panel_cache_key(
        "stock-history",
        product_id,
        limit,
    )

    cached_data = cache.get(cache_key)

    if cached_data is not None:
        return JsonResponse(
            cached_data,
            json_dumps_params={
                "ensure_ascii": False,
            },
        )

    try:
        product = (
            Product.objects
            .only(
                "id",
                "title",
                "stock",
                "isActive",
            )
            .get(id=product_id)
        )
    except Product.DoesNotExist:
        return json_error(
            "محصول یافت نشد",
            status=404,
        )

    stock_history = (
        ProductStockHistory.objects
        .filter(product_id=product_id)
        .only(
            "id",
            "stock_old",
            "stock_new",
            "saved_stock_before_disable",
            "change_type",
            "changed_by_name",
            "note",
            "created_at",
        )
        .order_by("-created_at")[:limit]
    )

    history_data = [
        {
            "id": hist.id,
            "stock_old": hist.stock_old,
            "stock_new": hist.stock_new,
            "saved_stock_before_disable": (
                hist.saved_stock_before_disable
            ),
            "change_type": hist.change_type,
            "change_type_display": (
                hist.get_change_type_display()
            ),
            "changed_by": hist.changed_by_name,
            "note": hist.note,
            "created_at": hist.created_at.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        }
        for hist in stock_history
    ]

    response_data = {
        "success": True,
        "product_id": product_id,
        "product_title": product.title,
        "current_stock": product.stock,
        "isActive": product.isActive,
        "history": history_data,
        "count": len(history_data),
    }

    cache.set(
        cache_key,
        response_data,
        timeout=HISTORY_CACHE_TIMEOUT,
    )

    return JsonResponse(
        response_data,
        json_dumps_params={
            "ensure_ascii": False,
        },
    )


@csrf_exempt
@require_http_methods(["GET"])
@login_required
@user_passes_test(is_staff_or_superuser)
def get_price_history(
    request,
    product_id,
):
    try:
        limit = int(
            request.GET.get(
                "limit",
                30,
            )
        )
    except ValueError:
        limit = 30

    limit = max(
        1,
        min(limit, 100),
    )

    sale_type_id = request.GET.get(
        "sale_type_id"
    )

    cache_key = build_price_panel_cache_key(
        "price-history",
        product_id,
        sale_type_id or "",
        limit,
    )

    cached_data = cache.get(cache_key)

    if cached_data is not None:
        return JsonResponse(
            cached_data,
            json_dumps_params={
                "ensure_ascii": False,
            },
        )

    try:
        product = (
            Product.objects
            .only(
                "id",
                "title",
            )
            .get(id=product_id)
        )
    except Product.DoesNotExist:
        return json_error(
            "محصول یافت نشد",
            status=404,
        )

    history_queryset = (
        ProductPriceHistory.objects
        .filter(product_id=product_id)
        .only(
            "id",
            "product_id",
            "sale_type_id",
            "price_old",
            "price_new",
            "percent_change",
            "change_type",
            "source",
            "source_detail",
            "changed_by_name",
            "note",
            "created_at",
        )
    )

    if sale_type_id:
        history_queryset = (
            history_queryset.filter(
                sale_type_id=sale_type_id
            )
        )

    history_queryset = (
        history_queryset
        .order_by("-created_at")
        [:limit]
    )

    history_data = [
        {
            "id": hist.id,
            "price_old": hist.price_old,
            "price_new": hist.price_new,
            "percent_change": (
                float(hist.percent_change)
                if hist.percent_change
                else 0
            ),
            "change_type": hist.change_type,
            "change_type_display": (
                hist.get_change_type_display()
            ),
            "source": hist.get_source_display(),
            "source_detail": hist.source_detail,
            "changed_by": hist.changed_by_name,
            "note": hist.note,
            "created_at": hist.created_at.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        }
        for hist in history_queryset
    ]

    stats_queryset = ProductPriceHistory.objects.filter(
        product_id=product_id
    )

    if sale_type_id:
        stats_queryset = stats_queryset.filter(
            sale_type_id=sale_type_id
        )

    stats = stats_queryset.aggregate(
        total_changes=Count("id"),
        avg_percent_change=Avg(
            "percent_change"
        ),
        increase_count=Count(
            "id",
            filter=Q(
                change_type="increase"
            ),
        ),
        decrease_count=Count(
            "id",
            filter=Q(
                change_type="decrease"
            ),
        ),
    )

    response_data = {
        "success": True,
        "product_id": product_id,
        "product_title": product.title,
        "stats": {
            "total_changes": (
                stats["total_changes"] or 0
            ),
            "last_change": (
                history_data[0]["created_at"]
                if history_data
                else None
            ),
            "avg_percent_change": float(
                stats["avg_percent_change"] or 0
            ),
            "increase_count": (
                stats["increase_count"] or 0
            ),
            "decrease_count": (
                stats["decrease_count"] or 0
            ),
        },
        "history": history_data,
        "count": len(history_data),
    }

    cache.set(
        cache_key,
        response_data,
        timeout=HISTORY_CACHE_TIMEOUT,
    )

    return JsonResponse(
        response_data,
        json_dumps_params={
            "ensure_ascii": False,
        },
    )


@csrf_exempt
@require_http_methods(["GET"])
@login_required
@user_passes_test(is_superuser)
def get_dashboard_stats(request):
    cache_key = build_price_panel_cache_key(
        "dashboard"
    )

    cached_data = cache.get(cache_key)

    if cached_data is not None:
        return JsonResponse(
            cached_data,
            json_dumps_params={
                "ensure_ascii": False,
            },
        )

    today = timezone.localdate()

    total_products = (
        Product.objects
        .filter(isActive=True)
        .count()
    )

    out_of_stock = (
        Product.objects
        .filter(
            isActive=True,
            stock=0,
        )
        .count()
    )

    today_queryset = (
        ProductPriceHistory.objects
        .filter(
            created_at__date=today
        )
    )

    today_stats = today_queryset.aggregate(
        today_changes=Count("id"),
        avg_change=Avg("percent_change"),
    )

    biggest_increase = (
        today_queryset
        .filter(
            change_type="increase"
        )
        .order_by(
            "-percent_change"
        )
        .values(
            "product__title",
            "percent_change",
        )
        .first()
    )

    biggest_decrease = (
        today_queryset
        .filter(
            change_type="decrease"
        )
        .order_by(
            "percent_change"
        )
        .values(
            "product__title",
            "percent_change",
        )
        .first()
    )

    latest_changes = (
        ProductPriceHistory.objects
        .select_related("product")
        .only(
            "id",
            "product_id",
            "product__title",
            "price_old",
            "price_new",
            "percent_change",
            "change_type",
            "created_at",
            "source",
        )
        .order_by("-created_at")[:10]
    )

    latest_data = [
        {
            "id": change.id,
            "product_title": (
                change.product.title
            ),
            "old_price": change.price_old,
            "new_price": change.price_new,
            "percent_change": (
                float(change.percent_change)
                if change.percent_change
                else 0
            ),
            "change_type": change.change_type,
            "created_at": change.created_at.strftime(
                "%H:%M %Y/%m/%d"
            ),
            "source": change.get_source_display(),
        }
        for change in latest_changes
    ]

    categories = list(
        Category.objects
        .filter(
            isActive=True,
            parent__isnull=True,
            products__isActive=True,
        )
        .annotate(
            product_count=Count(
                "products",
                filter=Q(
                    products__isActive=True
                ),
                distinct=True,
            )
        )
        .filter(
            product_count__gt=0
        )
        .values(
            "id",
            "title",
            "product_count",
        )
    )

    response_data = {
        "success": True,
        "stats": {
            "total_products": total_products,
            "out_of_stock": out_of_stock,
            "today_changes": (
                today_stats["today_changes"]
                or 0
            ),
            "avg_change_today": float(
                today_stats["avg_change"]
                or 0
            ),
            "biggest_increase": (
                {
                    "product": biggest_increase[
                        "product__title"
                    ],
                    "percent": float(
                        biggest_increase[
                            "percent_change"
                        ]
                        or 0
                    ),
                }
                if biggest_increase
                else None
            ),
            "biggest_decrease": (
                {
                    "product": biggest_decrease[
                        "product__title"
                    ],
                    "percent": float(
                        biggest_decrease[
                            "percent_change"
                        ]
                        or 0
                    ),
                }
                if biggest_decrease
                else None
            ),
        },
        "latest_changes": latest_data,
        "categories": [
            {
                "id": category["id"],
                "title": category["title"],
                "product_count": category[
                    "product_count"
                ],
                "parent": None,
            }
            for category in categories
        ],
    }

    cache.set(
        cache_key,
        response_data,
        timeout=DASHBOARD_CACHE_TIMEOUT,
    )

    return JsonResponse(
        response_data,
        json_dumps_params={
            "ensure_ascii": False,
        },
    )


@csrf_exempt
@require_http_methods(["GET"])
@login_required
@user_passes_test(is_staff_or_superuser)
def get_categories_with_stats(request):
    cache_key = build_price_panel_cache_key(
        "categories"
    )

    cached_data = cache.get(cache_key)

    if cached_data is not None:
        return JsonResponse(
            cached_data,
            json_dumps_params={
                "ensure_ascii": False,
            },
        )

    categories = (
        Category.objects
        .filter(
            isActive=True,
            parent__isnull=False,
        )
        .select_related("parent")
        .annotate(
            product_count=Count(
                "products",
                filter=Q(
                    products__isActive=True
                ),
                distinct=True,
            )
        )
        .only(
            "id",
            "title",
            "parent_id",
            "parent__id",
            "parent__title",
            "image",
        )
    )

    data = []

    for category in categories:
        parent_info = None

        if category.parent:
            parent_info = {
                "id": category.parent.id,
                "title": category.parent.title,
            }

        data.append(
            {
                "id": category.id,
                "title": category.title,
                "parent": parent_info,
                "image": safe_image_url(
                    category.image
                ),
                "product_count": (
                    category.product_count
                ),
            }
        )

    response_data = {
        "success": True,
        "categories": data,
    }

    cache.set(
        cache_key,
        response_data,
        timeout=CATEGORIES_CACHE_TIMEOUT,
    )

    return JsonResponse(
        response_data,
        json_dumps_params={
            "ensure_ascii": False,
        },
    )


@csrf_exempt
@require_http_methods(["POST"])
@login_required
@user_passes_test(is_superuser)
def bulk_update_prices(request):
    data = parse_json_body(request)

    if data is None:
        return json_error(
            "داده نامعتبر",
            status=400,
        )

    updates = data.get(
        "updates",
        [],
    )

    if not updates:
        return json_error(
            "لیست به‌روزرسانی خالی است",
            status=400,
        )

    user = request.user
    user_name = get_user_name(user)
    now = timezone.now()

    product_ids = {
        item.get("product_id")
        for item in updates
        if item.get("product_id") is not None
    }

    sale_type_ids = {
        item.get("sale_type_id")
        for item in updates
        if item.get("sale_type_id") is not None
    }

    with transaction.atomic():

        products = {
            product.id: product
            for product in (
                Product.objects
                .select_for_update()
                .filter(
                    id__in=product_ids
                )
                .only(
                    "id",
                    "title",
                )
            )
        }

        sale_types_queryset = (
            ProductSaleType.objects
            .select_for_update()
            .filter(
                product_id__in=product_ids
            )
        )

        if sale_type_ids:
            sale_types_queryset = (
                sale_types_queryset.filter(
                    Q(id__in=sale_type_ids)
                    | Q(
                        product_id__in=product_ids,
                        isActive=True,
                    )
                )
            )

        sale_types = {
            sale.id: sale
            for sale in sale_types_queryset
        }

        default_sale_types = {}

        for sale in sale_types.values():
            if (
                sale.product_id not in default_sale_types
                and sale.isActive
            ):
                default_sale_types[
                    sale.product_id
                ] = sale

        results = []
        errors = []

        sale_types_to_update = []
        history_to_create = []

        for update in updates:

            product_id = update.get(
                "product_id"
            )

            sale_type_id = update.get(
                "sale_type_id"
            )

            new_price = update.get(
                "price"
            )

            if product_id is None:
                errors.append(
                    {
                        "product_id": product_id,
                        "error": "product_id الزامی است",
                    }
                )
                continue

            if product_id not in products:
                errors.append(
                    {
                        "product_id": product_id,
                        "error": "محصول یافت نشد",
                    }
                )
                continue

            try:
                new_price_int = int(
                    new_price
                )

                if new_price_int < 0:
                    raise ValueError

            except (TypeError, ValueError):
                errors.append(
                    {
                        "product_id": product_id,
                        "error": "قیمت نامعتبر است",
                    }
                )
                continue

            if sale_type_id:
                sale_type = sale_types.get(
                    sale_type_id
                )

                if (
                    not sale_type
                    or sale_type.product_id != product_id
                ):
                    errors.append(
                        {
                            "product_id": product_id,
                            "error": "نوع فروش یافت نشد",
                        }
                    )
                    continue

            else:
                sale_type = default_sale_types.get(
                    product_id
                )

            if not sale_type:
                errors.append(
                    {
                        "product_id": product_id,
                        "error": "نوع فروش یافت نشد",
                    }
                )
                continue

            old_price = sale_type.price

            if old_price == new_price_int:
                results.append(
                    {
                        "product_id": product_id,
                        "status": "skipped",
                        "message": (
                            "قیمت تغییری نکرد"
                        ),
                    }
                )
                continue

            percent_change = (
                round(
                    (
                        (
                            new_price_int
                            - old_price
                        )
                        / old_price
                    )
                    * 100,
                    2,
                )
                if old_price > 0
                else 0
            )

            change_type = (
                "increase"
                if new_price_int > old_price
                else "decrease"
            )

            sale_type.price = new_price_int
            sale_type.finalPrice = new_price_int
            sale_type.updatedAt = now

            sale_types_to_update.append(
                sale_type
            )

            history_to_create.append(
                ProductPriceHistory(
                    product_id=product_id,
                    sale_type_id=sale_type.id,
                    price_old=old_price,
                    price_new=new_price_int,
                    percent_change=Decimal(
                        str(percent_change)
                    ),
                    change_type=change_type,
                    changed_by=user,
                    changed_by_name=user_name,
                    source="manual_excel",
                    is_current=True,
                    created_at=now,
                )
            )

            results.append(
                {
                    "product_id": product_id,
                    "product_title": products[
                        product_id
                    ].title,
                    "status": "success",
                    "old_price": old_price,
                    "new_price": new_price_int,
                    "percent_change": float(
                        percent_change
                    ),
                }
            )

        if sale_types_to_update:
            ProductSaleType.objects.bulk_update(
                sale_types_to_update,
                [
                    "price",
                    "finalPrice",
                    "updatedAt",
                ],
                batch_size=500,
            )

        history_sale_pairs = [
            (
                history.product_id,
                history.sale_type_id,
            )
            for history in history_to_create
        ]

        if history_sale_pairs:
            for product_id, sale_type_id in history_sale_pairs:
                ProductPriceHistory.objects.filter(
                    product_id=product_id,
                    sale_type_id=sale_type_id,
                    is_current=True,
                ).update(
                    is_current=False
                )

        if history_to_create:
            created_history = (
                ProductPriceHistory.objects.bulk_create(
                    history_to_create,
                    batch_size=500,
                )
            )

            created_by_product = {
                (
                    history.product_id,
                    history.sale_type_id,
                ): history
                for history in created_history
            }

            for result in results:
                if result.get("status") != "success":
                    continue

                key = (
                    result["product_id"],
                    next(
                        (
                            history.sale_type_id
                            for history in created_history
                            if history.product_id
                            == result["product_id"]
                            and history.price_new
                            == result["new_price"]
                        ),
                        None,
                    ),
                )

                history = created_by_product.get(
                    key
                )

                if history:
                    result[
                        "history_id"
                    ] = history.id

    if history_to_create:
        invalidate_price_panel_cache()

    return JsonResponse(
        {
            "success": True,
            "total": len(updates),
            "success_count": len(
                [
                    result
                    for result in results
                    if result.get("status")
                    == "success"
                ]
            ),
            "results": results,
            "errors": errors,
        },
        json_dumps_params={
            "ensure_ascii": False,
        },
    )