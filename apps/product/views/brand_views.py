from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.core.paginator import Paginator
from django.db.models import Count
from ..models.brand import Brand
from ..models.product import Product
from django.db import models

class PopularBrandsView(View):
    """
    لیست برندهای پر محصول
    - نمایش برندهای با بیشترین تعداد محصول
    """
    template_name = 'product_app/brand/popular_brands.html'

    def get(self, request):
        # استفاده از متد Manager
        popular_brands = Brand.objects.get_popular_brands(limit=20)

        # یا استفاده از متد دیگر
        # brands_with_count = Brand.objects.get_brands_with_product_count()
        # popular_brands = sorted(
        #     brands_with_count,
        #     key=lambda x: x.product_count,
        #     reverse=True
        # )[:20]

        context = {
            'popular_brands': popular_brands,
            'title': 'برندهای پرفروش',
            'meta_description': 'لیست برندهای معتبر با بیشترین محصولات',
        }

        return render(request, self.template_name, context)

class BrandProductsView(View):
    """
    محصولات بر اساس برند
    - فیلتر، مرتب‌سازی و صفحه‌بندی
    """
    template_name = 'product/brand/brand_products.html'

    def get(self, request, brand_slug):
        # دریافت برند
        brand = get_object_or_404(Brand, slug=brand_slug, is_active=True)

        # دریافت پارامترها
        page = request.GET.get('page', 1)
        order_by = request.GET.get('order_by', '-created_at')
        category_slug = request.GET.get('category')
        price_min = request.GET.get('price_min')
        price_max = request.GET.get('price_max')

        # آماده‌سازی فیلترها
        filters = {}

        if category_slug:
            filters['category'] = category_slug

        if price_min:
            try:
                filters['price_min'] = int(price_min)
            except:
                pass

        if price_max:
            try:
                filters['price_max'] = int(price_max)
            except:
                pass

        # دریافت محصولات با استفاده از متد مدل
        products = brand.get_products().order_by(order_by)

        # یا استفاده از Manager
        # products = Product.objects.get_by_brand(brand_slug, **filters)

        # صفحه‌بندی
        paginator = Paginator(products, 24)  # 24 محصول در هر صفحه
        products_page = paginator.get_page(page)

        # دریافت دسته‌بندی‌های این برند برای فیلتر
        categories = brand.get_categories()

        # دریافت محدوده قیمت برای فیلتر
        price_stats = products.aggregate(
            min_price=models.Min('price'),
            max_price=models.Max('price')
        )

        context = {
            'brand': brand,
            'products': products_page,
            'categories': categories,
            'total_products': products.count(),
            'price_min': price_stats['min_price'] or 0,
            'price_max': price_stats['max_price'] or 0,
            'current_order': order_by,
            'current_category': category_slug,
            'current_price_min': price_min,
            'current_price_max': price_max,
            'title': f'محصولات برند {brand.title}',
            'meta_description': brand.description[:160] if brand.description else f'خرید محصولات برند {brand.title}',
        }

        return render(request, self.template_name, context)

class BrandDetailView(View):
    """
    صفحه جزئیات برند
    - اطلاعات برند + محصولات ویژه
    """
    template_name = 'product/brand/brand_detail.html'

    def get(self, request, brand_slug):
        brand = get_object_or_404(Brand, slug=brand_slug, is_active=True)

        # محصولات جدید این برند
        new_products = brand.get_products().order_by('-created_at')[:8]

        # محصولات پرفروش (فعلاً بر اساس تاریخ)
        best_sellers = brand.get_products().order_by('-created_at')[:8]

        # دسته‌بندی‌های این برند
        categories = brand.get_categories()

        # تبدیل به دیکشنری برای JSON
        brand_data = brand.to_dict()

        context = {
            'brand': brand,
            'brand_data': brand_data,
            'new_products': new_products,
            'best_sellers': best_sellers,
            'categories': categories,
            'products_count': brand.get_products_count(),
            'title': brand.get_seo_title(),
            'meta_description': brand.get_seo_description(),
        }

        return render(request, self.template_name, context)