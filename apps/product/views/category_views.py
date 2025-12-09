from django.shortcuts import render, get_object_or_404
from django.views import View
from django.core.paginator import Paginator
from django.db import models
from ..models.category import ProductCategory
from ..models.product import Product
from ..models.attribute import Attribute

class PopularCategoriesView(View):
    """
    گروه‌های محصولات با بیشترین محصولات
    """
    template_name = 'product_app/category/popular_categories.html'

    def get(self, request):
        # برای دیباگ: چاپ اطلاعات
        print("=" * 50)
        print("آغاز دیباگ PopularCategoriesView")
        print("=" * 50)

        # 1. تست اولیه: تعداد کل دسته‌بندی‌ها
        all_categories = ProductCategory.objects.filter(is_active=True)
        print(f"تعداد کل دسته‌بندی‌های فعال: {all_categories.count()}")

        # 2. لیست دسته‌بندی‌ها
        for cat in all_categories:
            print(f"- {cat.title} (ID: {cat.id})")

        # 3. تست محصولات در هر دسته‌بندی
        print("\n" + "=" * 50)
        print("تعداد محصولات در هر دسته‌بندی:")
        print("=" * 50)

        from ..models.product import Product  # import محصولات

        for cat in all_categories:
            # روش 1: با متد get_products_count
            product_count_method = cat.get_products_count(include_children=False)

            # روش 2: با کوئری مستقیم
            product_count_direct = Product.objects.filter(
                categories=cat,
                is_active=True
            ).count()

            print(f"{cat.title}:")
            print(f"  - با متد: {product_count_method} محصول")
            print(f"  - مستقیم: {product_count_direct} محصول")
            print()

        # 4. تست متد get_popular_categories
        print("\n" + "=" * 50)
        print("تست متد get_popular_categories:")
        print("=" * 50)

        popular_categories = ProductCategory.objects.get_popular_categories(limit=12)
        print(f"تعداد دسته‌بندی‌های محبوب برگشتی: {len(popular_categories)}")

        for cat in popular_categories:
            # چک کن آیا product_count attribute دارد
            if hasattr(cat, 'product_count'):
                print(f"- {cat.title}: {cat.product_count} محصول")
            else:
                print(f"- {cat.title}: product_count attribute ندارد!")

                # محاسبه دستی
                from ..models.product import Product
                count = Product.objects.filter(categories=cat, is_active=True).count()
                print(f"  (محاسبه دستی: {count} محصول)")

        # 5. تست manager مستقیماً
        print("\n" + "=" * 50)
        print("تست Manager مستقیماً:")
        print("=" * 50)

        # تست متد get_popular_categories از manager
        from django.db.models import Count, Q

        print("کوئری annotate:")
        categories_annotated = ProductCategory.objects.filter(
            is_active=True
        ).annotate(
            product_count=Count(
                'products',
                filter=Q(products__is_active=True),
                distinct=True
            )
        ).filter(
            product_count__gte=5  # min_products
        ).order_by(
            '-product_count'
        )[:12]

        print(f"تعداد با annotate: {categories_annotated.count()}")
        for cat in categories_annotated:
            print(f"- {cat.title}: {cat.product_count} محصول")

        # 6. تست تعداد کل محصولات
        print("\n" + "=" * 50)
        print("تعداد کل محصولات فعال:")
        print("=" * 50)

        total_products = Product.objects.filter(is_active=True).count()
        print(f"تعداد کل محصولات فعال در سیستم: {total_products}")

        # 7. نمایش داده‌های context
        print("\n" + "=" * 50)
        print("داده‌های ارسالی به تمپلیت:")
        print("=" * 50)
        print(f"popular_categories: {len(popular_categories)} مورد")

        context = {
            'popular_categories': popular_categories,
            'title': 'پربازدیدترین دسته‌بندی‌ها',
            'meta_description': 'دسته‌بندی‌های پرطرفدار با بیشترین محصولات',
            'debug_info': {
                'total_categories': all_categories.count(),
                'total_products': total_products,
                'popular_categories_count': len(popular_categories),
                'categories_list': [
                    {
                        'title': cat.title,
                        'product_count': getattr(cat, 'product_count', 0),
                        'id': cat.id
                    }
                    for cat in popular_categories
                ]
            }
        }

        return render(request, self.template_name, context)



class CategoryTreeView(View):
    """
    لیست درختی دسته‌بندی‌ها
    - نمایش سلسله‌مراتبی
    """
    template_name = 'product/category/category_tree.html'

    def get(self, request):
        # دریافت درخت کامل دسته‌بندی‌ها
        category_tree = ProductCategory.objects.get_category_tree()

        # یا فقط دسته‌بندی‌های ریشه
        # root_categories = ProductCategory.objects.get_root_categories()

        context = {
            'category_tree': category_tree,
            'title': 'دسته‌بندی‌های محصولات',
            'meta_description': 'سلسله‌مراتب کامل دسته‌بندی‌های محصولات',
        }

        return render(request, self.template_name, context)

class CategoryProductsView(View):
    """
    جزئیات گروه محصولات
    - محصولات + فیلترها + اطلاعات
    """
    template_name = 'product/category/category_products.html'

    def get(self, request, category_slug):
        # دریافت دسته‌بندی
        category = get_object_or_404(ProductCategory, slug=category_slug, is_active=True)

        # دریافت پارامترها
        page = request.GET.get('page', 1)
        order_by = request.GET.get('order_by', '-created_at')
        brand_slug = request.GET.get('brand')
        price_min = request.GET.get('price_min')
        price_max = request.GET.get('price_max')
        attribute_filters = {}

        # استخراج فیلترهای ویژگی‌ها از پارامترها
        for key, value in request.GET.items():
            if key.startswith('attr_') and value:
                attr_slug = key.replace('attr_', '')
                attribute_filters[attr_slug] = value

        # آماده‌سازی فیلترها
        filters = {}

        if brand_slug:
            filters['brand'] = brand_slug

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

        if attribute_filters:
            filters['attributes'] = attribute_filters

        # دریافت محصولات با استفاده از متد مدل
        products = category.get_products(**filters).order_by(order_by)

        # یا استفاده از Manager
        # products = Product.objects.get_by_category(category_slug, **filters)

        # صفحه‌بندی
        paginator = Paginator(products, 24)
        products_page = paginator.get_page(page)

        # دریافت اطلاعات اضافی
        subcategories = category.children.filter(is_active=True)

        # دریافت برندهای این دسته‌بندی
        brands_in_category = category.get_brands()

        # دریافت ویژگی‌های قابل فیلتر
        filterable_attributes = category.get_filterable_attributes()

        # دریافت محدوده قیمت
        price_range = category.get_price_range()

        # مسیر ناوبری
        breadcrumbs = ProductCategory.objects.get_breadcrumbs(category)

        context = {
            'category': category,
            'products': products_page,
            'subcategories': subcategories,
            'brands': brands_in_category,
            'filterable_attributes': filterable_attributes,
            'price_min': price_range['min'],
            'price_max': price_range['max'],
            'current_order': order_by,
            'current_brand': brand_slug,
            'current_price_min': price_min,
            'current_price_max': price_max,
            'current_attribute_filters': attribute_filters,
            'breadcrumbs': breadcrumbs,
            'total_products': products.count(),
            'title': category.get_seo_title(),
            'meta_description': category.get_seo_description(),
        }

        return render(request, self.template_name, context)

class CategoryDetailView(View):
    """
    صفحه جزئیات دسته‌بندی
    - اطلاعات + زیردسته‌ها + محصولات ویژه
    """
    template_name = 'product/category/category_detail.html'

    def get(self, request, category_slug):
        category = get_object_or_404(ProductCategory, slug=category_slug, is_active=True)

        # اطلاعات دسته‌بندی به صورت دیکشنری
        category_data = category.to_dict(include_related=True)

        # زیردسته‌ها
        children = category.children.filter(is_active=True)

        # محصولات جدید این دسته‌بندی
        new_products = category.get_products().order_by('-created_at')[:8]

        # محصولات پرفروش
        best_sellers = category.get_products().order_by('-created_at')[:8]

        # برندهای این دسته‌بندی
        brands = category.get_brands()[:10]

        # آمار
        stats = {
            'total_products': category.get_products_count(),
            'children_count': children.count(),
            'brands_count': brands.count(),
        }

        context = {
            'category': category,
            'category_data': category_data,
            'children': children,
            'new_products': new_products,
            'best_sellers': best_sellers,
            'brands': brands,
            'stats': stats,
            'breadcrumbs': ProductCategory.objects.get_breadcrumbs(category),
            'title': category.get_seo_title(),
            'meta_description': category.get_seo_description(),
        }

        return render(request, self.template_name, context)