# apps/search/views.py
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q
from apps.product.models import Product, Category, Brand
from apps.search.models import PopularSearch
from django.utils import timezone
import json


def search_suggestions(request):
    """API برای پیشنهادات جستجو"""
    query = request.GET.get('q', '').strip()

    if not query or len(query) < 2:
        return JsonResponse({'suggestions': []})

    # ذخیره یا افزایش تعداد جستجو
    popular_search, created = PopularSearch.objects.get_or_create(
        keyword__iexact=query,
        defaults={'keyword': query}
    )
    if not created:
        popular_search.search_count += 1
        popular_search.save()

    # جستجو در محصولات
    product_suggestions = Product.objects.filter(
        Q(title__icontains=query) |
        Q(shortDescription__icontains=query),
        isActive=True
    ).distinct()[:5]

    # جستجو در دسته‌بندی‌ها
    category_suggestions = Category.objects.filter(
        title__icontains=query,
        isActive=True
    ).distinct()[:5]

    # جستجو در برندها
    brand_suggestions = Brand.objects.filter(
        title__icontains=query,
        isActive=True
    ).distinct()[:5]

    # ترکیب پیشنهادات
    suggestions = []

    # محصولات
    for product in product_suggestions:
        suggestions.append({
            'type': 'product',
            'title': product.title,
            'url': product.get_absolute_url(),
            'image': product.mainImage.url if product.mainImage else None
        })

    # دسته‌بندی‌ها
    for category in category_suggestions:
        suggestions.append({
            'type': 'category',
            'title': category.title,
            'url': f"/category/{category.slug}/",
            'image': category.image.url if category.image else None
        })

    # برندها
    for brand in brand_suggestions:
        suggestions.append({
            'type': 'brand',
            'title': brand.title,
            'url': f"/brand/{brand.slug}/",
            'image': brand.logo.url if brand.logo else None
        })

    return JsonResponse({'suggestions': suggestions})



def popular_searches(request):
    """API برای جستجوهای پرطرفدار"""
    # 10 جستجوی پرطرفدار اخیر
    popular_searches = PopularSearch.objects.filter(
        last_searched__gte=timezone.now() - timezone.timedelta(days=30)
    ).order_by('-search_count')[:10]

    popular_list = []
    for search in popular_searches:
        popular_list.append({
            'keyword': search.keyword,
            'count': search.search_count
        })

    return JsonResponse({'popular_searches': popular_list})


def increment_click(request):
    """افزایش تعداد کلیک روی پیشنهاد"""
    query = request.GET.get('q', '')
    if query:
        popular_search, created = PopularSearch.objects.get_or_create(
            keyword__iexact=query,
            defaults={'keyword': query}
        )
        popular_search.click_count += 1
        popular_search.save()

    return JsonResponse({'status': 'success'})

# apps/search/views.py
from django.shortcuts import render
from django.db.models import Q, OuterRef, Subquery, Min, Max, F
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models.expressions import ExpressionWrapper
from django.db.models.fields import PositiveIntegerField
from django.db.models.functions import Coalesce, Floor
from django.db.models import Value
from apps.product.models import Product, Category, Brand, ProductSaleType
from apps.discount.models import DiscountBasket
from apps.search.models import PopularSearch


def search_results(request):
    """صفحه نتایج جستجو"""
    query = request.GET.get('q', '').strip()

    # ذخیره جستجو برای پرطرفدارها
    if query:
        popular_search, created = PopularSearch.objects.get_or_create(
            keyword__iexact=query,
            defaults={'keyword': query}
        )
        if not created:
            popular_search.search_count += 1
            popular_search.save()

    # جستجو در محصولات
    products_qs = Product.objects.filter(
        Q(title__icontains=query) |
        Q(shortDescription__icontains=query) |
        Q(description__icontains=query),
        isActive=True
    ).distinct()

    # زیرکوئری قیمت
    price_subquery = ProductSaleType.objects.filter(
        product=OuterRef('pk'),
        isActive=True
    ).order_by('price').values('price')[:1]

    products_qs = products_qs.annotate(
        price=Subquery(price_subquery)
    ).filter(price__isnull=False)

    # تخفیف فعال
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
            Floor(F('price') * (100 - Coalesce(Subquery(discount_subquery), Value(0))) / Value(100)),
            output_field=PositiveIntegerField()
        )
    )

    # جستجو در دسته‌بندی‌ها
    categories = Category.objects.filter(
        title__icontains=query,
        isActive=True
    ).distinct()

    # جستجو در برندها
    brands = Brand.objects.filter(
        title__icontains=query,
        isActive=True
    ).distinct()

    # فیلترها
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

    # مرتب‌سازی
    sort = request.GET.get('sort', '1')

    if sort in ['3', 'cheap']:
        products_qs = products_qs.order_by('price')
    elif sort in ['2', 'expensive']:
        products_qs = products_qs.order_by('-price')
    elif sort in ['5', 'popular']:
        # بر اساس تعداد فروش - بعداً کاملش کن
        products_qs = products_qs.order_by('?')
    else:
        products_qs = products_qs.order_by('-createdAt')

    # قیمت‌ها برای فیلتر
    price_stats = products_qs.aggregate(
        min_price=Min('price'),
        max_price=Max('price')
    )

    min_price = price_stats['min_price'] or 0
    max_price = price_stats['max_price'] or 0

    # صفحه‌بندی
    paginator = Paginator(products_qs, 20)
    page = request.GET.get('page', 1)
    products_page = paginator.get_page(page)

    # برندها و دسته‌بندی‌های موجود برای فیلتر
    available_brands = Brand.objects.filter(
        products__in=products_qs
    ).distinct()

    available_categories = Category.objects.filter(
        products__in=products_qs
    ).distinct()

    # برای نمایش برند و دسته‌بندی انتخاب‌شده در فیلترهای فعال
    selected_brand = None
    selected_category = None

    if brand_filter:
        selected_brand = available_brands.filter(slug=brand_filter).first()

    if category_filter:
        selected_category = available_categories.filter(slug=category_filter).first()

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