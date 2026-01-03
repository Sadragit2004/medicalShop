# views/discount_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q
from datetime import datetime
from apps.discount.models import Copon, DiscountBasket, DiscountDetail, Product


# ========================
# COUPON CRUD
# ========================

def coupon_list(request):
    """لیست کوپن‌های تخفیف"""
    coupons = Copon.objects.all()

    # فیلتر بر اساس وضعیت فعال/غیرفعال
    status = request.GET.get('status')
    if status == 'active':
        coupons = coupons.filter(isActive=True)
    elif status == 'inactive':
        coupons = coupons.filter(isActive=False)

    # فیلتر بر اساس جستجو
    search_query = request.GET.get('search', '')
    if search_query:
        coupons = coupons.filter(
            Q(copon__icontains=search_query)
        )

    # فیلتر بر اساس تاریخ
    date_filter = request.GET.get('date_filter')
    if date_filter == 'expired':
        coupons = coupons.filter(endDate__lt=timezone.now())
    elif date_filter == 'upcoming':
        coupons = coupons.filter(startDate__gt=timezone.now())
    elif date_filter == 'current':
        now = timezone.now()
        coupons = coupons.filter(startDate__lte=now, endDate__gte=now)

    paginator = Paginator(coupons, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'panelAdmin/discount/coupon/list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'selected_status': status,
        'selected_date_filter': date_filter,
        'now': timezone.now()
    })

def coupon_create(request):
    """ایجاد کوپن تخفیف جدید"""
    if request.method == 'POST':
        try:
            # تبدیل تاریخ‌ها به datetime
            start_date_str = request.POST.get('startDate')
            end_date_str = request.POST.get('endDate')

            start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')

            coupon = Copon.objects.create(
                copon=request.POST.get('copon'),
                startDate=start_date,
                endDate=end_date,
                discount=request.POST.get('discount'),
                isActive=request.POST.get('isActive') == 'on'
            )

            messages.success(request, f'کوپن {coupon.copon} با موفقیت ایجاد شد')
            return redirect('admin_coupon_list')

        except Exception as e:
            messages.error(request, f'خطا در ایجاد کوپن: {str(e)}')

    return render(request, 'panelAdmin/discount/coupon/create.html')

def coupon_update(request, coupon_id):
    """ویرایش کوپن تخفیف"""
    coupon = get_object_or_404(Copon, id=coupon_id)

    if request.method == 'POST':
        try:
            # تبدیل تاریخ‌ها به datetime
            start_date_str = request.POST.get('startDate')
            end_date_str = request.POST.get('endDate')

            if start_date_str:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
                coupon.startDate = start_date

            if end_date_str:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')
                coupon.endDate = end_date

            coupon.copon = request.POST.get('copon', coupon.copon)
            coupon.discount = request.POST.get('discount', coupon.discount)
            coupon.isActive = request.POST.get('isActive') == 'on'
            coupon.save()

            messages.success(request, 'کوپن با موفقیت ویرایش شد')
            return redirect('admin_coupon_list')

        except Exception as e:
            messages.error(request, f'خطا در ویرایش کوپن: {str(e)}')

    # فرمت تاریخ برای ورودی datetime-local
    start_date_formatted = coupon.startDate.strftime('%Y-%m-%dT%H:%M') if coupon.startDate else ''
    end_date_formatted = coupon.endDate.strftime('%Y-%m-%dT%H:%M') if coupon.endDate else ''

    return render(request, 'panelAdmin/discount/coupon/update.html', {
        'coupon': coupon,
        'start_date_formatted': start_date_formatted,
        'end_date_formatted': end_date_formatted
    })

def coupon_delete(request, coupon_id):
    """حذف کوپن تخفیف"""
    coupon = get_object_or_404(Copon, id=coupon_id)

    if request.method == 'POST':
        try:
            coupon_code = coupon.copon
            coupon.delete()
            messages.success(request, f'کوپن {coupon_code} با موفقیت حذف شد')
            return redirect('admin_coupon_list')
        except Exception as e:
            messages.error(request, f'خطا در حذف کوپن: {str(e)}')

    return render(request, 'panelAdmin/discount/coupon/delete_confirm.html', {'coupon': coupon})

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

    return redirect('admin_coupon_list')

def coupon_detail(request, coupon_id):
    """مشاهده جزئیات کوپن"""
    coupon = get_object_or_404(Copon, id=coupon_id)

    # بررسی وضعیت کوپن
    now = timezone.now()
    is_expired = coupon.endDate < now
    is_upcoming = coupon.startDate > now
    is_current = coupon.startDate <= now <= coupon.endDate

    return render(request, 'panelAdmin/discount/coupon/detail.html', {
        'coupon': coupon,
        'is_expired': is_expired,
        'is_upcoming': is_upcoming,
        'is_current': is_current,
        'now': now
    })


# ========================
# DISCOUNT BASKET CRUD
# ========================

def discount_basket_list(request):
    """لیست سبدهای تخفیف"""
    discount_baskets = DiscountBasket.objects.all()

    # فیلتر بر اساس وضعیت
    status = request.GET.get('status')
    if status == 'active':
        discount_baskets = discount_baskets.filter(isActive=True)
    elif status == 'inactive':
        discount_baskets = discount_baskets.filter(isActive=False)

    # فیلتر بر اساس تخفیف شگفت‌انگیز
    is_amazing = request.GET.get('is_amazing')
    if is_amazing == 'yes':
        discount_baskets = discount_baskets.filter(isamzing=True)
    elif is_amazing == 'no':
        discount_baskets = discount_baskets.filter(isamzing=False)

    # فیلتر بر اساس جستجو
    search_query = request.GET.get('search', '')
    if search_query:
        discount_baskets = discount_baskets.filter(
            Q(discountTitle__icontains=search_query)
        )

    # فیلتر بر اساس تاریخ
    date_filter = request.GET.get('date_filter')
    if date_filter == 'expired':
        discount_baskets = discount_baskets.filter(endDate__lt=timezone.now())
    elif date_filter == 'upcoming':
        discount_baskets = discount_baskets.filter(startDate__gt=timezone.now())
    elif date_filter == 'current':
        now = timezone.now()
        discount_baskets = discount_baskets.filter(startDate__lte=now, endDate__gte=now)

    # محاسبه تعداد محصولات هر سبد
    for basket in discount_baskets:
        basket.product_count = DiscountDetail.objects.filter(discountBasket=basket).count()

    paginator = Paginator(discount_baskets, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'panelAdmin/discount/basket/list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'selected_status': status,
        'selected_is_amazing': is_amazing,
        'selected_date_filter': date_filter
    })

def discount_basket_create(request):
    """ایجاد سبد تخفیف جدید"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # تبدیل تاریخ‌ها به datetime
                start_date_str = request.POST.get('startDate')
                end_date_str = request.POST.get('endDate')

                start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
                end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')

                # ایجاد سبد تخفیف
                discount_basket = DiscountBasket.objects.create(
                    discountTitle=request.POST.get('discountTitle'),
                    startDate=start_date,
                    endDate=end_date,
                    discount=request.POST.get('discount'),
                    isActive=request.POST.get('isActive') == 'on',
                    isamzing=request.POST.get('isamzing') == 'on'
                )

                # اضافه کردن محصولات به سبد تخفیف
                product_ids = request.POST.getlist('products')
                for product_id in product_ids:
                    product = Product.objects.get(id=product_id)
                    DiscountDetail.objects.create(
                        discountBasket=discount_basket,
                        product=product
                    )

                messages.success(request, f'سبد تخفیف {discount_basket.discountTitle} با موفقیت ایجاد شد')
                return redirect('admin_discount_basket_detail', basket_id=discount_basket.id)

        except Exception as e:
            messages.error(request, f'خطا در ایجاد سبد تخفیف: {str(e)}')

    # دریافت محصولات فعال
    products = Product.objects.filter(isActive=True)

    return render(request, 'panelAdmin/discount/basket/create.html', {
        'products': products
    })

def discount_basket_detail(request, basket_id):
    """مشاهده جزئیات سبد تخفیف"""
    discount_basket = get_object_or_404(
        DiscountBasket.objects.prefetch_related('discountOfBasket__product'),
        id=basket_id
    )

    # دریافت محصولات مرتبط
    discount_details = discount_basket.discountOfBasket.all()

    # بررسی وضعیت سبد تخفیف
    now = timezone.now()
    is_expired = discount_basket.endDate < now
    is_upcoming = discount_basket.startDate > now
    is_current = discount_basket.startDate <= now <= discount_basket.endDate

    return render(request, 'panelAdmin/discount/basket/detail.html', {
        'discount_basket': discount_basket,
        'discount_details': discount_details,
        'is_expired': is_expired,
        'is_upcoming': is_upcoming,
        'is_current': is_current,
        'now': now
    })

def discount_basket_update(request, basket_id):
    """ویرایش سبد تخفیف"""
    discount_basket = get_object_or_404(
        DiscountBasket.objects.prefetch_related('discountOfBasket__product'),
        id=basket_id
    )

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # آپدیت اطلاعات سبد تخفیف
                discount_basket.discountTitle = request.POST.get('discountTitle', discount_basket.discountTitle)

                # تبدیل تاریخ‌ها
                start_date_str = request.POST.get('startDate')
                end_date_str = request.POST.get('endDate')

                if start_date_str:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
                    discount_basket.startDate = start_date

                if end_date_str:
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')
                    discount_basket.endDate = end_date

                discount_basket.discount = request.POST.get('discount', discount_basket.discount)
                discount_basket.isActive = request.POST.get('isActive') == 'on'
                discount_basket.isamzing = request.POST.get('isamzing') == 'on'
                discount_basket.save()

                # حذف محصولات قبلی و اضافه کردن جدید
                DiscountDetail.objects.filter(discountBasket=discount_basket).delete()

                product_ids = request.POST.getlist('products')
                for product_id in product_ids:
                    product = Product.objects.get(id=product_id)
                    DiscountDetail.objects.create(
                        discountBasket=discount_basket,
                        product=product
                    )

                messages.success(request, 'سبد تخفیف با موفقیت ویرایش شد')
                return redirect('admin_discount_basket_detail', basket_id=discount_basket.id)

        except Exception as e:
            messages.error(request, f'خطا در ویرایش سبد تخفیف: {str(e)}')

    # دریافت محصولات فعال و محصولات انتخاب شده
    products = Product.objects.filter(isActive=True)
    selected_products = discount_basket.discountOfBasket.values_list('product_id', flat=True)

    # فرمت تاریخ برای ورودی datetime-local
    start_date_formatted = discount_basket.startDate.strftime('%Y-%m-%dT%H:%M') if discount_basket.startDate else ''
    end_date_formatted = discount_basket.endDate.strftime('%Y-%m-%dT%H:%M') if discount_basket.endDate else ''

    return render(request, 'panelAdmin/discount/basket/update.html', {
        'discount_basket': discount_basket,
        'products': products,
        'selected_products': list(selected_products),
        'start_date_formatted': start_date_formatted,
        'end_date_formatted': end_date_formatted
    })

def discount_basket_delete(request, basket_id):
    """حذف سبد تخفیف"""
    discount_basket = get_object_or_404(DiscountBasket, id=basket_id)

    if request.method == 'POST':
        try:
            basket_title = discount_basket.discountTitle
            discount_basket.delete()
            messages.success(request, f'سبد تخفیف {basket_title} با موفقیت حذف شد')
            return redirect('admin_discount_basket_list')
        except Exception as e:
            messages.error(request, f'خطا در حذف سبد تخفیف: {str(e)}')

    return render(request, 'panelAdmin/discount/basket/delete_confirm.html', {
        'discount_basket': discount_basket
    })

def discount_basket_toggle(request, basket_id):
    """تغییر وضعیت فعال/غیرفعال سبد تخفیف"""
    discount_basket = get_object_or_404(DiscountBasket, id=basket_id)

    if request.method == 'POST':
        try:
            discount_basket.isActive = not discount_basket.isActive
            discount_basket.save()

            status = 'فعال' if discount_basket.isActive else 'غیرفعال'
            messages.success(request, f'سبد تخفیف با موفقیت {status} شد')
        except Exception as e:
            messages.error(request, f'خطا در تغییر وضعیت سبد تخفیف: {str(e)}')

    return redirect('admin_discount_basket_detail', basket_id=discount_basket.id)

def remove_product_from_basket(request, detail_id):
    """حذف محصول از سبد تخفیف"""
    discount_detail = get_object_or_404(DiscountDetail, id=detail_id)
    basket_id = discount_detail.discountBasket.id

    if request.method == 'POST':
        try:
            product_name = discount_detail.product.title
            discount_detail.delete()
            messages.success(request, f'محصول {product_name} از سبد تخفیف حذف شد')
        except Exception as e:
            messages.error(request, f'خطا در حذف محصول از سبد تخفیف: {str(e)}')

    return redirect('admin_discount_basket_detail', basket_id=basket_id)


# ========================
# AJAX VIEWS
# ========================

def search_products_ajax(request):
    """جستجوی محصولات برای سبد تخفیف"""
    search_term = request.GET.get('q', '')

    if search_term:
        products = Product.objects.filter(
            Q(title__icontains=search_term) |
            Q(slug__icontains=search_term)
        ).filter(isActive=True)[:10]
    else:
        products = Product.objects.filter(isActive=True)[:10]

    results = []
    for product in products:
        results.append({
            'id': str(product.id),
            'title': product.title,
            'image': product.mainImage.url if product.mainImage else '',
            'price': product.saleTypes.first().price if product.saleTypes.exists() else 0
        })

    return JsonResponse({'results': results})

def get_product_details(request):
    """دریافت جزئیات محصول"""
    product_id = request.GET.get('product_id')

    if product_id:
        try:
            product = Product.objects.get(id=product_id)

            # دریافت قیمت محصول
            sale_type = product.saleTypes.first()
            price = sale_type.price if sale_type else 0

            data = {
                'id': str(product.id),
                'title': product.title,
                'image': product.mainImage.url if product.mainImage else '',
                'price': price,
                'category': ', '.join([cat.title for cat in product.category.all()]),
                'brand': product.brand.title if product.brand else 'بدون برند'
            }
            return JsonResponse(data)
        except Product.DoesNotExist:
            return JsonResponse({'error': 'محصول یافت نشد'}, status=404)

    return JsonResponse({'error': 'آیدی محصول ارسال نشده'}, status=400)


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
    upcoming_coupons = Copon.objects.filter(startDate__gt=now).count()
    current_coupons = Copon.objects.filter(startDate__lte=now, endDate__gte=now).count()

    # آمار سبدهای تخفیف
    total_baskets = DiscountBasket.objects.count()
    active_baskets = DiscountBasket.objects.filter(isActive=True).count()
    amazing_baskets = DiscountBasket.objects.filter(isamzing=True).count()
    expired_baskets = DiscountBasket.objects.filter(endDate__lt=now).count()
    current_baskets = DiscountBasket.objects.filter(startDate__lte=now, endDate__gte=now).count()

    # محصولات دارای تخفیف
    products_with_discount = Product.objects.filter(
        id__in=DiscountDetail.objects.values_list('product_id', flat=True).distinct()
    ).count()

    # سبدهای تخفیف فعال امروز
    today_baskets = DiscountBasket.objects.filter(
        isActive=True,
        startDate__lte=now,
        endDate__gte=now
    )

    context = {
        # آمار کوپن‌ها
        'total_coupons': total_coupons,
        'active_coupons': active_coupons,
        'expired_coupons': expired_coupons,
        'upcoming_coupons': upcoming_coupons,
        'current_coupons': current_coupons,

        # آمار سبدهای تخفیف
        'total_baskets': total_baskets,
        'active_baskets': active_baskets,
        'amazing_baskets': amazing_baskets,
        'expired_baskets': expired_baskets,
        'current_baskets': current_baskets,

        # سایر آمار
        'products_with_discount': products_with_discount,
        'today_baskets': today_baskets,
        'now': now
    }

    return render(request, 'panelAdmin/discount/report.html', context)