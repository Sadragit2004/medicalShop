# apps/search/views.py

from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import (
    Q, OuterRef, Subquery, Min, Max, F, Value
)
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models.expressions import ExpressionWrapper
from django.db.models.fields import PositiveIntegerField
from django.db.models.functions import Coalesce, Floor

from apps.product.models import Product, Category, Brand, ProductSaleType
from apps.discount.models import DiscountBasket
from apps.search.models import PopularSearch


# ======================================================
# 🔒 لیست کامل کلمات و الگوهای مخرب (Attack Keywords)
# ======================================================

ATTACK_KEYWORDS = [
    # SQL Injection
    "select ", "insert ", "update ", "delete ", "drop ",
    "truncate ", "alter ", "create ",
    "union ", "union all ",
    " or ", " and ",
    "--", ";--", ";", "/*", "*/",
    "@@", "@",
    "char(", "nchar(", "varchar(", "nvarchar(",
    "cast(", "convert(",
    "information_schema",
    "xp_", "sp_",

    # XSS
    "<script", "</script",
    "<iframe", "<img", "<svg",
    "onerror=", "onload=", "onclick=",
    "javascript:", "alert(", "document.", "window.",

    # Command Injection
    "&&", "||", "|", "`",
    "$(", "${",
    "wget ", "curl ",
    "rm -", "chmod ", "chown ",

    # Path Traversal
    "../", "..\\",
    "/etc/passwd", "boot.ini",

    # NoSQL Injection
    "$ne", "$gt", "$lt", "$or", "$and",
    "{\"", "\"}",

    # Template Injection
    "{{", "}}", "{%", "%}",
]


def is_malicious_query(query: str) -> bool:
    query = query.lower()
    for keyword in ATTACK_KEYWORDS:
        if keyword in query:
            return True
    return False


# ======================================================
# 🔍 API پیشنهادات جستجو
# ======================================================

def search_suggestions(request):
    query = request.GET.get('q', '').strip()

    if not query or len(query) < 2:
        return JsonResponse({'suggestions': []})

    # ✅ بررسی امنیت
    if is_malicious_query(query):
        return JsonResponse({'suggestions': [], 'blocked': True})

    # ذخیره یا افزایش تعداد جستجو
    popular_search, created = PopularSearch.objects.get_or_create(
        keyword__iexact=query,
        defaults={'keyword': query}
    )
    if not created:
        popular_search.search_count += 1
        popular_search.save()

    product_suggestions = Product.objects.filter(
        Q(title__icontains=query) |
        Q(shortDescription__icontains=query),
        isActive=True
    ).distinct()[:5]

    category_suggestions = Category.objects.filter(
        title__icontains=query,
        isActive=True
    ).distinct()[:5]

    brand_suggestions = Brand.objects.filter(
        title__icontains=query,
        isActive=True
    ).distinct()[:5]

    suggestions = []

    for product in product_suggestions:
        suggestions.append({
            'type': 'product',
            'title': product.title,
            'url': product.get_absolute_url(),
            'image': product.mainImage.url if product.mainImage else None
        })

    for category in category_suggestions:
        suggestions.append({
            'type': 'category',
            'title': category.title,
            'url': f"/product/category/{category.slug}/",
            'image': category.image.url if category.image else None
        })

    for brand in brand_suggestions:
        suggestions.append({
            'type': 'brand',
            'title': brand.title,
            'url': f"/brand/{brand.slug}/",
            'image': brand.logo.url if brand.logo else None
        })

    return JsonResponse({'suggestions': suggestions})


# ======================================================
# 🔥 جستجوهای پرطرفدار
# ======================================================

def popular_searches(request):
    popular_searches = PopularSearch.objects.filter(
        last_searched__gte=timezone.now() - timezone.timedelta(days=30)
    ).order_by('-search_count')[:10]

    return JsonResponse({
        'popular_searches': [
            {'keyword': s.keyword, 'count': s.search_count}
            for s in popular_searches
        ]
    })


def increment_click(request):
    query = request.GET.get('q', '')
    if query:
        popular_search, _ = PopularSearch.objects.get_or_create(
            keyword__iexact=query,
            defaults={'keyword': query}
        )
        popular_search.click_count += 1
        popular_search.save()

    return JsonResponse({'status': 'success'})


# ======================================================
# 📄 صفحه نتایج جستجو
# ======================================================

def search_results(request):
    query = request.GET.get('q', '').strip()

    # ✅ بررسی امنیت
    if query and is_malicious_query(query):
        return render(request, 'search_app/results.html', {
            'query': query,
            'products': [],
            'categories': [],
            'brands': [],
            'total_results': 0,
            'product_count': 0,
            'category_count': 0,
            'brand_count': 0,
            'has_results': False,
            'blocked': True,
        })

    if query:
        popular_search, created = PopularSearch.objects.get_or_create(
            keyword__iexact=query,
            defaults={'keyword': query}
        )
        if not created:
            popular_search.search_count += 1
            popular_search.save()

    products_qs = Product.objects.filter(
        Q(title__icontains=query) |
        Q(shortDescription__icontains=query) |
        Q(description__icontains=query),
        isActive=True
    ).distinct()

    price_subquery = ProductSaleType.objects.filter(
        product=OuterRef('pk'),
        isActive=True
    ).order_by('price').values('price')[:1]

    products_qs = products_qs.annotate(
        price=Subquery(price_subquery)
    ).filter(price__isnull=False)

    now = timezone.now()
    discount_subquery = DiscountBasket.objects.filter(
        isActive=True,
        startDate__lte=now,
        endDate__gte=now,
        discountOfBasket__product=OuterRef('pk')
    ).order_by('-discount').values('discount')[:1]

    products_qs = products_qs.annotate(
        discount_percent=Subquery(discount_subquery),
        final_price=ExpressionWrapper(
            Floor(
                F('price') * (100 - Coalesce(Subquery(discount_subquery), Value(0))) / Value(100)
            ),
            output_field=PositiveIntegerField()
        )
    )

    categories = Category.objects.filter(
        title__icontains=query,
        isActive=True
    ).distinct()

    brands = Brand.objects.filter(
        title__icontains=query,
        isActive=True
    ).distinct()

    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')

    if price_min:
        products_qs = products_qs.filter(price__gte=int(price_min))
    if price_max:
        products_qs = products_qs.filter(price__lte=int(price_max))

    if request.GET.get('available'):
        products_qs = products_qs.filter(saleTypes__isActive=True)

    brand_filter = request.GET.get('brand')
    if brand_filter:
        products_qs = products_qs.filter(brand__slug=brand_filter)

    category_filter = request.GET.get('category')
    if category_filter:
        products_qs = products_qs.filter(category__slug=category_filter)

    sort = request.GET.get('sort', '1')

    if sort in ['3', 'cheap']:
        products_qs = products_qs.order_by('price')
    elif sort in ['2', 'expensive']:
        products_qs = products_qs.order_by('-price')
    elif sort in ['5', 'popular']:
        products_qs = products_qs.order_by('?')
    else:
        products_qs = products_qs.order_by('-createdAt')

    price_stats = products_qs.aggregate(
        min_price=Min('price'),
        max_price=Max('price')
    )

    min_price = price_stats['min_price'] or 0
    max_price = price_stats['max_price'] or 0

    paginator = Paginator(products_qs, 20)
    page = request.GET.get('page', 1)
    products_page = paginator.get_page(page)

    available_brands = Brand.objects.filter(products__in=products_qs).distinct()
    available_categories = Category.objects.filter(products__in=products_qs).distinct()

    selected_brand = available_brands.filter(slug=brand_filter).first() if brand_filter else None
    selected_category = available_categories.filter(slug=category_filter).first() if category_filter else None

    context = {
        'query': query,
        'products': products_page,
        'categories': categories,
        'brands': brands,
        'available_brands': available_brands,
        'available_categories': available_categories,
        'selected_brand': selected_brand,
        'selected_category': selected_category,
        'total_results': len(categories) + len(brands) + paginator.count,
        'product_count': paginator.count,
        'category_count': len(categories),
        'brand_count': len(brands),
        'sort_option': sort,
        'min_price': min_price,
        'max_price': max_price,
        'selected_min': price_min or min_price,
        'selected_max': price_max or max_price,
        'has_results': bool(query),
        'brand_filter': brand_filter,
        'category_filter': category_filter,
        'available_filter': request.GET.get('available'),
    }

    return render(request, 'search_app/results.html', context)
