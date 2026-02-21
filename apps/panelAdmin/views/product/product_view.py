from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Prefetch
from django.views.decorators.http import require_POST
from django.core.files.storage import default_storage
import json
import os
import uuid
from datetime import datetime
from apps.product.models import (
    Product, Category, Brand, Feature, ProductGallery,
    ProductFeature, FeatureValue, ProductSaleType,
    Rating, Comment,SaleType
)


# ========================
# CATEGORY CRUD
# ========================

def category_list(request):
    """لیست دسته‌بندی‌ها"""
    categories = Category.objects.all()
    return render(request, 'panelAdmin/products/category/list.html', {'categories': categories})

from django.utils.text import slugify

# در فایل views.py

def category_create(request):
    """ایجاد دسته‌بندی جدید"""

    # --- تغییر این خط ---
    # قبلاً: فقط دسته‌بندی‌های اصلی (parent=None) بود
    # categories = Category.objects.filter(parent=None)

    # الان: دریافت همه دسته‌بندی‌ها برای نمایش در لیست والدین
    categories = Category.objects.all().order_by('title')
    # -------------------

    if request.method == 'POST':
        try:
            title = request.POST.get('title')
            manual_slug = request.POST.get('slug')
            parent_id = request.POST.get('parent')
            image = request.FILES.get('image')
            is_active = request.POST.get('isActive') == 'on'

            if manual_slug:
                final_slug = slugify(manual_slug, allow_unicode=True)
            else:
                final_slug = slugify(title, allow_unicode=True)

            category = Category.objects.create(
                title=title,
                slug=final_slug,
                parent_id=parent_id if parent_id else None,
                image=image,
                isActive=is_active
            )
            messages.success(request, 'دسته‌بندی با موفقیت ایجاد شد')
            return redirect('panelAdmin:admin_category_list')
        except Exception as e:
            messages.error(request, f'خطا در ایجاد دسته‌بندی: {str(e)}')

    return render(request, 'panelAdmin/products/category/create.html', {'categories': categories})





def category_update(request, category_id):
    """ویرایش دسته‌بندی"""
    category = get_object_or_404(Category, id=category_id)
    categories = Category.objects.filter(parent=None).exclude(id=category_id)

    if request.method == 'POST':
        try:
            category.title = request.POST.get('title', category.title)
            category.parent_id = request.POST.get('parent') if request.POST.get('parent') else None

            if 'image' in request.FILES:
                category.image = request.FILES['image']

            category.isActive = request.POST.get('isActive') == 'on'
            category.save()

            messages.success(request, 'دسته‌بندی با موفقیت ویرایش شد')
            return redirect('panelAdmin:admin_category_list')
        except Exception as e:
            messages.error(request, f'خطا در ویرایش دسته‌بندی: {str(e)}')

    return render(request, 'panelAdmin/products/category/update.html', {
        'category': category,
        'categories': categories
    })

def category_delete(request, category_id):
    """حذف دسته‌بندی"""
    category = get_object_or_404(Category, id=category_id)

    if request.method == 'POST':
        try:
            category.delete()
            messages.success(request, 'دسته‌بندی با موفقیت حذف شد')
            return redirect('panelAdmin:admin_category_list')
        except Exception as e:
            messages.error(request, f'خطا در حذف دسته‌بندی: {str(e)}')

    return render(request, 'panelAdmin/products/category/delete_confirm.html', {'category': category})


# ========================
# BRAND CRUD
# ========================

def brand_list(request):
    """لیست برندها"""
    brands = Brand.objects.all()
    return render(request, 'panelAdmin/products/brand/list.html', {'brands': brands})

def brand_create(request):
    """ایجاد برند جدید"""
    if request.method == 'POST':
        try:
            brand = Brand.objects.create(
                title=request.POST.get('title'),
                slug=request.POST.get('slug'),  # ذخیره مستقیم slug
                description=request.POST.get('description'),
                logo=request.FILES.get('logo'),
                isActive=request.POST.get('isActive') == 'on'
            )
            messages.success(request, 'برند با موفقیت ایجاد شد')
            return redirect('panelAdmin:admin_brand_list')
        except Exception as e:
            messages.error(request, f'خطا در ایجاد برند: {str(e)}')

    return render(request, 'panelAdmin/products/brand/create.html')

def brand_update(request, brand_id):
    """ویرایش برند"""
    brand = get_object_or_404(Brand, id=brand_id)

    if request.method == 'POST':
        try:
            brand.title = request.POST.get('title', brand.title)
            brand.slug = request.POST.get('slug', brand.slug)  # ذخیره مستقیم slug
            brand.description = request.POST.get('description', brand.description)

            if 'logo' in request.FILES:
                brand.logo = request.FILES['logo']

            # بررسی حذف لوگو
            if request.POST.get('delete_logo') == 'true':
                brand.logo = None

            brand.isActive = request.POST.get('isActive') == 'on'
            brand.save()

            messages.success(request, 'برند با موفقیت ویرایش شد')
            return redirect('panelAdmin:admin_brand_list')
        except Exception as e:
            messages.error(request, f'خطا در ویرایش برند: {str(e)}')

    return render(request, 'panelAdmin/products/brand/update.html', {'brand': brand})



def brand_delete(request, brand_id):
    """حذف برند"""
    brand = get_object_or_404(Brand, id=brand_id)

    if request.method == 'POST':
        try:
            brand.delete()
            messages.success(request, 'برند با موفقیت حذف شد')
            return redirect('panelAdmin:admin_brand_list')
        except Exception as e:
            messages.error(request, f'خطا در حذف برند: {str(e)}')

    return render(request, 'panelAdmin/products/brand/delete_confirm.html', {'brand': brand})


# ========================
# FEATURE CRUD
# ========================

def feature_list(request):
    """لیست ویژگی‌ها"""
    features = Feature.objects.all()
    return render(request, 'panelAdmin/products/feature/list.html', {'features': features})

def feature_create(request):
    """ایجاد ویژگی جدید"""
    categories = Category.objects.all()

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # ایجاد ویژگی
                feature = Feature.objects.create(
                    title=request.POST.get('title'),
                    isActive=request.POST.get('isActive') == 'on'
                )

                # اضافه کردن دسته‌بندی‌ها
                selected_categories = request.POST.getlist('categories')
                if selected_categories:
                    feature.categories.set(selected_categories)

                # ذخیره مقادیر ویژگی
                values = request.POST.getlist('feature_values[]')
                for value in values:
                    if value.strip():  # فقط اگر مقدار خالی نباشد
                        FeatureValue.objects.create(
                            feature=feature,
                            value=value.strip()
                        )

                messages.success(request, 'ویژگی با موفقیت ایجاد شد')
                return redirect('panelAdmin:admin_feature_list')
        except Exception as e:
            messages.error(request, f'خطا در ایجاد ویژگی: {str(e)}')
            print(f"Error in feature_create: {str(e)}")  # برای دیباگ

    return render(request, 'panelAdmin/products/feature/create.html', {'categories': categories})

def feature_update(request, feature_id):
    """ویرایش ویژگی"""
    feature = get_object_or_404(Feature, id=feature_id)
    categories = Category.objects.all()
    selected_categories = feature.categories.all()

    if request.method == 'POST':
        try:
            with transaction.atomic():
                feature.title = request.POST.get('title', feature.title)
                feature.isActive = request.POST.get('isActive') == 'on'
                feature.save()

                # آپدیت دسته‌بندی‌ها
                selected_categories = request.POST.getlist('categories')
                feature.categories.set(selected_categories)

                # اضافه کردن مقادیر جدید
                new_values = request.POST.getlist('new_values[]')
                for value in new_values:
                    if value.strip():  # فقط اگر مقدار خالی نباشد
                        FeatureValue.objects.create(
                            feature=feature,
                            value=value.strip()
                        )

                messages.success(request, 'ویژگی با موفقیت ویرایش شد')
                return redirect('panelAdmin:admin_feature_list')
        except Exception as e:
            messages.error(request, f'خطا در ویرایش ویژگی: {str(e)}')
            print(f"Error in feature_update: {str(e)}")  # برای دیباگ

    return render(request, 'panelAdmin/products/feature/update.html', {
        'feature': feature,
        'categories': categories,
        'selected_categories': selected_categories
    })

def feature_delete(request, feature_id):
    """حذف ویژگی"""
    feature = get_object_or_404(Feature, id=feature_id)

    if request.method == 'POST':
        try:
            feature.delete()
            messages.success(request, 'ویژگی با موفقیت حذف شد')
            return redirect('panelAdmin:admin_feature_list')
        except Exception as e:
            messages.error(request, f'خطا در حذف ویژگی: {str(e)}')

    return render(request, 'panelAdmin/products/feature/delete_confirm.html', {'feature': feature})





# ========================
# FEATURE VALUE MANAGEMENT
# ========================

def feature_value_create(request, feature_id):
    """ایجاد مقدار جدید برای ویژگی"""
    feature = get_object_or_404(Feature, id=feature_id)

    if request.method == 'POST':
        try:
            value = request.POST.get('value', '').strip()
            if value:
                FeatureValue.objects.create(
                    feature=feature,
                    value=value
                )
                messages.success(request, 'مقدار با موفقیت اضافه شد')
            else:
                messages.error(request, 'مقدار نمی‌تواند خالی باشد')
        except Exception as e:
            messages.error(request, f'خطا در ایجاد مقدار: {str(e)}')

    return redirect('panelAdmin:admin_feature_update', feature_id=feature_id)

def feature_value_update(request, value_id):
    """ویرایش مقدار ویژگی"""
    feature_value = get_object_or_404(FeatureValue, id=value_id)
    feature_id = feature_value.feature.id

    if request.method == 'POST':
        try:
            value = request.POST.get('value', '').strip()
            if value:
                feature_value.value = value
                feature_value.save()
                messages.success(request, 'مقدار با موفقیت ویرایش شد')
            else:
                messages.error(request, 'مقدار نمی‌تواند خالی باشد')
        except Exception as e:
            messages.error(request, f'خطا در ویرایش مقدار: {str(e)}')

    return redirect('panelAdmin:admin_feature_update', feature_id=feature_id)

@require_POST
def feature_value_delete(request, value_id):
    """حذف مقدار ویژگی"""
    feature_value = get_object_or_404(FeatureValue, id=value_id)
    feature_id = feature_value.feature.id

    try:
        feature_value.delete()
        messages.success(request, 'مقدار با موفقیت حذف شد')
    except Exception as e:
        messages.error(request, f'خطا در حذف مقدار: {str(e)}')

    return redirect('panelAdmin:admin_feature_update', feature_id=feature_id)


# ========================
# PRODUCT CRUD
# ========================

def product_list(request):
    """لیست محصولات"""
    products = Product.objects.select_related('brand').prefetch_related('category').all()

    # فیلتر بر اساس جستجو
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(
            Q(title__icontains=search_query) |
            Q(slug__icontains=search_query) |
            Q(shortDescription__icontains=search_query)
        )

    # فیلتر بر اساس دسته‌بندی
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category__id=category_id)

    # فیلتر بر اساس برند
    brand_id = request.GET.get('brand')
    if brand_id:
        products = products.filter(brand__id=brand_id)

    # فیلتر بر اساس وضعیت
    status = request.GET.get('status')
    if status == 'active':
        products = products.filter(isActive=True)
    elif status == 'inactive':
        products = products.filter(isActive=False)

    paginator = Paginator(products, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.all()
    brands = Brand.objects.all()

    return render(request, 'panelAdmin/products/product/list.html', {
        'page_obj': page_obj,
        'categories': categories,
        'brands': brands,
        'search_query': search_query,
        'selected_category': category_id,
        'selected_brand': brand_id,
        'selected_status': status
    })

def product_create(request):
    """ایجاد محصول جدید"""
    categories = Category.objects.all()
    brands = Brand.objects.all()
    features = Feature.objects.filter(isActive=True).prefetch_related('featureValues')

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # دریافت اسلاگ از فرم
                slug = request.POST.get('slug', '').strip()
                title = request.POST.get('title')

                # اگر اسلاگ خالی بود، از عنوان ایجاد کن
                if not slug and title:
                    from django.utils.text import slugify
                    slug = slugify(title, allow_unicode=True)

                # بررسی تکراری بودن اسلاگ
                if slug:
                    base_slug = slug
                    counter = 1
                    while Product.objects.filter(slug=slug).exists():
                        slug = f"{base_slug}-{counter}"
                        counter += 1

                # ایجاد محصول
                product = Product.objects.create(
                    title=title,
                    slug=slug,  # ذخیره اسلاگ دستی
                    brand_id=request.POST.get('brand') if request.POST.get('brand') else None,
                    mainImage=request.FILES.get('mainImage'),
                    description=request.POST.get('description'),
                    shortDescription=request.POST.get('shortDescription'),
                    isActive=request.POST.get('isActive') == 'on'
                )

                # اضافه کردن دسته‌بندی‌ها
                selected_categories = request.POST.getlist('categories')
                if selected_categories:
                    product.category.set(selected_categories)

                # ایجاد گالری تصاویر
                gallery_images = request.FILES.getlist('gallery_images')
                alt_text = request.POST.get('altText', product.title)

                for image in gallery_images:
                    if image:
                        ProductGallery.objects.create(
                            product=product,
                            image=image,
                            altText=alt_text
                        )

                # مدیریت ویژگی‌ها از JSON
                features_json = request.POST.get('features_json')
                if features_json:
                    features_data = json.loads(features_json)
                    for feature_data in features_data:
                        feature_id = feature_data.get('feature_id')
                        value = feature_data.get('value')
                        filter_value_id = feature_data.get('filter_value_id')

                        if feature_id and value:
                            ProductFeature.objects.create(
                                product=product,
                                feature_id=feature_id,
                                value=value,
                                filterValue_id=filter_value_id if filter_value_id else None
                            )

                messages.success(request, f'محصول {product.title} با موفقیت ایجاد شد')
                return redirect('panelAdmin:admin_product_detail', product_id=product.id)

        except Exception as e:
            messages.error(request, f'خطا در ایجاد محصول: {str(e)}')
            print(f"Error: {str(e)}")

    return render(request, 'panelAdmin/products/product/create.html', {
        'categories': categories,
        'brands': brands,
        'features': features
    })



def product_detail(request, product_id):
    """مشاهده جزئیات محصول"""
    product = get_object_or_404(
        Product.objects.select_related('brand')
        .prefetch_related('category', 'galleries', 'featuresValue__feature', 'saleTypes'),
        id=product_id
    )

    # آمار کامنت‌ها و ریتینگ‌ها
    ratings = Rating.objects.filter(product=product)
    comments = Comment.objects.filter(product=product)

    return render(request, 'panelAdmin/products/product/detail.html', {
        'product': product,
        'ratings': ratings,
        'comments': comments,
        'comment_stats': product.comment_stats
    })

def product_update(request, product_id):
    """ویرایش محصول - با امکانات پیشرفته"""
    product = get_object_or_404(
        Product.objects.prefetch_related(
            'category',
            'galleries',
            Prefetch('featuresValue', queryset=ProductFeature.objects.select_related('feature'))
        ),
        id=product_id
    )

    categories = Category.objects.all()
    brands = Brand.objects.all()
    features = Feature.objects.filter(isActive=True).prefetch_related(
        Prefetch('featureValues', queryset=FeatureValue.objects.all())
    )
    selected_categories = product.category.all()

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # آپدیت اطلاعات پایه محصول
                product.title = request.POST.get('title', product.title)
                product.brand_id = request.POST.get('brand') if request.POST.get('brand') else None
                product.description = request.POST.get('description', product.description)
                product.shortDescription = request.POST.get('shortDescription', product.shortDescription)
                product.isActive = request.POST.get('isActive') == 'on'

                if 'mainImage' in request.FILES:
                    product.mainImage = request.FILES['mainImage']

                product.save()

                # آپدیت دسته‌بندی‌ها
                selected_categories = request.POST.getlist('categories')
                product.category.set(selected_categories)

                # آپدیت گالری - اضافه کردن عکس‌های جدید
                gallery_images = request.FILES.getlist('gallery_images')
                for image in gallery_images:
                    if image.size > 0:
                        ProductGallery.objects.create(
                            product=product,
                            image=image,
                            altText=request.POST.get('altText', product.title)
                        )

                # آپدیت ویژگی‌ها
                # حذف ویژگی‌های قبلی
                product.featuresValue.all().delete()

                # اضافه کردن ویژگی‌های جدید (روش پویا)
                features_json = request.POST.get('features_json')
                if features_json:
                    features_data = json.loads(features_json)
                    for feature_data in features_data:
                        if feature_data.get('feature_id') and feature_data.get('value'):
                            ProductFeature.objects.create(
                                product=product,
                                feature_id=feature_data['feature_id'],
                                value=feature_data['value'],
                                filterValue_id=feature_data.get('filter_value_id')
                            )

                messages.success(request, 'محصول با موفقیت ویرایش شد')
                return redirect('panelAdmin:admin_product_detail', product_id=product.id)

        except Exception as e:
            messages.error(request, f'خطا در ویرایش محصول: {str(e)}')

    # آماده‌سازی ویژگی‌های موجود برای نمایش در فرم
    product_features = []
    for pf in product.featuresValue.all():
        feature_values = []
        if pf.feature:
            feature_values = list(pf.feature.featureValues.values('id', 'value'))

        product_features.append({
            'feature_id': pf.feature.id if pf.feature else None,
            'feature_title': pf.feature.title if pf.feature else '',
            'value': pf.value,
            'filter_value_id': pf.filterValue.id if pf.filterValue else None,
            'filter_value': pf.filterValue.value if pf.filterValue else '',
            'available_values': feature_values
        })

    return render(request, 'panelAdmin/products/product/update.html', {
        'product': product,
        'categories': categories,
        'brands': brands,
        'features': features,
        'selected_categories': selected_categories,
        'product_features_json': json.dumps(product_features)
    })

def product_delete(request, product_id):
    """حذف محصول"""
    product = get_object_or_404(
        Product.objects.prefetch_related('galleries', 'saleTypes', 'featuresValue__feature'),
        id=product_id
    )

    # محاسبه آمار قبل از ارسال به تمپلیت
    galleries_count = product.galleries.count()
    sale_types_count = product.saleTypes.count()

    if request.method == 'POST':
        try:
            product_title = product.title
            product.delete()
            messages.success(request, f'محصول {product_title} با موفقیت حذف شد')
            return redirect('panelAdmin:admin_product_list')
        except Exception as e:
            messages.error(request, f'خطا در حذف محصول: {str(e)}')

    return render(request, 'panelAdmin/products/product/delete_confirm.html', {
        'product': product,
        'galleries_count': galleries_count,
        'sale_types_count': sale_types_count,
        'comment_stats': {
            'total_comments': product.total_comments,
            'average_rating': product.average_rating,
        }
    })

@require_POST
def delete_gallery_image(request, image_id):
    """حذف تصویر از گالری"""
    gallery_image = get_object_or_404(ProductGallery, id=image_id)
    product_id = gallery_image.product.id

    try:
        gallery_image.delete()
        messages.success(request, 'تصویر با موفقیت حذف شد')
    except Exception as e:
        messages.error(request, f'خطا در حذف تصویر: {str(e)}')

    return redirect('admin_product_update', product_id=product_id)


# ========================
# PRODUCT SALE TYPE CRUD
# ========================

def sale_type_create(request, product_id):
    """ایجاد نوع فروش برای محصول"""
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        try:
            # گرفتن مقادیر و تبدیل مقادیر خالی به None
            type_sale = request.POST.get('typeSale')
            price = request.POST.get('price')
            member_carton = request.POST.get('memberCarton')
            limited_sale = request.POST.get('limitedSale')
            title = request.POST.get('title')
            is_active = request.POST.get('isActive') == 'on'

            # تبدیل مقادیر خالی به None برای فیلدهای عددی
            if member_carton == '':
                member_carton = None
            if limited_sale == '':
                limited_sale = None

            # تبدیل به عدد اگر مقدار وجود دارد
            if member_carton:
                member_carton = int(member_carton)
            if limited_sale:
                limited_sale = int(limited_sale)

            sale_type = ProductSaleType.objects.create(
                product=product,
                typeSale=type_sale,
                price=price,
                memberCarton=member_carton,
                limitedSale=limited_sale,
                title=title,
                isActive=is_active
            )
            messages.success(request, 'نوع فروش با موفقیت اضافه شد')
            return redirect('panelAdmin:admin_product_detail', product_id=product.id)
        except ValueError as e:
            messages.error(request, f'خطا در مقادیر عددی: {str(e)}')
        except Exception as e:
            messages.error(request, f'خطا در ایجاد نوع فروش: {str(e)}')

    return render(request, 'panelAdmin/products/sale_type/create.html', {
        'product': product,
        'sale_types': SaleType.CHOICES
    })



def sale_type_update(request, sale_type_id):
    """ویرایش نوع فروش"""
    sale_type = get_object_or_404(ProductSaleType, id=sale_type_id)

    if request.method == 'POST':
        try:
            # گرفتن مقادیر و تبدیل مقادیر خالی به None
            type_sale = request.POST.get('typeSale', sale_type.typeSale)
            price = request.POST.get('price', sale_type.price)
            member_carton = request.POST.get('memberCarton')
            limited_sale = request.POST.get('limitedSale')
            title = request.POST.get('title', sale_type.title)
            is_active = request.POST.get('isActive') == 'on'

            # تبدیل مقادیر خالی به None برای فیلدهای عددی
            if member_carton == '':
                member_carton = None
            if limited_sale == '':
                limited_sale = None

            # تبدیل به عدد اگر مقدار وجود دارد
            if member_carton:
                member_carton = int(member_carton)
            if limited_sale:
                limited_sale = int(limited_sale)

            sale_type.typeSale = type_sale
            sale_type.price = price
            sale_type.memberCarton = member_carton
            sale_type.limitedSale = limited_sale
            sale_type.title = title
            sale_type.isActive = is_active
            sale_type.save()

            messages.success(request, 'نوع فروش با موفقیت ویرایش شد')
            return redirect('panelAdmin:admin_product_detail', product_id=sale_type.product.id)
        except ValueError as e:
            messages.error(request, f'خطا در مقادیر عددی: {str(e)}')
        except Exception as e:
            messages.error(request, f'خطا در ویرایش نوع فروش: {str(e)}')

    return render(request, 'panelAdmin/products/sale_type/update.html', {
        'sale_type': sale_type,
        'sale_types': SaleType.CHOICES
    })

def sale_type_delete(request, sale_type_id):
    """حذف نوع فروش"""
    sale_type = get_object_or_404(ProductSaleType, id=sale_type_id)
    product_id = sale_type.product.id

    if request.method == 'POST':
        try:
            sale_type.delete()
            messages.success(request, 'نوع فروش با موفقیت حذف شد')
        except Exception as e:
            messages.error(request, f'خطا در حذف نوع فروش: {str(e)}')

    return redirect('panelAdmin:admin_product_detail', product_id=product_id)


# ========================
# COMMENT MANAGEMENT
# ========================

def comment_list(request):
    """لیست کامنت‌ها"""
    comments = Comment.objects.select_related('user', 'product').all()

    # فیلتر بر اساس جستجو
    search_query = request.GET.get('search', '')
    if search_query:
        comments = comments.filter(
            Q(text__icontains=search_query) |
            Q(user__mobileNumber__icontains=search_query) |
            Q(user__name__icontains=search_query) |
            Q(user__family__icontains=search_query) |
            Q(product__title__icontains=search_query)
        )

    # فیلتر بر اساس محصول
    product_id = request.GET.get('product')
    if product_id:
        comments = comments.filter(product_id=product_id)

    # فیلتر بر اساس وضعیت
    status = request.GET.get('status')
    if status == 'active':
        comments = comments.filter(isActive=True)
    elif status == 'inactive':
        comments = comments.filter(isActive=False)

    # فیلتر بر اساس نوع
    comment_type = request.GET.get('type')
    if comment_type:
        comments = comments.filter(typeComment=comment_type)

    # مرتب‌سازی
    comments = comments.order_by('-createdAt')

    # محاسبه آمار
    active_comments_count = comments.filter(isActive=True).count()
    recommend_count = comments.filter(typeComment='recommend', isActive=True).count()
    not_recommend_count = comments.filter(typeComment='not_recommend', isActive=True).count()

    # صفحه‌بندی
    paginator = Paginator(comments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    products = Product.objects.all()

    return render(request, 'panelAdmin/products/comment/list.html', {
        'page_obj': page_obj,
        'products': products,
        'selected_product': product_id,
        'selected_status': status,
        'selected_type': comment_type,
        'search_query': search_query,
        'active_comments_count': active_comments_count,
        'recommend_count': recommend_count,
        'not_recommend_count': not_recommend_count,
    })


@require_POST
def comment_toggle(request, comment_id):
    """تغییر وضعیت فعال/غیرفعال کامنت"""
    comment = get_object_or_404(Comment, id=comment_id)

    try:
        comment.isActive = not comment.isActive
        comment.save()

        status = 'فعال' if comment.isActive else 'غیرفعال'
        messages.success(request, f'کامنت با موفقیت {status} شد')
    except Exception as e:
        messages.error(request, f'خطا در تغییر وضعیت کامنت: {str(e)}')

    return redirect('panelAdmin:admin_comment_list')

@require_POST
def bulk_comment_action(request):
    """عملیات گروهی روی کامنت‌ها"""
    if request.method == 'POST':
        comment_ids = request.POST.get('comment_ids', '').split(',')
        action = request.POST.get('bulk_action')

        if not comment_ids or not action:
            messages.error(request, 'لطفا کامنت‌ها و عملیات را انتخاب کنید')
            return redirect('panelAdmin:admin_comment_list')

        try:
            comments = Comment.objects.filter(id__in=comment_ids)

            if action == 'activate':
                comments.update(isActive=True)
                messages.success(request, f'{comments.count()} کامنت فعال شدند')
            elif action == 'deactivate':
                comments.update(isActive=False)
                messages.success(request, f'{comments.count()} کامنت غیرفعال شدند')
            elif action == 'delete':
                count = comments.count()
                comments.delete()
                messages.success(request, f'{count} کامنت حذف شدند')

        except Exception as e:
            messages.error(request, f'خطا در انجام عملیات گروهی: {str(e)}')

    return redirect('panelAdmin:admin_comment_list')


@require_POST
def comment_delete(request, comment_id):
    """حذف کامنت"""
    comment = get_object_or_404(Comment, id=comment_id)

    try:
        comment.delete()
        messages.success(request, 'کامنت با موفقیت حذف شد')
    except Exception as e:
        messages.error(request, f'خطا در حذف کامنت: {str(e)}')

    return redirect('panelAdmin:admin_comment_list')


# ========================
# AJAX VIEWS - امکانات جدید
# ========================

def get_feature_values(request):
    """دریافت مقادیر یک ویژگی"""
    feature_id = request.GET.get('feature_id')
    if feature_id:
        values = FeatureValue.objects.filter(feature_id=feature_id).values('id', 'value')
        return JsonResponse(list(values), safe=False)
    return JsonResponse([], safe=False)



def get_category_features(request):
    """دریافت ویژگی‌های مربوط به یک دسته‌بندی"""
    category_id = request.GET.get('category_id')
    if category_id:
        category = get_object_or_404(Category, id=category_id)
        features = Feature.objects.filter(
            categories=category,
            isActive=True
        ).prefetch_related('featureValues')

        data = [{
            'id': f.id,
            'title': f.title,
            'values': [{'id': v.id, 'value': v.value} for v in f.featureValues.all()]
        } for f in features]
        return JsonResponse(data, safe=False)
    return JsonResponse([], safe=False)


def get_feature_details(request):
    """دریافت جزئیات یک ویژگی به همراه مقادیر آن"""
    feature_id = request.GET.get('feature_id')
    if feature_id:
        try:
            feature = Feature.objects.filter(id=feature_id).prefetch_related('featureValues').first()
            if feature:
                data = {
                    'id': feature.id,
                    'title': feature.title,
                    'values': [{'id': v.id, 'value': v.value} for v in feature.featureValues.all()]
                }
                return JsonResponse(data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({})

def get_all_features(request):
    """دریافت تمام ویژگی‌ها به همراه مقادیر"""
    features = Feature.objects.filter(isActive=True).prefetch_related('featureValues')
    data = []
    for feature in features:
        data.append({
            'id': feature.id,
            'title': feature.title,
            'values': [{'id': v.id, 'value': v.value} for v in feature.featureValues.all()]
        })
    return JsonResponse(data, safe=False)




@require_POST
def ajax_upload_gallery_images(request):
    """آپلود تصاویر گالری به صورت AJAX"""
    if request.FILES:
        response_data = []
        for image in request.FILES.getlist('images'):
            try:
                # ذخیره موقت فایل
                temp_filename = f"temp_{uuid.uuid4().hex}_{image.name}"
                temp_path = os.path.join('temp', temp_filename)

                # ذخیره فایل
                saved_path = default_storage.save(temp_path, image)

                response_data.append({
                    'name': image.name,
                    'size': image.size,
                    'temp_path': saved_path,
                    'url': default_storage.url(saved_path)
                })
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=400)

        return JsonResponse({'success': True, 'files': response_data})

    return JsonResponse({'error': 'No images provided'}, status=400)

def get_product_features(request):
    """دریافت ویژگی‌های یک محصول خاص"""
    product_id = request.GET.get('product_id')
    if product_id:
        product = get_object_or_404(Product, id=product_id)
        features = product.featuresValue.select_related('feature', 'filterValue').all()

        data = [{
            'feature_id': pf.feature.id if pf.feature else None,
            'feature_title': pf.feature.title if pf.feature else '',
            'value': pf.value,
            'filter_value_id': pf.filterValue.id if pf.filterValue else None,
            'filter_value': pf.filterValue.value if pf.filterValue else ''
        } for pf in features]

        return JsonResponse(data, safe=False)

    return JsonResponse([], safe=False)

# تابع کمکی برای ایجاد ویژگی‌های پویا
def get_dynamic_features_html(request):
    """دریافت HTML برای فرم ویژگی‌های پویا"""
    features = Feature.objects.filter(isActive=True).prefetch_related('featureValues')

    # ایجاد HTML برای انتخاب ویژگی‌ها
    html = ""
    for feature in features:
        values_html = "".join([
            f'<option value="{value.id}">{value.value}</option>'
            for value in feature.featureValues.all()
        ])

        html += f"""
        <div class="feature-item" data-feature-id="{feature.id}">
            <div class="row mb-3">
                <div class="col-md-4">
                    <label class="form-label">ویژگی</label>
                    <input type="text" class="form-control" value="{feature.title}" readonly>
                </div>
                <div class="col-md-3">
                    <label class="form-label">مقدار</label>
                    <input type="text" class="form-control feature-value"
                           placeholder="مقدار را وارد کنید">
                </div>
                <div class="col-md-3">
                    <label class="form-label">مقدار فیلترینگ</label>
                    <select class="form-select feature-filter-value">
                        <option value="">انتخاب کنید</option>
                        {values_html}
                    </select>
                </div>
                <div class="col-md-2">
                    <label class="form-label">&nbsp;</label>
                    <button type="button" class="btn btn-danger w-100 remove-feature">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        </div>
        """

    return HttpResponse(html)