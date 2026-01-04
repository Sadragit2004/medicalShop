from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q, Count
from datetime import datetime, timedelta
from apps.discount.models import Copon, DiscountBasket, DiscountDetail
from apps.product.models import Product, Category, Brand

# ========================
# COUPON CRUD
# ========================

def coupon_list(request):
    """لیست کوپن‌های تخفیف"""
    coupons = Copon.objects.all().order_by('-id')

    # فیلترها
    search_query = request.GET.get('search', '')
    status = request.GET.get('status', '')
    date_filter = request.GET.get('date_filter', '')

    if search_query:
        coupons = coupons.filter(copon__icontains=search_query)

    if status == 'active':
        coupons = coupons.filter(isActive=True)
    elif status == 'inactive':
        coupons = coupons.filter(isActive=False)

    now = timezone.now()
    if date_filter == 'expired':
        coupons = coupons.filter(endDate__lt=now)
    elif date_filter == 'current':
        coupons = coupons.filter(startDate__lte=now, endDate__gte=now)
    elif date_filter == 'upcoming':
        coupons = coupons.filter(startDate__gt=now)

    # صفحه‌بندی
    paginator = Paginator(coupons, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # آمار
    total_coupons = coupons.count()
    active_coupons = coupons.filter(isActive=True).count()
    expired_coupons = coupons.filter(endDate__lt=now).count()

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'selected_status': status,
        'selected_date_filter': date_filter,
        'total_coupons': total_coupons,
        'active_coupons': active_coupons,
        'expired_coupons': expired_coupons,
        'now': now,
    }

    return render(request, 'panelAdmin/discounts/coupon/list.html', context)

def coupon_create(request):
    """ایجاد کوپن تخفیف جدید"""
    if request.method == 'POST':
        try:
            # دریافت داده‌ها
            code = request.POST.get('copon', '').strip().upper()
            discount = int(request.POST.get('discount', 0))
            start_date = request.POST.get('startDate')
            end_date = request.POST.get('endDate')
            is_active = request.POST.get('isActive') == 'on'

            # اعتبارسنجی
            if not code:
                messages.error(request, 'کد کوپن الزامی است')
                return redirect('panelAdmin:admin_coupon_create')

            if discount < 1 or discount > 100:
                messages.error(request, 'درصد تخفیف باید بین ۱ تا ۱۰۰ باشد')
                return redirect('panelAdmin:admin_coupon_create')

            # بررسی تکراری نبودن کد
            if Copon.objects.filter(copon=code).exists():
                messages.error(request, 'این کد کوپن قبلاً استفاده شده است')
                return redirect('panelAdmin:admin_coupon_create')

            # ایجاد کوپن
            coupon = Copon.objects.create(
                copon=code,
                discount=discount,
                startDate=datetime.fromisoformat(start_date.replace('Z', '+00:00')),
                endDate=datetime.fromisoformat(end_date.replace('Z', '+00:00')),
                isActive=is_active
            )

            messages.success(request, f'کوپن {code} با موفقیت ایجاد شد')
            return redirect('panelAdmin:admin_coupon_detail', coupon_id=coupon.id)

        except Exception as e:
            messages.error(request, f'خطا در ایجاد کوپن: {str(e)}')
            return redirect('panelAdmin:admin_coupon_create')

    # تنظیم تاریخ‌های پیش‌فرض
    now = timezone.now()
    default_start = now + timedelta(hours=1)
    default_end = now + timedelta(days=30)

    context = {
        'default_start': default_start.strftime('%Y-%m-%dT%H:%M'),
        'default_end': default_end.strftime('%Y-%m-%dT%H:%M'),
    }

    return render(request, 'panelAdmin/discounts/coupon/create.html', context)

def coupon_detail(request, coupon_id):
    """مشاهده جزئیات کوپن"""
    coupon = get_object_or_404(Copon, id=coupon_id)
    now = timezone.now()

    # بررسی وضعیت
    is_expired = coupon.endDate < now
    is_upcoming = coupon.startDate > now
    is_current = coupon.startDate <= now <= coupon.endDate

    context = {
        'coupon': coupon,
        'is_expired': is_expired,
        'is_upcoming': is_upcoming,
        'is_current': is_current,
        'now': now,
    }

    return render(request, 'panelAdmin/discounts/coupon/detail.html', context)

def coupon_update(request, coupon_id):
    """ویرایش کوپن تخفیف"""
    coupon = get_object_or_404(Copon, id=coupon_id)

    if request.method == 'POST':
        try:
            # دریافت داده‌ها
            code = request.POST.get('copon', '').strip().upper()
            discount = int(request.POST.get('discount', 0))
            start_date = request.POST.get('startDate')
            end_date = request.POST.get('endDate')
            is_active = request.POST.get('isActive') == 'on'

            # اعتبارسنجی
            if not code:
                messages.error(request, 'کد کوپن الزامی است')
                return redirect('panelAdmin:admin_coupon_update', coupon_id=coupon_id)

            if discount < 1 or discount > 100:
                messages.error(request, 'درصد تخفیف باید بین ۱ تا ۱۰۰ باشد')
                return redirect('panelAdmin:admin_coupon_update', coupon_id=coupon_id)

            # بررسی تکراری نبودن کد (به جز خودش)
            if Copon.objects.filter(copon=code).exclude(id=coupon_id).exists():
                messages.error(request, 'این کد کوپن قبلاً استفاده شده است')
                return redirect('panelAdmin:admin_coupon_update', coupon_id=coupon_id)

            # آپدیت
            coupon.copon = code
            coupon.discount = discount
            coupon.startDate = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            coupon.endDate = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            coupon.isActive = is_active
            coupon.save()

            messages.success(request, 'کوپن با موفقیت ویرایش شد')
            return redirect('panelAdmin:admin_coupon_detail', coupon_id=coupon.id)

        except Exception as e:
            messages.error(request, f'خطا در ویرایش کوپن: {str(e)}')
            return redirect('panelAdmin:admin_coupon_update', coupon_id=coupon_id)

    # فرمت تاریخ برای input
    start_date_formatted = coupon.startDate.strftime('%Y-%m-%dT%H:%M')
    end_date_formatted = coupon.endDate.strftime('%Y-%m-%dT%H:%M')

    context = {
        'coupon': coupon,
        'start_date_formatted': start_date_formatted,
        'end_date_formatted': end_date_formatted,
    }

    return render(request, 'panelAdmin/discounts/coupon/update.html', context)

def coupon_delete(request, coupon_id):
    """حذف کوپن تخفیف"""
    coupon = get_object_or_404(Copon, id=coupon_id)

    if request.method == 'POST':
        try:
            coupon_code = coupon.copon
            coupon.delete()
            messages.success(request, f'کوپن {coupon_code} با موفقیت حذف شد')
            return redirect('panelAdmin:admin_coupon_list')
        except Exception as e:
            messages.error(request, f'خطا در حذف کوپن: {str(e)}')
            return redirect('panelAdmin:admin_coupon_detail', coupon_id=coupon_id)

    return render(request, 'panelAdmin/discounts/coupon/delete_confirm.html', {'coupon': coupon})

def coupon_toggle(request, coupon_id):
    """تغییر وضعیت فعال/غیرفعال کوپن"""
    coupon = get_object_or_404(Copon, id=coupon_id)

    if request.method == 'POST':
        try:
            coupon.isActive = not coupon.isActive
            coupon.save()

            status = 'فعال' if coupon.isActive else 'غیرفعال'
            messages.success(request, f'کوپن با موفقیت {status} شد')
        except Exception as e:
            messages.error(request, f'خطا در تغییر وضعیت کوپن: {str(e)}')

    return redirect('panelAdmin:admin_coupon_detail', coupon_id=coupon.id)

# ========================
# DISCOUNT BASKET CRUD
# ========================

def discount_basket_list(request):
    """لیست سبدهای تخفیف"""
    baskets = DiscountBasket.objects.all().order_by('-id')

    # فیلترها
    search_query = request.GET.get('search', '')
    status = request.GET.get('status', '')
    is_amazing = request.GET.get('is_amazing', '')
    date_filter = request.GET.get('date_filter', '')

    if search_query:
        baskets = baskets.filter(discountTitle__icontains=search_query)

    if status == 'active':
        baskets = baskets.filter(isActive=True)
    elif status == 'inactive':
        baskets = baskets.filter(isActive=False)

    if is_amazing == 'yes':
        baskets = baskets.filter(isamzing=True)
    elif is_amazing == 'no':
        baskets = baskets.filter(isamzing=False)

    now = timezone.now()
    if date_filter == 'expired':
        baskets = baskets.filter(endDate__lt=now)
    elif date_filter == 'current':
        baskets = baskets.filter(startDate__lte=now, endDate__gte=now)
    elif date_filter == 'upcoming':
        baskets = baskets.filter(startDate__gt=now)

    # محاسبه تعداد محصولات
    for basket in baskets:
        basket.product_count = DiscountDetail.objects.filter(discountBasket=basket).count()

    # صفحه‌بندی
    paginator = Paginator(baskets, 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # آمار
    total_baskets = baskets.count()
    active_baskets = baskets.filter(isActive=True).count()
    amazing_baskets = baskets.filter(isamzing=True).count()

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'selected_status': status,
        'selected_is_amazing': is_amazing,
        'selected_date_filter': date_filter,
        'total_baskets': total_baskets,
        'active_baskets': active_baskets,
        'amazing_baskets': amazing_baskets,
        'now': now,
    }

    return render(request, 'panelAdmin/discounts/basket/list.html', context)

def discount_basket_create(request):
    """ایجاد سبد تخفیف جدید"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # دریافت داده‌ها
                title = request.POST.get('discountTitle', '').strip()
                discount = int(request.POST.get('discount', 0))
                start_date = request.POST.get('startDate')
                end_date = request.POST.get('endDate')
                is_active = request.POST.get('isActive') == 'on'
                is_amazing = request.POST.get('isamzing') == 'on'
                product_ids = request.POST.getlist('products')

                # دیباگ - چاپ مقادیر دریافتی
                print(f"Title: {title}")
                print(f"Discount: {discount}")
                print(f"Product IDs: {product_ids}")
                print(f"Product IDs count: {len(product_ids)}")

                # اعتبارسنجی
                if not title:
                    messages.error(request, 'عنوان سبد تخفیف الزامی است')
                    return redirect('panelAdmin:admin_discount_basket_create')

                if discount < 1 or discount > 100:
                    messages.error(request, 'درصد تخفیف باید بین ۱ تا ۱۰۰ باشد')
                    return redirect('panelAdmin:admin_discount_basket_create')

                if not product_ids:
                    messages.error(request, 'حداقل یک محصول باید انتخاب شود')
                    return redirect('panelAdmin:admin_discount_basket_create')

                # ایجاد سبد تخفیف
                basket = DiscountBasket.objects.create(
                    discountTitle=title,
                    discount=discount,
                    startDate=datetime.fromisoformat(start_date.replace('Z', '+00:00')),
                    endDate=datetime.fromisoformat(end_date.replace('Z', '+00:00')),
                    isActive=is_active,
                    isamzing=is_amazing
                )

                # اضافه کردن محصولات
                added_count = 0
                for product_id in product_ids:
                    try:
                        product = Product.objects.get(id=product_id, isActive=True)
                        DiscountDetail.objects.create(
                            discountBasket=basket,
                            product=product
                        )
                        added_count += 1
                        print(f"Added product: {product_id} - {product.title}")
                    except Product.DoesNotExist:
                        print(f"Product not found: {product_id}")
                        continue

                print(f"Total products added: {added_count}")

                messages.success(request, f'سبد تخفیف {title} با {added_count} محصول ایجاد شد')
                return redirect('panelAdmin:admin_discount_basket_detail', basket_id=basket.id)

        except Exception as e:
            messages.error(request, f'خطا در ایجاد سبد تخفیف: {str(e)}')
            import traceback
            traceback.print_exc()
            return redirect('panelAdmin:admin_discount_basket_create')

    # دریافت دسته‌بندی‌ها و برندها
    categories = Category.objects.filter(isActive=True, parent__isnull=True).prefetch_related('children')
    brands = Brand.objects.filter(isActive=True)

    # تنظیم تاریخ‌های پیش‌فرض
    now = timezone.now()
    default_start = now + timedelta(hours=1)
    default_end = now + timedelta(days=30)

    context = {
        'categories': categories,
        'brands': brands,
        'default_start': default_start.strftime('%Y-%m-%dT%H:%M'),
        'default_end': default_end.strftime('%Y-%m-%dT%H:%M'),
    }

    return render(request, 'panelAdmin/discounts/basket/create.html', context)

def discount_basket_detail(request, basket_id):
    """مشاهده جزئیات سبد تخفیف"""
    basket = get_object_or_404(DiscountBasket, id=basket_id)

    # دریافت محصولات مرتبط از طریق DiscountDetail
    discount_details = DiscountDetail.objects.filter(discountBasket=basket).select_related('product__brand')

    # آماده‌سازی داده‌های محصولات
    products_list = []
    for detail in discount_details:
        product = detail.product
        sale_type = product.saleTypes.first()
        original_price = sale_type.price if sale_type else 0

        # محاسبه قیمت با تخفیف (در پایتون)
        discount_percent = basket.discount
        if original_price > 0:
            discount_amount = (original_price * discount_percent) // 100
            final_price = original_price - discount_amount
        else:
            discount_amount = 0
            final_price = 0

        products_list.append({
            'detail': detail,
            'product': product,
            'original_price': original_price,
            'discount_amount': discount_amount,
            'final_price': final_price,
            'discount_percent': discount_percent,
            'has_image': bool(product.mainImage)
        })

    now = timezone.now()
    is_expired = basket.endDate < now
    is_upcoming = basket.startDate > now
    is_current = basket.startDate <= now <= basket.endDate

    context = {
        'discount_basket': basket,
        'products_list': products_list,  # استفاده از products_list به جای discount_details
        'product_count': len(products_list),
        'is_expired': is_expired,
        'is_upcoming': is_upcoming,
        'is_current': is_current,
        'now': now,
    }

    return render(request, 'panelAdmin/discounts/basket/detail.html', context)




def discount_basket_update(request, basket_id):
    """ویرایش سبد تخفیف"""
    basket = get_object_or_404(DiscountBasket, id=basket_id)

    # دریافت محصولات فعلی از طریق DiscountDetail
    discount_details = DiscountDetail.objects.filter(discountBasket=basket)
    current_product_ids = list(discount_details.values_list('product_id', flat=True))

    # دریافت دسته‌بندی‌ها و برندها
    categories = Category.objects.filter(isActive=True, parent__isnull=True).prefetch_related('children')
    brands = Brand.objects.filter(isActive=True)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # دریافت داده‌ها
                title = request.POST.get('discountTitle', '').strip()
                discount = int(request.POST.get('discount', 0))
                start_date = request.POST.get('startDate')
                end_date = request.POST.get('endDate')
                is_active = request.POST.get('isActive') == 'on'
                is_amazing = request.POST.get('isamzing') == 'on'
                product_ids = request.POST.getlist('products')

                # اعتبارسنجی
                if not title:
                    messages.error(request, 'عنوان سبد تخفیف الزامی است')
                    return redirect('panelAdmin:admin_discount_basket_update', basket_id=basket_id)

                if discount < 1 or discount > 100:
                    messages.error(request, 'درصد تخفیف باید بین ۱ تا ۱۰۰ باشد')
                    return redirect('panelAdmin:admin_discount_basket_update', basket_id=basket_id)

                if not product_ids:
                    messages.error(request, 'حداقل یک محصول باید انتخاب شود')
                    return redirect('panelAdmin:admin_discount_basket_update', basket_id=basket_id)

                # آپدیت سبد تخفیف
                basket.discountTitle = title
                basket.discount = discount
                basket.startDate = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                basket.endDate = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                basket.isActive = is_active
                basket.isamzing = is_amazing
                basket.save()

                # حذف محصولات قبلی و اضافه کردن جدید
                discount_details.delete()

                for product_id in product_ids:
                    try:
                        product = Product.objects.get(id=product_id, isActive=True)
                        DiscountDetail.objects.create(
                            discountBasket=basket,
                            product=product
                        )
                    except Product.DoesNotExist:
                        continue

                messages.success(request, 'سبد تخفیف با موفقیت ویرایش شد')
                return redirect('panelAdmin:admin_discount_basket_detail', basket_id=basket.id)

        except Exception as e:
            messages.error(request, f'خطا در ویرایش سبد تخفیف: {str(e)}')
            return redirect('panelAdmin:admin_discount_basket_update', basket_id=basket_id)

    # فرمت تاریخ برای input
    start_date_formatted = basket.startDate.strftime('%Y-%m-%dT%H:%M')
    end_date_formatted = basket.endDate.strftime('%Y-%m-%dT%H:%M')

    context = {
        'discount_basket': basket,
        'categories': categories,
        'brands': brands,
        'selected_products': current_product_ids,
        'start_date_formatted': start_date_formatted,
        'end_date_formatted': end_date_formatted,
    }

    return render(request, 'panelAdmin/discounts/basket/update.html', context)

def discount_basket_delete(request, basket_id):
    """حذف سبد تخفیف"""
    basket = get_object_or_404(DiscountBasket, id=basket_id)

    if request.method == 'POST':
        try:
            basket_title = basket.discountTitle
            basket.delete()
            messages.success(request, f'سبد تخفیف {basket_title} با موفقیت حذف شد')
            return redirect('panelAdmin:admin_discount_basket_list')
        except Exception as e:
            messages.error(request, f'خطا در حذف سبد تخفیف: {str(e)}')
            return redirect('panelAdmin:admin_discount_basket_detail', basket_id=basket_id)

    return render(request, 'panelAdmin/discounts/basket/delete_confirm.html', {'discount_basket': basket})

def discount_basket_toggle(request, basket_id):
    """تغییر وضعیت فعال/غیرفعال سبد تخفیف"""
    basket = get_object_or_404(DiscountBasket, id=basket_id)

    if request.method == 'POST':
        try:
            basket.isActive = not basket.isActive
            basket.save()

            status = 'فعال' if basket.isActive else 'غیرفعال'
            messages.success(request, f'سبد تخفیف با موفقیت {status} شد')
        except Exception as e:
            messages.error(request, f'خطا در تغییر وضعیت سبد تخفیف: {str(e)}')

    return redirect('panelAdmin:admin_discount_basket_detail', basket_id=basket.id)

def remove_product_from_basket(request, detail_id):
    """حذف محصول از سبد تخفیف"""
    detail = get_object_or_404(DiscountDetail, id=detail_id)
    basket_id = detail.discountBasket.id

    if request.method == 'POST':
        try:
            product_name = detail.product.title
            detail.delete()
            messages.success(request, f'محصول {product_name} از سبد تخفیف حذف شد')
        except Exception as e:
            messages.error(request, f'خطا در حذف محصول از سبد تخفیف: {str(e)}')

    return redirect('panelAdmin:admin_discount_basket_detail', basket_id=basket_id)

# ========================
# AJAX VIEWS
# ========================

def search_products_ajax(request):
    """جستجوی پیشرفته محصولات"""
    search_term = request.GET.get('q', '')
    category_id = request.GET.get('category_id', '')
    brand_id = request.GET.get('brand_id', '')
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 12))

    # فیلتر پایه
    products = Product.objects.filter(isActive=True).select_related('brand').prefetch_related('category')

    # اعمال فیلترها
    if search_term:
        products = products.filter(
            Q(title__icontains=search_term) |
            Q(slug__icontains=search_term) |
            Q(brand__title__icontains=search_term) |
            Q(category__title__icontains=search_term)
        )

    if category_id:
        products = products.filter(category__id=category_id)

    if brand_id:
        products = products.filter(brand__id=brand_id)

    # تعداد کل محصولات
    total_count = products.count()

    # صفحه‌بندی
    start = (page - 1) * limit
    end = start + limit
    paginated_products = products.distinct()[start:end]

    # آماده‌سازی داده‌ها
    results = []
    for product in paginated_products:
        # دریافت قیمت
        sale_type = product.saleTypes.first()
        price = sale_type.price if sale_type else 0

        # دریافت دسته‌بندی‌ها
        categories = []
        for cat in product.category.all()[:2]:
            categories.append({'id': cat.id, 'title': cat.title})

        # دریافت تصویر
        image_url = ''
        if product.mainImage:
            try:
                image_url = product.mainImage.url
            except:
                image_url = ''

        results.append({
            'id': str(product.id),  # تبدیل به string
            'title': product.title,
            'image': image_url,
            'price': price,
            'price_formatted': f'{price:,}',
            'brand': product.brand.title if product.brand else 'بدون برند',
            'brand_id': str(product.brand.id) if product.brand else None,
            'categories': categories,
            'has_image': bool(product.mainImage)
        })

    # دریافت دسته‌بندی‌ها و برندهای موجود برای فیلترها
    if products.exists():
        # استفاده از product__in به جای products__in (بستگی به مدل Category دارد)
        try:
            all_categories = Category.objects.filter(
                isActive=True,
                product__in=products  # بررسی کنید کدام یک کار می‌کند
            ).distinct().values('id', 'title')[:20]
        except:
            all_categories = Category.objects.filter(
                isActive=True,
                products__in=products  # حالت دیگر
            ).distinct().values('id', 'title')[:20]

        all_brands = Brand.objects.filter(
            isActive=True,
            products__in=products
        ).distinct().values('id', 'title')[:20]
    else:
        all_categories = []
        all_brands = []

    return JsonResponse({
        'success': True,
        'results': results,
        'total_count': total_count,
        'current_page': page,
        'total_pages': (total_count + limit - 1) // limit,
        'categories': list(all_categories),
        'brands': list(all_brands)
    })

def get_product_details(request):
    """دریافت جزئیات محصول"""
    product_id = request.GET.get('product_id')

    if product_id:
        try:
            product = Product.objects.get(id=product_id, isActive=True)
            sale_type = product.saleTypes.first()
            price = sale_type.price if sale_type else 0

            data = {
                'id': product.id,
                'title': product.title,
                'image': product.mainImage.url if product.mainImage else '',
                'price': price,
                'price_formatted': f'{price:,}',
                'brand': product.brand.title if product.brand else 'بدون برند',
                'categories': [cat.title for cat in product.category.all()[:2]],
                'is_active': product.isActive
            }
            return JsonResponse({'success': True, 'product': data})
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'محصول یافت نشد'}, status=404)

    return JsonResponse({'success': False, 'error': 'آیدی محصول ارسال نشده'}, status=400)

def get_all_categories_ajax(request):
    """دریافت تمام دسته‌بندی‌ها"""
    categories = Category.objects.filter(isActive=True, parent__isnull=True).prefetch_related('children')

    def build_category_tree(category):
        return {
            'id': category.id,
            'title': category.title,
            'children': [build_category_tree(child) for child in category.children.all() if child.isActive]
        }

    categories_tree = [build_category_tree(cat) for cat in categories]

    return JsonResponse({'success': True, 'categories': categories_tree})

def get_all_brands_ajax(request):
    """دریافت تمام برندها"""
    brands = Brand.objects.filter(isActive=True).values('id', 'title')
    return JsonResponse({'success': True, 'brands': list(brands)})

def get_products_bulk_ajax(request):
    """دریافت گروهی محصولات"""
    product_ids = request.GET.getlist('ids[]')

    if product_ids:
        products = Product.objects.filter(
            id__in=product_ids,
            isActive=True
        ).select_related('brand').prefetch_related('category')

        results = []
        for product in products:
            sale_type = product.saleTypes.first()
            price = sale_type.price if sale_type else 0

            results.append({
                'id': product.id,
                'title': product.title,
                'image': product.mainImage.url if product.mainImage else '',
                'price': price,
                'price_formatted': f'{price:,}',
                'brand': product.brand.title if product.brand else 'بدون برند',
                'categories': [cat.title for cat in product.category.all()[:2]]
            })

        return JsonResponse({'success': True, 'products': results})

    return JsonResponse({'success': False, 'error': 'آیدی‌ای ارسال نشده'}, status=400)

# ========================
# REPORT VIEWS
# ========================

def discount_report(request):
    """گزارش تخفیف‌ها"""
    now = timezone.now()

    # آمار کوپن‌ها
    total_coupons = Copon.objects.count()
    active_coupons = Copon.objects.filter(isActive=True).count()
    expired_coupons = Copon.objects.filter(endDate__lt=now).count()
    current_coupons = Copon.objects.filter(startDate__lte=now, endDate__gte=now).count()

    # آمار سبدهای تخفیف
    total_baskets = DiscountBasket.objects.count()
    active_baskets = DiscountBasket.objects.filter(isActive=True).count()
    amazing_baskets = DiscountBasket.objects.filter(isamzing=True).count()
    current_baskets = DiscountBasket.objects.filter(startDate__lte=now, endDate__gte=now).count()

    # محصولات دارای تخفیف
    products_with_discount = Product.objects.filter(
        productofdiscount__isnull=False  # اینجا productofdiscount است
    ).distinct().count()

    # سبدهای تخفیف فعال امروز
    today_baskets = DiscountBasket.objects.filter(
        isActive=True,
        startDate__lte=now,
        endDate__gte=now
    )

    context = {
        'total_coupons': total_coupons,
        'active_coupons': active_coupons,
        'expired_coupons': expired_coupons,
        'current_coupons': current_coupons,

        'total_baskets': total_baskets,
        'active_baskets': active_baskets,
        'amazing_baskets': amazing_baskets,
        'current_baskets': current_baskets,

        'products_with_discount': products_with_discount,
        'today_baskets': today_baskets,
        'now': now,
    }

    return render(request, 'panelAdmin/discounts/report.html', context)