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
from apps.discount.models import DiscountBasket, DiscountDetail


# 1. محبوب‌ترین برندها
def popular_brands(request):
    """
    محبوب‌ترین برندها بر اساس تعداد محصولات
    """
    from .models import Brand

    brands = Brand.objects.filter(
        isActive=True
    ).annotate(
        product_count=Count('products', filter=Q(products__isActive=True))
    ).filter(
        product_count__gt=0
    ).order_by('-product_count')[:10]

    return render(request, 'product_app/brand/popular_brands.html', {'brands': brands})

# 2. پر محتواترین دسته‌بندی‌ها
def rich_categories(request):
    """
    پر محتواترین دسته‌بندی‌ها بر اساس تعداد محصولات
    """
    from .models import Category

    # فقط زیردسته‌ها (parent__isnull=False) تا والدها در لیست نیایند
    categories = Category.objects.filter(
        isActive=True,
        parent__isnull=False
    ).annotate(
        total_products=Count('products', filter=Q(products__isActive=True))
    ).filter(
        total_products__gt=0
    ).order_by('-total_products')[:10]

    return render(request, 'product_app/category/popular_categories.html', {'categories': categories})


def latest_products(request):
    """
    جدیدترین محصولات
    """
    from .models import Product, ProductGallery

    now = timezone.now()
    discount_subquery = DiscountBasket.objects.filter(
        isActive=True,
        startDate__lte=now,
        endDate__gte=now,
        discountOfBasket__product=OuterRef('pk')
    ).order_by('-discount').values('discount')[:1]

    # گرفتن محصولات جدید + قیمت پایه و تخفیف
    products = Product.objects.filter(
        isActive=True
    ).select_related('brand').prefetch_related(
        'category', 'saleTypes'
    ).annotate(
        price=Subquery(
            ProductSaleType.objects.filter(
                product=OuterRef('pk'),
                isActive=True
            ).order_by('price').values('price')[:1]
        ),
        discount_percent=Subquery(discount_subquery),
        final_price=ExpressionWrapper(
            Floor(F('price') * (100 - Coalesce(Subquery(discount_subquery), Value(0))) / Value(100)),
            output_field=PositiveIntegerField()
        )
    ).order_by('-createdAt')[:12]

    # آماده کردن داده‌ها برای تمپلیت
    product_list = []
    for product in products:
        base_price = product.price or 0
        discount_percent = product.discount_percent or 0
        final_price = product.final_price or base_price

        # گرفتن تصویر اصلی
        main_image = product.mainImage.url if product.mainImage else ''

        # گرفتن تصویر hover (اولین تصویر گالری)
        hover_image = main_image
        try:
            gallery_image = product.galleries.filter(isActive=True).first()
            if gallery_image and gallery_image.image:
                hover_image = gallery_image.image.url
        except:
            pass

        product_list.append({
            'id': product.id,
            'slug': product.slug,
            'title': product.title,
            'short_title': product.title[:40] + '...' if len(product.title) > 40 else product.title,
            'main_image': main_image,
            'hover_image': hover_image,  # این مهمه
            'final_price': int(final_price),
            'base_price': int(base_price),
            'discount_percentage': int(discount_percent),
            'rating': product.average_rating,
            'comments_count': product.total_comments,
            'shipping_today': True,
            'brand': product.brand.title if product.brand else None,
        })

    context = {
        'latest_products': product_list,
        'title': 'جدیدترین محصولات',
    }

    return render(request, 'product_app/product/latest_products.html', context)

# views.py

# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Count, Q

def product_detail(request, slug):
    """
    صفحه جزئیات محصول
    آدرس: /products/<slug>/
    """
    # 1. اطلاعات اولیه محصول
    product = get_object_or_404(Product, slug=slug, isActive=True)

    # 2. گالری محصول
    galleries = ProductGallery.objects.filter(
        product=product,
        isActive=True
    ).order_by('createdAt')

    # 3. ویژگی‌های محصول
    product_features = ProductFeature.objects.filter(
        product=product
    ).select_related('feature', 'filterValue')

    # 4. لیست کامنت‌ها
    comments = Comment.objects.filter(
        product=product,
        isActive=True
    ).select_related('user').order_by('-createdAt')

    # صفحه‌بندی کامنت‌ها
    page = request.GET.get('page', 1)
    paginator = Paginator(comments, 10)
    page_comments = paginator.get_page(page)

    # 5. آمارهای امتیاز و کامنت (از propertyهای خود مدل Product استفاده می‌کنیم)
    comment_stats = product.comment_stats

    # 6. قیمت‌ها + تخفیف
    now = timezone.now()
    discount_percent = DiscountBasket.objects.filter(
        isActive=True,
        startDate__lte=now,
        endDate__gte=now,
        discountOfBasket__product=product
    ).order_by('-discount').values_list('discount', flat=True).first() or 0


    sale_types = ProductSaleType.objects.filter(
        product=product,
        isActive=True
    ).order_by('typeSale')

    # نوع پیش‌فرض فروش
    default_sale_type = sale_types.filter(typeSale=SaleType.SINGLE).first()
    if not default_sale_type and sale_types.exists():
        default_sale_type = sale_types.first()


    # محاسبه finalPrice برای هر نوع فروش
    for sale in sale_types:
        # قیمت پایه هر نوع فروش (همیشه قیمت واحد نمایش داده می‌شود)
        base_price = sale.price

        # قیمت نهایی پس از تخفیف
        discounted_price = base_price
        if discount_percent:
            discounted_price = int(base_price * (100 - discount_percent) / 100)

        # تخصیص قیمت نهایی به شی فروش برای استفاده در تمپلیت
        sale.final_price = discounted_price

    # محاسبه finalPrice برای نوع پیش‌فرض
    if default_sale_type:
        # قیمت پایه همیشه قیمت واحد است (برای همه نوع فروش)
        default_base_price = default_sale_type.price

        default_final_price = default_base_price
        if discount_percent:
            default_final_price = int(default_base_price * (100 - discount_percent) / 100)

        # تخصیص قیمت نهایی به شی default_sale_type برای استفاده در تمپلیت
        default_sale_type.final_price = default_final_price
    else:
        default_base_price = 0
        default_final_price = 0

    # 7. محصولات مرتبط (از همان دسته‌بندی‌ها) + تخفیف
    now = timezone.now()
    discount_subquery = DiscountBasket.objects.filter(
        isActive=True,
        startDate__lte=now,
        endDate__gte=now,
        discountOfBasket__product=OuterRef('pk')
    ).order_by('-discount').values('discount')[:1]

    related_products = Product.objects.filter(
        isActive=True,
        category__in=product.category.all()
    ).annotate(
        price=Subquery(
            ProductSaleType.objects.filter(
                product=OuterRef('pk'),
                isActive=True
            ).order_by('price').values('price')[:1]
        ),
        discount_percent=Subquery(discount_subquery),
        final_price=ExpressionWrapper(
            Floor(F('price') * (100 - Coalesce(Subquery(discount_subquery), Value(0))) / Value(100)),
            output_field=PositiveIntegerField()
        )
    ).filter(price__isnull=False).distinct()[:8]

    # 8. آماده کردن متا تگ‌ها
    meta_data = {
        'title': product.title,
        'description': product.shortDescription[:160],
        'robots': 'index, follow',
        'og_type': 'product',
        'og_site_name': 'فروشگاه شما',
        'og_title': product.title,
        'og_description': product.shortDescription[:100],
        'og_image': request.build_absolute_uri(product.mainImage.url) if product.mainImage else '',
        'og_url': request.build_absolute_uri(product.get_absolute_url()),
        'twitter_card': 'summary_large_image',
        'twitter_title': product.title,
        'twitter_description': product.shortDescription[:100],
        'twitter_image': request.build_absolute_uri(product.mainImage.url) if product.mainImage else '',
    }

    # 9. مشخصات کلی محصول (از ویژگی‌های خاص)
    specifications = {}
    for pf in product_features:
        if pf.feature.title in ['مدل', 'نمایشگر', 'چیپست', 'دوربین', 'باتری']:
            specifications[pf.feature.title] = pf.value

    context = {
        # اطلاعات اصلی محصول
        'product': product,

        # گالری
        'galleries': galleries,

        # ویژگی‌ها
        'product_features': product_features,

        # کامنت‌ها
        'comments': page_comments,
        'total_comments': paginator.count,

        # آمارها
        'comment_stats': comment_stats,
        'average_rating': product.average_rating,
        'recommendation_stats': product.recommendation_stats,
        'rating_distribution': product.rating_distribution,

        # قیمت‌ها
        'sale_types': sale_types,
        'default_sale_type': default_sale_type,
        'default_final_price': default_final_price,
        'default_base_price': default_base_price,
        'discount_percent': discount_percent,
        'has_multiple_prices': sale_types.count() > 1,

        # محصولات مرتبط
        'related_products': related_products,

        # متا تگ‌ها
        'meta': meta_data,

        # مشخصات کلی
        'specifications': specifications,

        # برای فرم کامنت
        'user_has_commented': False,
    }

    # بررسی اگر کاربر لاگین کرده، آیا قبلاً کامنت داده است؟
    if request.user.is_authenticated:
        context['user_has_commented'] = Comment.objects.filter(
            user=request.user,
            product=product
        ).exists()

    return render(request, 'product_app/product/product_detail.html', context)


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
            'user_name': request.user.get_full_name() or request.user.username,
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
                'user_name': comment.user.get_full_name() or comment.user.username,
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

# prodfrom django.db.models import Min, Max, OuterRef, Subquery
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from .models import Product, Category, ProductSaleType, Brand
from .filters import ProductFilter


def show_by_filter(request, slug):
    category = get_object_or_404(Category, slug=slug)

    # ========================
    # محصولات فعال این دسته
    # ========================
    products = Product.objects.filter(
        isActive=True,
        category__slug=slug
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
    # فیلترهای django-filter (برند و ...)
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
    # برندها
    # ========================
    brands = Brand.objects.filter(
        products__in=filtered_products
    ).distinct()

    context = {
        'products': page_obj,
        'group': category,
        'filter': filter_obj,
        'brands': brands,
        'price_min': price_min,
        'price_max': price_max,
        'selected_min': req_min or price_min,
        'selected_max': req_max or price_max,
        'sort_option': sort,
        'total_products': paginator.count,
        'slug': slug,
    }

    return render(request, 'product_app/shop/shop.html', context)




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