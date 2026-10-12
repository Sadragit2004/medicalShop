from django.shortcuts import render
from django.db.models import Min, Max, OuterRef, Subquery, F, Value, PositiveIntegerField, ExpressionWrapper
from django.db.models.functions import Coalesce, Floor
from datetime import timedelta
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from .models import Product,ProductFeature,ProductSaleType,ProductGallery,Comment,Rating,SaleType,Brand,Feature,FeatureValue
from .filters import ProductFilter
from apps.main.models import SettingShop

from apps.discount.models import DiscountBasket, DiscountDetail


# 1. محبوب‌ترین برندها

from django.core.cache import cache
from django.db.models import  Avg



POPULAR_BRANDS_CACHE_KEY = "product_app:popular_brands:v1"
POPULAR_BRANDS_CACHE_TIMEOUT = 60 * 60

RICH_CATEGORIES_CACHE_KEY = "product_app:rich_categories:v1"
RICH_CATEGORIES_CACHE_TIMEOUT = 60 * 60

LATEST_PRODUCTS_CACHE_KEY = "product_app:latest_products:v1"
LATEST_PRODUCTS_CACHE_TIMEOUT = 60 * 60


def popular_brands(request):
    brands = cache.get(POPULAR_BRANDS_CACHE_KEY)

    if brands is not None:
        print("comeeeeeeee")
    else:
        print("cache miss")

        brands = list(
            Brand.objects.filter(
                isActive=True
            ).annotate(
                product_count=Count(
                    "products",
                    filter=Q(products__isActive=True),
                    distinct=True,
                )
            ).filter(
                product_count__gt=0
            ).order_by(
                "-product_count"
            )[:10]
        )

        cache.set(
            POPULAR_BRANDS_CACHE_KEY,
            brands,
            POPULAR_BRANDS_CACHE_TIMEOUT,
        )

    return render(
        request,
        "product_app/brand/popular_brands.html",
        {"brands": brands},
    )


def rich_categories(request):
    categories = cache.get(RICH_CATEGORIES_CACHE_KEY)

    if categories is not None:
        print("comeeeeeeee")
    else:
        print("cache miss")

        categories = list(
            Category.objects.filter(
                isActive=True,
                parent__isnull=False,
                parent__parent__isnull=True,
            ).annotate(
                total_products=Count(
                    "products",
                    filter=Q(products__isActive=True),
                    distinct=True,
                )
            ).filter(
                total_products__gt=0
            ).order_by(
                "-total_products"
            )[:10]
        )

        cache.set(
            RICH_CATEGORIES_CACHE_KEY,
            categories,
            RICH_CATEGORIES_CACHE_TIMEOUT,
        )

    return render(
        request,
        "product_app/category/popular_categories.html",
        {"categories": categories},
    )


def latest_products(request):
    product_list = cache.get(LATEST_PRODUCTS_CACHE_KEY)

    if product_list is not None:
        print("comeeeeeeee")
    else:
        print("cache miss")

        now = timezone.now()

        discount_subquery = DiscountBasket.objects.filter(
            isActive=True,
            startDate__lte=now,
            endDate__gte=now,
            discountOfBasket__product=OuterRef("pk"),
        ).order_by(
            "-discount"
        ).values(
            "discount"
        )[:1]

        products = (
            Product.objects.filter(
                isActive=True
            ).select_related(
                "brand",
                "typetitle",
            ).prefetch_related(
                "category",
                "saleTypes",
                "galleries",
            ).annotate(
                price=Subquery(
                    ProductSaleType.objects.filter(
                        product=OuterRef("pk"),
                        isActive=True,
                    ).order_by(
                        "price"
                    ).values(
                        "price"
                    )[:1],
                    output_field=PositiveIntegerField(),
                ),
                discount_percent=Subquery(
                    discount_subquery,
                    output_field=PositiveIntegerField(),
                ),
            ).annotate(
                final_price=ExpressionWrapper(
                    Floor(
                        F("price")
                        * (
                            Value(100)
                            - Coalesce(
                                F("discount_percent"),
                                Value(0),
                            )
                        )
                        / Value(100)
                    ),
                    output_field=PositiveIntegerField(),
                )
            ).order_by(
                "-createdAt"
            )[:12]
        )

        product_list = []

        for product in products:
            base_price = product.price or 0
            discount_percent = product.discount_percent or 0

            final_price = (
                product.final_price
                if product.price is not None
                else 0
            )

            main_image = (
                product.mainImage.url
                if product.mainImage
                else ""
            )

            gallery_image = next(
                (
                    gallery
                    for gallery in product.galleries.all()
                    if gallery.isActive and gallery.image
                ),
                None,
            )

            hover_image = (
                gallery_image.image.url
                if gallery_image
                else main_image
            )

            average_rating = Rating.objects.filter(
                product=product
            ).aggregate(
                avg=Avg("rating")
            )["avg"]

            comments_count = Comment.objects.filter(
                product=product,
                isActive=True,
            ).count()

            product_list.append({
                "id": product.id,
                "slug": product.slug,
                "title": product.title,
                "short_title": (
                    product.title[:40] + "..."
                    if len(product.title) > 40
                    else product.title
                ),
                "main_image": main_image,
                "hover_image": hover_image,
                "final_price": int(
                    final_price
                    if final_price is not None
                    else base_price
                ),
                "base_price": int(base_price),
                "discount_percentage": int(discount_percent),
                "rating": round(float(average_rating or 0), 1),
                "comments_count": comments_count,
                "shipping_today": True,
                "brand": (
                    product.brand.title
                    if product.brand
                    else None
                ),
            })

        cache.set(
            LATEST_PRODUCTS_CACHE_KEY,
            product_list,
            LATEST_PRODUCTS_CACHE_TIMEOUT,
        )

    return render(
        request,
        "product_app/product/latest_products.html",
        {
            "latest_products": product_list,
            "title": "جدیدترین محصولات",
        },
    )

# views.py
# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Count, Q, OuterRef, Subquery, ExpressionWrapper, F, Value, PositiveIntegerField
from django.db.models.functions import Floor, Coalesce
from django.utils import timezone
import re
from django.shortcuts import get_object_or_404, render
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import OuterRef, Subquery, F, Value, ExpressionWrapper, PositiveIntegerField
from django.db.models.functions import Floor, Coalesce


def product_detail(request, slug):
    """
    صفحه جزئیات محصول
    آدرس: /products/<slug>/
    """

    # 1. اطلاعات اولیه محصول
    product = get_object_or_404(
        Product,
        slug=slug,
        isActive=True,
    )

    # 2. لینک ویدیو آپارات از دیتابیس - تبدیل به لینک Embed
    video_link = (product.vidiolink or "").strip()
    video_embed_url = ""
    video_hash = ""

    if video_link:
        match = re.search(r'aparat\.com/v/([a-zA-Z0-9]+)', video_link)
        if match:
            video_hash = match.group(1)
            video_embed_url = (
                f"https://www.aparat.com/video/video/embed/videohash/"
                f"{video_hash}/vt/frame?config=%7B%22skin%22%3A%22modern%22%7D"
            )

    # 3. گالری محصول
    galleries = ProductGallery.objects.filter(
        product=product,
        isActive=True,
    ).order_by("createdAt")

    # 4. ویژگی‌های محصول
    product_features = ProductFeature.objects.filter(
        product=product
    ).select_related("feature", "filterValue")

    # 5. کامنت‌ها
    comments = Comment.objects.filter(
        product=product,
        isActive=True,
    ).select_related("user").order_by("-createdAt")

    page = request.GET.get("page", 1)
    paginator = Paginator(comments, 10)
    page_comments = paginator.get_page(page)

    # 6. آمار امتیاز و کامنت
    comment_stats = product.comment_stats

    # 7. تخفیف محصول
    now = timezone.now()

    discount_percent = (
        DiscountBasket.objects.filter(
            isActive=True,
            startDate__lte=now,
            endDate__gte=now,
            discountOfBasket__product=product,
        )
        .order_by("-discount")
        .values_list("discount", flat=True)
        .first()
        or 0
    )

    # 8. انواع فروش
    sale_types = list(
        ProductSaleType.objects.filter(
            product=product,
            isActive=True,
        ).order_by("typeSale")
    )

    default_sale_type = next(
        (
            sale
            for sale in sale_types
            if sale.typeSale == SaleType.SINGLE
        ),
        None,
    )

    if default_sale_type is None and sale_types:
        default_sale_type = sale_types[0]

    # محاسبه قیمت نهایی هر نوع فروش
    for sale in sale_types:
        sale.final_price = (
            int(sale.price * (100 - discount_percent) / 100)
            if discount_percent
            else sale.price
        )

    if default_sale_type:
        default_base_price = default_sale_type.price

        default_final_price = (
            int(default_base_price * (100 - discount_percent) / 100)
            if discount_percent
            else default_base_price
        )

        default_sale_type.final_price = default_final_price
    else:
        default_base_price = 0
        default_final_price = 0

    # 9. محاسبات موجودی و محدودیت فروش
    max_cartons = 0
    total_units = 0
    max_limited = 0
    step_limited = 0

    if (
        default_sale_type
        and default_sale_type.typeSale == SaleType.CARTON
    ):
        if (
            default_sale_type.memberCarton
            and default_sale_type.memberCarton > 0
        ):
            max_cartons = product.stock // default_sale_type.memberCarton
            total_units = default_sale_type.memberCarton

    if (
        default_sale_type
        and default_sale_type.typeSale == SaleType.LIMITED
    ):
        max_limited = product.stock
        step_limited = default_sale_type.limitedSale or 1

    # 10. وضعیت کامنت کاربر
    user_has_commented = False

    if request.user.is_authenticated:
        user_has_commented = Comment.objects.filter(
            user=request.user,
            product=product,
        ).exists()

    # 11. وضعیت علاقه‌مندی
    is_favorite = False

    if request.user.is_authenticated:
        is_favorite = request.user.favorites.filter(
            id=product.id
        ).exists()

    # 12. محصولات مرتبط و تخفیف آن‌ها
    discount_subquery = (
        DiscountBasket.objects.filter(
            isActive=True,
            startDate__lte=now,
            endDate__gte=now,
            discountOfBasket__product=OuterRef("pk"),
        )
        .order_by("-discount")
        .values("discount")[:1]
    )

    related_products = (
        Product.objects.filter(
            isActive=True,
            category__in=product.category.all(),
        )
        .exclude(id=product.id)
        .annotate(
            price=Subquery(
                ProductSaleType.objects.filter(
                    product=OuterRef("pk"),
                    isActive=True,
                )
                .order_by("price")
                .values("price")[:1]
            ),
            discount_percent=Subquery(discount_subquery),
        )
        .annotate(
            final_price=ExpressionWrapper(
                Floor(
                    F("price")
                    * (
                        Value(100)
                        - Coalesce(
                            F("discount_percent"),
                            Value(0),
                        )
                    )
                    / Value(100)
                ),
                output_field=PositiveIntegerField(),
            )
        )
        .filter(price__isnull=False)
        .distinct()[:8]
    )

    # 13. متاتگ‌های محصول
    image_url = (
        request.build_absolute_uri(product.mainImage.url)
        if product.mainImage
        else ""
    )

    meta_data = {
        "title": product.title,
        "description": (product.shortDescription or "")[:160],
        "robots": "index, follow",
        "og_type": "product",
        "og_site_name": "فروشگاه شما",
        "og_title": product.title,
        "og_description": (product.shortDescription or "")[:100],
        "og_image": image_url,
        "og_url": request.build_absolute_uri(
            product.get_absolute_url()
        ),
        "twitter_card": "summary_large_image",
        "twitter_title": product.title,
        "twitter_description": (product.shortDescription or "")[:100],
        "twitter_image": image_url,
    }

    # 14. مشخصات کلی محصول
    specifications = {}

    for pf in product_features:
        if pf.feature.title in [
            "مدل",
            "نمایشگر",
            "چیپست",
            "دوربین",
            "باتری",
        ]:
            specifications[pf.feature.title] = pf.value

    # 15. تنظیمات فروشگاه
    shop_setting = SettingShop.objects.select_related(
        "emergency_phone"
    ).first()

    is_call = shop_setting.is_call if shop_setting else False
    emergency_phone = (
        shop_setting.emergency_phone
        if shop_setting
        else None
    )

    # 16. نوع بسته‌بندی محصول
    product_type_title = product.typetitle

    # 17. اطلاعات ارسالی به تمپلیت
    context = {
        "product": product,

        # لینک ویدیو آپارات
        "video_link": video_link,
        "video_embed_url": video_embed_url,
        "video_hash": video_hash,
        "has_video": bool(video_embed_url),

        # تنظیمات فروشگاه
        "is_call": is_call,
        "emergency_phone": emergency_phone,

        # گالری
        "galleries": galleries,

        # ویژگی‌ها
        "product_features": product_features,

        # کامنت‌ها
        "comments": page_comments,
        "total_comments": paginator.count,

        # آمار
        "comment_stats": comment_stats,
        "average_rating": product.average_rating,
        "recommendation_stats": product.recommendation_stats,
        "rating_distribution": product.rating_distribution,

        # قیمت‌ها
        "sale_types": sale_types,
        "default_sale_type": default_sale_type,
        "default_final_price": default_final_price,
        "default_base_price": default_base_price,
        "discount_percent": discount_percent,
        "has_multiple_prices": len(sale_types) > 1,

        # محصولات مرتبط
        "related_products": related_products,

        # متاتگ‌ها
        "meta": meta_data,

        # مشخصات
        "specifications": specifications,

        # کامنت کاربر
        "user_has_commented": user_has_commented,

        # علاقه‌مندی
        "is_favorite": is_favorite,

        # موجودی و محدودیت‌ها
        "max_cartons": max_cartons,
        "total_units": total_units,
        "max_limited": max_limited,
        "step_limited": step_limited,
        "product_stock": product.stock,

        "member_carton": (
            default_sale_type.memberCarton
            if default_sale_type
            and default_sale_type.typeSale == SaleType.CARTON
            else 0
        ),

        "limited_sale": (
            default_sale_type.limitedSale
            if default_sale_type
            and default_sale_type.typeSale == SaleType.LIMITED
            else 0
        ),

        "product_type_title": product_type_title,
    }

    return render(
        request,
        "product_app/product/product_detail.html",
        context,
    )



# ========================
# درج کامنت (برای AJAX)
# ========================
@login_required
@require_POST
def add_comment(request, product_slug):
    """
    افزودن کامنت جدید به صورت AJAX
    آدرس: /products/<slug>/comment/add/
    """
    try:
        product = get_object_or_404(Product, slug=product_slug, isActive=True)

        # بررسی آیا کاربر قبلاً کامنت داده است؟
        if Comment.objects.filter(user=request.user, product=product).exists():
            return JsonResponse({
                'success': False,
                'error': 'شما قبلاً برای این محصول کامنت داده‌اید'
            })

        # دریافت داده‌ها
        text = request.POST.get('text', '').strip()
        comment_type = request.POST.get('type', 'recommend')

        # اعتبارسنجی
        if not text:
            return JsonResponse({
                'success': False,
                'error': 'متن کامنت الزامی است'
            })

        if len(text) < 10:
            return JsonResponse({
                'success': False,
                'error': 'متن باید حداقل ۱۰ کاراکتر باشد'
            })

        if comment_type not in ['recommend', 'not_recommend']:
            comment_type = 'recommend'

        # ایجاد کامنت
        comment = Comment.objects.create(
            user=request.user,
            product=product,
            text=text,
            typeComment=comment_type
        )

        # آماده کردن داده برای پاسخ
        comment_data = {
            'id': comment.id,
            'user_name': request.user.family or request.user.username,
            'text': comment.text,
            'type': comment.get_typeComment_display(),
            'type_class': 'text-green-500' if comment_type == 'recommend' else 'text-red-500',
            'created_at': comment.createdAt.strftime('%Y/%m/%d %H:%M'),
            'is_buyer': True,  # می‌توانید بعداً بر اساس خرید کاربر تنظیم کنید
        }

        # آمار جدید
        stats = {
            'total_comments': product.total_comments,
            'average_rating': product.average_rating,
            'recommendation_stats': product.recommendation_stats,
        }

        return JsonResponse({
            'success': True,
            'message': 'کامنت با موفقیت ثبت شد',
            'comment': comment_data,
            'stats': stats,
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


# ========================
# دریافت کامنت‌ها (برای AJAX - infinite scroll)
# ========================
def load_more_comments(request, product_slug):
    """
    دریافت کامنت‌های بیشتر به صورت AJAX
    آدرس: /products/<slug>/comments/load-more/
    """
    try:
        product = get_object_or_404(Product, slug=product_slug, isActive=True)

        page = int(request.GET.get('page', 2))  # صفحه ۲ به بعد
        per_page = 10

        comments = Comment.objects.filter(
            product=product,
            isActive=True
        ).select_related('user').order_by('-createdAt')

        paginator = Paginator(comments, per_page)

        if page > paginator.num_pages:
            return JsonResponse({
                'success': True,
                'has_more': False,
                'comments': []
            })

        page_obj = paginator.get_page(page)

        comments_list = []
        for comment in page_obj:
            comments_list.append({
                'id': comment.id,
                'user_name': comment.user.family or comment.user.username,
                'text': comment.text,
                'type': comment.get_typeComment_display(),
                'type_class': 'text-green-500' if comment.typeComment == 'recommend' else 'text-red-500',
                'created_at': comment.createdAt.strftime('%Y/%m/%d %H:%M'),
                'is_buyer': True,
            })

        return JsonResponse({
            'success': True,
            'has_more': page_obj.has_next(),
            'comments': comments_list,
            'next_page': page + 1 if page_obj.has_next() else None
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


def show_by_filter(request, slug):
    category = get_object_or_404(Category, slug=slug)

    products = (
        Product.objects.filter(
            isActive=True,
            category__slug=slug,
        )
        .select_related("brand")
        .prefetch_related("saleTypes", "featuresValue")
        .distinct()
    )

    price_subquery = (
        ProductSaleType.objects.filter(
            product=OuterRef("pk"),
            isActive=True,
        )
        .order_by("price", "pk")
        .values("price")[:1]
    )

    products = (
        products.annotate(price=Subquery(price_subquery))
        .filter(price__isnull=False)
    )

    now = timezone.now()

    discount_subquery = (
        DiscountBasket.objects.filter(
            isActive=True,
            startDate__lte=now,
            endDate__gte=now,
            discountOfBasket__product=OuterRef("pk"),
        )
        .order_by("-discount")
        .values("discount")[:1]
    )

    products = products.annotate(
        discount_percent=Subquery(discount_subquery),
    ).annotate(
        final_price=ExpressionWrapper(
            Floor(
                F("price")
                * (
                    Value(100)
                    - Coalesce(F("discount_percent"), Value(0))
                )
                / Value(100)
            ),
            output_field=PositiveIntegerField(),
        ),
    )

    price_stats = ProductSaleType.objects.filter(
        product__in=products,
        isActive=True,
    ).aggregate(
        min_price=Min("price"),
        max_price=Max("price"),
    )

    price_min = price_stats["min_price"] or 0
    price_max = price_stats["max_price"] or 0

    filter_obj = ProductFilter(request.GET, queryset=products)
    filtered_products = filter_obj.qs

    feature_values = request.GET.getlist("feature")

    if feature_values:
        filtered_products = filtered_products.filter(
            featuresValue__filterValue_id__in=feature_values,
        )

    req_min = request.GET.get("price_min")
    req_max = request.GET.get("price_max")

    if req_min:
        filtered_products = filtered_products.filter(
            price__gte=req_min,
        )

    if req_max:
        filtered_products = filtered_products.filter(
            price__lte=req_max,
        )

    sort = request.GET.get("sort", "1")

    if sort in ("3", "cheap"):
        filtered_products = filtered_products.order_by("price", "pk")
    elif sort in ("2", "expensive"):
        filtered_products = filtered_products.order_by("-price", "pk")
    else:
        filtered_products = filtered_products.order_by("-createdAt", "-pk")

    filtered_products = filtered_products.distinct()

    paginator = Paginator(filtered_products, 12)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    brands = Brand.objects.filter(
        products__in=filtered_products,
    ).distinct()

    context = {
        "products": page_obj,
        "group": category,
        "filter": filter_obj,
        "brands": brands,
        "price_min": price_min,
        "price_max": price_max,
        "selected_min": req_min or price_min,
        "selected_max": req_max or price_max,
        "sort_option": sort,
        "total_products": paginator.count,
        "slug": slug,
    }

    return render(
        request,
        "product_app/shop/shop.html",
        context,
    )



def show_brand_products(request, slug):
    """
    نمایش محصولات یک برند خاص
    مشابه صفحه shop اما فیلتر شده بر اساس برند
    """
    brand = get_object_or_404(Brand, slug=slug)

    # ========================
    # محصولات فعال این برند
    # ========================
    products = Product.objects.filter(
        isActive=True,
        brand=brand
    ).select_related('brand').prefetch_related(
        'saleTypes',
        'featuresValue'
    ).distinct()

    # ========================
    # زیرکوئری قیمت (price فقط)
    # ========================
    price_subquery = ProductSaleType.objects.filter(
        product=OuterRef('pk'),
        isActive=True
    ).order_by('price').values('price')[:1]

    # 🔥 این خط کلیدی است
    products = products.annotate(
        price=Subquery(price_subquery)
    ).filter(price__isnull=False)

    # ========================
    # تخفیف فعال برای هر محصول
    # ========================
    now = timezone.now()
    discount_subquery = DiscountBasket.objects.filter(
        isActive=True,
        startDate__lte=now,
        endDate__gte=now,
        discountOfBasket__product=OuterRef('pk')
    ).order_by('-discount').values('discount')[:1]

    products = products.annotate(
        discount_percent=Subquery(discount_subquery),
        final_price=ExpressionWrapper(
            Floor(F('price') * (100 - Coalesce(Subquery(discount_subquery), Value(0))) / Value(100)),
            output_field=PositiveIntegerField()
        )
    )

    # ========================
    # min / max قیمت واقعی
    # ========================
    price_stats = ProductSaleType.objects.filter(
        product__in=products,
        isActive=True
    ).aggregate(
        min_price=Min('price'),
        max_price=Max('price')
    )

    price_min = price_stats['min_price'] or 0
    price_max = price_stats['max_price'] or 0

    # ========================
    # فیلترهای django-filter (دسته‌بندی و ...)
    # ========================
    filter_obj = ProductFilter(request.GET, queryset=products)
    filtered_products = filter_obj.qs

    # ========================
    # فیلتر ویژگی‌ها (feature checkboxes)
    # ========================
    feature_values = request.GET.getlist('feature')
    if feature_values:
        # هر مقدار در URL یک FeatureValue.id است
        filtered_products = filtered_products.filter(
            featuresValue__filterValue_id__in=feature_values
        ).distinct()

    # ========================
    # فیلتر قیمت
    # ========================
    req_min = request.GET.get('price_min')
    req_max = request.GET.get('price_max')

    if req_min:
        filtered_products = filtered_products.filter(price__gte=req_min)

    if req_max:
        filtered_products = filtered_products.filter(price__lte=req_max)

    # ========================
    # مرتب‌سازی
    # ========================
    sort = request.GET.get('sort', '1')

    # پشتیبانی از هر دو حالت: مقادیر عددی (1,2,3) و متنی (cheap, expensive, new)
    if sort in ['3', 'cheap']:
        filtered_products = filtered_products.order_by('price')
    elif sort in ['2', 'expensive']:
        filtered_products = filtered_products.order_by('-price')
    else:  # '1' یا 'new' و هر مقدار نامعتبر دیگر
        filtered_products = filtered_products.order_by('-createdAt')

    # ========================
    # صفحه‌بندی
    # ========================
    paginator = Paginator(filtered_products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    # ========================
    # دسته‌بندی‌ها (برای فیلتر)
    # ========================
    categories = Category.objects.filter(
        products__in=filtered_products
    ).distinct()

    context = {
        'products': page_obj,
        'group': brand,  # استفاده از برند به جای دسته‌بندی
        'filter': filter_obj,
        'categories': categories,  # دسته‌بندی‌ها برای فیلتر
        'price_min': price_min,
        'price_max': price_max,
        'selected_min': req_min or price_min,
        'selected_max': req_max or price_max,
        'sort_option': sort,
        'total_products': paginator.count,
        'slug': slug,
        'is_brand_page': True,  # نشان‌دهنده صفحه برند
    }

    return render(request, 'product_app/shop/shop.html', context)




# View جدید برای فیلتر ویژگی‌های برند
def get_brand_feature_filter(request, slug):
    brand = get_object_or_404(Brand, slug=slug)

    # دریافت محصولات فیلتر شده برند
    products = Product.objects.filter(
        isActive=True,
        brand=brand
    )

    # ساخت feature_dict برای نمایش در فیلترها
    # برای برندها، تمام ویژگی‌های محصولات برند را نمایش می‌دهیم
    feature_dict = {}

    # دریافت تمام ویژگی‌های منحصر به فرد از محصولات این برند
    all_features = Feature.objects.filter(
        featureValues__productfeature__product__in=products
    ).distinct()

    for feature in all_features:
        values = FeatureValue.objects.filter(
            feature=feature,
            productfeature__product__in=products
        ).annotate(
            product_count=Count('productfeature__product')
        ).filter(product_count__gt=0).distinct()

        if values.exists():
            feature_dict[feature] = values

    # شناسه ویژگی‌های انتخاب‌شده برای علامت زدن چک‌باکس‌ها
    selected_features = request.GET.getlist('feature')

    return render(request, 'product_app/product/partials/feature_list_filer.html', {
        'feature_dict': feature_dict,
        'slug': slug,
        'selected_features': selected_features,
    })


# View جدید برای فیلتر ویژگی‌ها
def get_feature_filter(request, slug):
    category = get_object_or_404(Category, slug=slug)

    # دریافت محصولات فیلتر شده
    products = Product.objects.filter(
        isActive=True,
        category=category
    )

    # ساخت feature_dict برای نمایش در فیلترها
    feature_dict = {}
    features_in_category = Feature.objects.filter(categories=category)

    for feature in features_in_category:
        values = FeatureValue.objects.filter(
            feature=feature,
            productfeature__product__in=products
        ).annotate(
            product_count=Count('productfeature__product')
        ).filter(product_count__gt=0).distinct()

        if values.exists():
            feature_dict[feature] = values

    # شناسه ویژگی‌های انتخاب‌شده برای علامت زدن چک‌باکس‌ها
    selected_features = request.GET.getlist('feature')

    return render(request, 'product_app/product/partials/feature_list_filer.html', {
        'feature_dict': feature_dict,
        'slug': slug,
        'selected_features': selected_features,
    })

from django.db.models import Sum

def top_selling_products(request):
    """
    نمایش 10 محصول پرفروش با تخفیف
    """
    # دریافت محصولات پرفروش
    products = Product.objects.filter(
        orderItems__order__isFinally=True,
        orderItems__order__status__in=['delivered', 'shipped'],
        isActive=True
    ).annotate(
        total_sold=Sum('orderItems__qty')
    ).order_by('-total_sold')[:10]

    # تاریخ فعلی برای بررسی تخفیف
    now = timezone.now()

    products_list = []
    for product in products:
        # قیمت اصلی محصول
        sale_type = product.saleTypes.filter(isActive=True).first()
        original_price = sale_type.price if sale_type else 0

        # بررسی تخفیف محصول
        discount_detail = DiscountDetail.objects.filter(
            product=product,
            discountBasket__isActive=True,
            discountBasket__startDate__lte=now,
            discountBasket__endDate__gte=now
        ).select_related('discountBasket').first()

        # محاسبه قیمت نهایی
        if discount_detail:
            discount_percent = discount_detail.discountBasket.discount
            final_price = original_price - (original_price * discount_percent // 100)
            is_amazing = discount_detail.discountBasket.isamzing
            discount_title = discount_detail.discountBasket.discountTitle
        else:
            discount_percent = 0
            final_price = original_price
            is_amazing = False
            discount_title = ""

        products_list.append({
            'product': product,
            'total_sold': product.total_sold or 0,
            'original_price': original_price,
            'final_price': final_price,
            'discount_percent': discount_percent,
            'is_discounted': discount_percent > 0,
            'is_amazing': is_amazing,
            'discount_title': discount_title
        })

    context = {
        'products_list': products_list,
    }

    return render(request, 'product_app/product/top_selling.html', context)


def get_category_tree(request):
    """نمایش درختی دسته‌بندی‌ها - مرتب‌سازی قدیمی‌ترین‌ها اول"""

    # دیباگ: تعداد دسته‌بندی‌های موجود
    total_categories = Category.objects.count()
    active_categories = Category.objects.filter(isActive=True).count()
    main_categories_count = Category.objects.filter(parent=None, isActive=True).count()

    print(f"Total Categories: {total_categories}")
    print(f"Active Categories: {active_categories}")
    print(f"Main Categories (parent=None): {main_categories_count}")

    # دریافت دسته‌بندی‌های اصلی
    # تغییر: order_by('createdAt') یعنی از قدیمی به جدید
    main_categories = Category.objects.filter(
        parent=None,
        isActive=True
    ).order_by('createdAt')[:20]

    # دیباگ: نام دسته‌بندی‌های اصلی
    for cat in main_categories:
        print(f"Main Category: {cat.title} (ID: {cat.id})")
        children_count = cat.children.filter(isActive=True).count()
        print(f"  Children: {children_count}")

    # ساختار درختی
    tree_data = []

    for main_cat in main_categories:
        # فرزندان سطح دوم (قدیمی‌ترین‌ها اول)
        children_l2 = main_cat.children.filter(isActive=True).order_by('createdAt')

        children_data = []
        for child_l2 in children_l2:
            # فرزندان سطح سوم (قدیمی‌ترین‌ها اول)
            children_l3 = child_l2.children.filter(isActive=True).order_by('createdAt')

            children_data.append({
                'child': child_l2,
                'grandchildren': children_l3
            })

        tree_data.append({
            'main': main_cat,
            'children': children_data
        })

    # دیباگ: ساختار نهایی
    print(f"Tree Data Length: {len(tree_data)}")

    context = {
        'tree_data': tree_data,
        'debug': {
            'total_categories': total_categories,
            'active_categories': active_categories,
            'main_categories': list(main_categories.values_list('title', flat=True))
        }
    }

    return render(request, 'product_app/category/category_tree_pc.html', context)



from django.shortcuts import render
from .models import Category
import json

def get_category_tree_mobile(request):
    """نمایش درختی دسته‌بندی‌ها با لاگ برای دیباگ"""

    # دیباگ: تعداد دسته‌بندی‌های موجود
    total_categories = Category.objects.count()
    active_categories = Category.objects.filter(isActive=True).count()
    main_categories_count = Category.objects.filter(parent=None, isActive=True).count()

    print(f"Total Categories: {total_categories}")
    print(f"Active Categories: {active_categories}")
    print(f"Main Categories (parent=None): {main_categories_count}")

    # دریافت دسته‌بندی‌های اصلی
    main_categories = Category.objects.filter(
        parent=None,
        isActive=True
    ).order_by('createdAt')[:6]

    # دیباگ: نام دسته‌بندی‌های اصلی
    for cat in main_categories:
        print(f"Main Category: {cat.title} (ID: {cat.id})")
        children_count = cat.children.filter(isActive=True).count()
        print(f"  Children: {children_count}")

        for child in cat.children.filter(isActive=True)[:50]:
            grandchildren_count = child.children.filter(isActive=True).count()
            print(f"    Child: {child.title} - Grandchildren: {grandchildren_count}")

    # ساختار درختی
    tree_data = []

    for main_cat in main_categories:
        # فرزندان سطح دوم
        children_l2 = main_cat.children.filter(isActive=True).order_by('createdAt')

        children_data = []
        for child_l2 in children_l2:
            # فرزندان سطح سوم
            children_l3 = child_l2.children.filter(isActive=True).order_by('createdAt')
            children_data.append({
                'child': child_l2,
                'grandchildren': children_l3
            })

        tree_data.append({
            'main': main_cat,
            'children': children_data
        })

    # دیباگ: ساختار نهایی
    print(f"Tree Data Length: {len(tree_data)}")

    context = {
        'tree_data': tree_data,
        'debug': {
            'total_categories': total_categories,
            'active_categories': active_categories,
            'main_categories': list(main_categories.values_list('title', flat=True))
        }
    }

    return render(request, 'product_app/category/category_tree_mobile.html', context)



# views.py
def check_cart_stock(request):
    product_id = request.GET.get('product_id')
    try:
        product = Product.objects.get(id=product_id)
        return JsonResponse({
            'success': True,
            'stock': product.stock
        })
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'محصول یافت نشد'
        })