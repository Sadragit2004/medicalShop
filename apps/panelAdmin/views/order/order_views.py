# views/order_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count, F
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from apps.order.models import (
    State, City, UserAddress,
    Order, OrderDetail, CustomUser, Product, Brand
)
import json
import utils

# ========================
# STATE & CITY CRUD
# ========================

def state_list(request):
    """لیست استان‌ها"""
    states = State.objects.annotate(
        city_count=Count('cities', distinct=True),
        user_count=Count('cities__useraddress__user', distinct=True)
    ).all()

    search_query = request.GET.get('search', '')
    if search_query:
        states = states.filter(
            Q(name__icontains=search_query) |
            Q(center__icontains=search_query)
        )

    return render(request, 'panelAdmin/order/state/list.html', {
        'states': states,
        'search_query': search_query
    })

def state_create(request):
    """ایجاد استان جدید"""
    if request.method == 'POST':
        try:
            state = State.objects.create(
                name=request.POST.get('name'),
                center=request.POST.get('center'),
                lat=request.POST.get('lat') if request.POST.get('lat') else None,
                lng=request.POST.get('lng') if request.POST.get('lng') else None
            )
            messages.success(request, f'استان {state.name} با موفقیت ایجاد شد')
            return redirect('admin_state_list')
        except Exception as e:
            messages.error(request, f'خطا در ایجاد استان: {str(e)}')

    return render(request, 'panelAdmin/order/state/create.html')

def state_update(request, state_id):
    """ویرایش استان"""
    state = get_object_or_404(State, id=state_id)

    if request.method == 'POST':
        try:
            state.name = request.POST.get('name', state.name)
            state.center = request.POST.get('center', state.center)
            state.lat = request.POST.get('lat') if request.POST.get('lat') else None
            state.lng = request.POST.get('lng') if request.POST.get('lng') else None
            state.save()

            messages.success(request, 'استان با موفقیت ویرایش شد')
            return redirect('admin_state_list')
        except Exception as e:
            messages.error(request, f'خطا در ویرایش استان: {str(e)}')

    return render(request, 'panelAdmin/order/state/update.html', {'state': state})

def state_delete(request, state_id):
    """حذف استان"""
    state = get_object_or_404(State, id=state_id)

    if request.method == 'POST':
        try:
            state_name = state.name
            state.delete()
            messages.success(request, f'استان {state_name} با موفقیت حذف شد')
            return redirect('admin_state_list')
        except Exception as e:
            messages.error(request, f'خطا در حذف استان: {str(e)}')

    return render(request, 'panelAdmin/order/state/delete_confirm.html', {'state': state})

def city_list(request, state_id=None):
    """لیست شهرها"""
    state = None
    if state_id:
        state = get_object_or_404(State, id=state_id)
        cities = City.objects.filter(state=state)
    else:
        cities = City.objects.all()

    # فیلتر بر اساس جستجو
    search_query = request.GET.get('search', '')
    if search_query:
        cities = cities.filter(
            Q(name__icontains=search_query) |
            Q(state__name__icontains=search_query)
        )

    # آمار کاربران
    cities = cities.annotate(
        address_count=Count('useraddress', distinct=True)
    )

    return render(request, 'panelAdmin/order/city/list.html', {
        'cities': cities,
        'state': state,
        'search_query': search_query
    })

def city_create(request, state_id=None):
    """ایجاد شهر جدید"""
    states = State.objects.all()

    if request.method == 'POST':
        try:
            state = get_object_or_404(State, id=request.POST.get('state'))
            city = City.objects.create(
                state=state,
                name=request.POST.get('name'),
                lat=request.POST.get('lat') if request.POST.get('lat') else None,
                lng=request.POST.get('lng') if request.POST.get('lng') else None
            )
            messages.success(request, f'شهر {city.name} با موفقیت ایجاد شد')

            if state_id:
                return redirect('admin_city_list', state_id=state_id)
            return redirect('admin_city_list')
        except Exception as e:
            messages.error(request, f'خطا در ایجاد شهر: {str(e)}')

    return render(request, 'panelAdmin/order/city/create.html', {
        'states': states,
        'selected_state_id': state_id
    })

def city_update(request, city_id):
    """ویرایش شهر"""
    city = get_object_or_404(City, id=city_id)
    states = State.objects.all()

    if request.method == 'POST':
        try:
            city.state = get_object_or_404(State, id=request.POST.get('state'))
            city.name = request.POST.get('name', city.name)
            city.lat = request.POST.get('lat') if request.POST.get('lat') else None
            city.lng = request.POST.get('lng') if request.POST.get('lng') else None
            city.save()

            messages.success(request, 'شهر با موفقیت ویرایش شد')
            return redirect('admin_city_list')
        except Exception as e:
            messages.error(request, f'خطا در ویرایش شهر: {str(e)}')

    return render(request, 'panelAdmin/order/city/update.html', {
        'city': city,
        'states': states
    })

def city_delete(request, city_id):
    """حذف شهر"""
    city = get_object_or_404(City, id=city_id)

    if request.method == 'POST':
        try:
            city_name = city.name
            state_id = city.state.id
            city.delete()
            messages.success(request, f'شهر {city_name} با موفقیت حذف شد')
            return redirect('admin_city_list', state_id=state_id)
        except Exception as e:
            messages.error(request, f'خطا در حذف شهر: {str(e)}')

    return render(request, 'panelAdmin/order/city/delete_confirm.html', {'city': city})


# ========================
# USER ADDRESS MANAGEMENT
# ========================

def user_address_list(request):
    """لیست آدرس‌های کاربران"""
    addresses = UserAddress.objects.select_related('user', 'state', 'city').all()

    # فیلتر بر اساس کاربر
    user_id = request.GET.get('user')
    if user_id:
        addresses = addresses.filter(user_id=user_id)

    # فیلتر بر اساس استان
    state_id = request.GET.get('state')
    if state_id:
        addresses = addresses.filter(state_id=state_id)

    # فیلتر بر اساس شهر
    city_id = request.GET.get('city')
    if city_id:
        addresses = addresses.filter(city_id=city_id)

    # فیلتر بر اساس جستجو
    search_query = request.GET.get('search', '')
    if search_query:
        addresses = addresses.filter(
            Q(user__mobileNumber__icontains=search_query) |
            Q(user__name__icontains=search_query) |
            Q(user__family__icontains=search_query) |
            Q(addressDetail__icontains=search_query) |
            Q(postalCode__icontains=search_query)
        )

    paginator = Paginator(addresses, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    users = CustomUser.objects.all()
    states = State.objects.all()
    cities = City.objects.all()

    return render(request, 'panelAdmin/order/address/list.html', {
        'page_obj': page_obj,
        'users': users,
        'states': states,
        'cities': cities,
        'selected_user': user_id,
        'selected_state': state_id,
        'selected_city': city_id,
        'search_query': search_query
    })

def user_address_detail(request, address_id):
    """مشاهده جزئیات آدرس"""
    address = get_object_or_404(
        UserAddress.objects.select_related('user', 'state', 'city'),
        id=address_id
    )

    return render(request, 'panelAdmin/order/address/detail.html', {'address': address})

def user_address_delete(request, address_id):
    """حذف آدرس کاربر"""
    address = get_object_or_404(UserAddress, id=address_id)

    if request.method == 'POST':
        try:
            user_info = f"{address.user.mobileNumber} - {address.city.name}"
            address.delete()
            messages.success(request, f'آدرس کاربر {user_info} با موفقیت حذف شد')
            return redirect('admin_user_address_list')
        except Exception as e:
            messages.error(request, f'خطا در حذف آدرس: {str(e)}')

    return render(request, 'panelAdmin/order/address/delete_confirm.html', {'address': address})


# ========================
# ORDER CRUD
# ========================

def order_list(request):
    """لیست سفارشات"""
    orders = Order.objects.select_related('customer', 'address__city__state').all()

    # فیلتر بر اساس وضعیت
    status = request.GET.get('status')
    if status:
        orders = orders.filter(status=status)

    # فیلتر بر اساس نهایی بودن
    is_finally = request.GET.get('is_finally')
    if is_finally == 'yes':
        orders = orders.filter(isFinally=True)
    elif is_finally == 'no':
        orders = orders.filter(isFinally=False)

    # فیلتر بر اساس کاربر
    user_id = request.GET.get('user')
    if user_id:
        orders = orders.filter(customer_id=user_id)

    # فیلتر بر اساس تاریخ
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d')
            orders = orders.filter(registerDate__date__gte=date_from)
        except:
            pass
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d')
            orders = orders.filter(registerDate__date__lte=date_to)
        except:
            pass

    # فیلتر بر اساس جستجو
    search_query = request.GET.get('search', '')
    if search_query:
        orders = orders.filter(
            Q(orderCode__icontains=search_query) |
            Q(customer__mobileNumber__icontains=search_query) |
            Q(customer__name__icontains=search_query) |
            Q(customer__family__icontains=search_query) |
            Q(address__addressDetail__icontains=search_query)
        )

    # محاسبه قیمت‌ها
    for order in orders:
        order.total_price = order.getTotalPrice()
        order.final_price = order.getFinalPrice()
        order.item_count = order.details.aggregate(Sum('qty'))['qty__sum'] or 0

    # مرتب‌سازی
    sort_by = request.GET.get('sort_by', '-registerDate')
    if sort_by in ['registerDate', '-registerDate', 'total_price', '-total_price']:
        if sort_by == 'total_price':
            orders = sorted(orders, key=lambda x: x.total_price)
        elif sort_by == '-total_price':
            orders = sorted(orders, key=lambda x: x.total_price, reverse=True)
        else:
            orders = orders.order_by(sort_by)

    paginator = Paginator(orders, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    users = CustomUser.objects.all()

    return render(request, 'panelAdmin/order/order/list.html', {
        'page_obj': page_obj,
        'users': users,
        'status_choices': Order.STATUS_CHOICES,
        'selected_status': status,
        'selected_user': user_id,
        'selected_is_finally': is_finally,
        'search_query': search_query,
        'date_from': date_from.strftime('%Y-%m-%d') if isinstance(date_from, datetime) else date_from,
        'date_to': date_to.strftime('%Y-%m-%d') if isinstance(date_to, datetime) else date_to,
        'sort_by': sort_by
    })

def order_detail(request, order_id):
    """مشاهده جزئیات سفارش"""
    order = get_object_or_404(
        Order.objects.select_related('customer', 'address__city__state')
        .prefetch_related('details__product', 'details__brand'),
        id=order_id
    )

    order_details = order.details.all()

    # محاسبه قیمت‌ها
    total_price = order.getTotalPrice()
    final_price = order.getFinalPrice()
    discount_amount = total_price - final_price if order.discount else 0

    return render(request, 'panelAdmin/order/order/detail.html', {
        'order': order,
        'order_details': order_details,
        'total_price': total_price,
        'final_price': final_price,
        'discount_amount': discount_amount,
        'status_choices': Order.STATUS_CHOICES
    })

def order_create(request):
    """ایجاد سفارش جدید"""
    users = CustomUser.objects.all()
    products = Product.objects.filter(isActive=True)
    addresses = UserAddress.objects.all()

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # ایجاد سفارش
                order = Order.objects.create(
                    customer_id=request.POST.get('customer'),
                    address_id=request.POST.get('address') if request.POST.get('address') else None,
                    status=request.POST.get('status', 'pending'),
                    description=request.POST.get('description'),
                    discount=int(request.POST.get('discount', 0)),
                    isFinally=request.POST.get('isFinally') == 'on'
                )

                # اضافه کردن محصولات به سفارش
                product_ids = request.POST.getlist('products[]')
                quantities = request.POST.getlist('quantities[]')
                prices = request.POST.getlist('prices[]')
                selected_options = request.POST.getlist('selected_options[]')

                for i, product_id in enumerate(product_ids):
                    if product_id and quantities[i] and prices[i]:
                        product = Product.objects.get(id=product_id)

                        OrderDetail.objects.create(
                            order=order,
                            product=product,
                            brand=product.brand,
                            qty=int(quantities[i]),
                            price=int(prices[i]),
                            selectedOptions=selected_options[i] if i < len(selected_options) else None
                        )

                messages.success(request, f'سفارش {order.orderCode} با موفقیت ایجاد شد')
                return redirect('admin_order_detail', order_id=order.id)

        except Exception as e:
            messages.error(request, f'خطا در ایجاد سفارش: {str(e)}')

    return render(request, 'panelAdmin/order/order/create.html', {
        'users': users,
        'products': products,
        'addresses': addresses
    })

def order_update(request, order_id):
    """ویرایش سفارش"""
    order = get_object_or_404(
        Order.objects.select_related('customer', 'address')
        .prefetch_related('details__product'),
        id=order_id
    )

    users = CustomUser.objects.all()
    addresses = UserAddress.objects.all()

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # آپدیت اطلاعات سفارش
                order.customer_id = request.POST.get('customer', order.customer.id)
                order.address_id = request.POST.get('address') if request.POST.get('address') else None
                order.status = request.POST.get('status', order.status)
                order.description = request.POST.get('description', order.description)
                order.discount = int(request.POST.get('discount', order.discount))
                order.isFinally = request.POST.get('isFinally') == 'on'
                order.save()

                # مدیریت جزئیات سفارش
                detail_ids = request.POST.getlist('detail_ids[]')
                product_ids = request.POST.getlist('products[]')
                quantities = request.POST.getlist('quantities[]')
                prices = request.POST.getlist('prices[]')
                selected_options = request.POST.getlist('selected_options[]')

                # حذف آیتم‌های حذف شده
                existing_detail_ids = [int(id) for id in detail_ids if id]
                order.details.exclude(id__in=existing_detail_ids).delete()

                # آپدیت یا ایجاد آیتم‌های جدید
                for i, detail_id in enumerate(detail_ids):
                    if product_ids[i] and quantities[i] and prices[i]:
                        product = Product.objects.get(id=product_ids[i])

                        if detail_id:  # آپدیت آیتم موجود
                            order_detail = OrderDetail.objects.get(id=detail_id)
                            order_detail.product = product
                            order_detail.brand = product.brand
                            order_detail.qty = int(quantities[i])
                            order_detail.price = int(prices[i])
                            order_detail.selectedOptions = selected_options[i] if i < len(selected_options) else None
                            order_detail.save()
                        else:  # ایجاد آیتم جدید
                            OrderDetail.objects.create(
                                order=order,
                                product=product,
                                brand=product.brand,
                                qty=int(quantities[i]),
                                price=int(prices[i]),
                                selectedOptions=selected_options[i] if i < len(selected_options) else None
                            )

                messages.success(request, 'سفارش با موفقیت ویرایش شد')
                return redirect('admin_order_detail', order_id=order.id)

        except Exception as e:
            messages.error(request, f'خطا در ویرایش سفارش: {str(e)}')

    return render(request, 'panelAdmin/order/order/update.html', {
        'order': order,
        'users': users,
        'addresses': addresses,
        'order_details': order.details.all(),
        'status_choices': Order.STATUS_CHOICES
    })

def order_delete(request, order_id):
    """حذف سفارش"""
    order = get_object_or_404(Order, id=order_id)

    if request.method == 'POST':
        try:
            order_code = str(order.orderCode)
            order.delete()
            messages.success(request, f'سفارش {order_code} با موفقیت حذف شد')
            return redirect('admin_order_list')
        except Exception as e:
            messages.error(request, f'خطا در حذف سفارش: {str(e)}')

    return render(request, 'panelAdmin/order/order/delete_confirm.html', {'order': order})

def update_order_status(request, order_id):
    """تغییر وضعیت سفارش"""
    order = get_object_or_404(Order, id=order_id)

    if request.method == 'POST':
        try:
            new_status = request.POST.get('status')
            if new_status in dict(Order.STATUS_CHOICES).keys():
                order.status = new_status
                order.save()

                status_display = dict(Order.STATUS_CHOICES).get(new_status)
                messages.success(request, f'وضعیت سفارش به {status_display} تغییر یافت')
            else:
                messages.error(request, 'وضعیت انتخابی نامعتبر است')

        except Exception as e:
            messages.error(request, f'خطا در تغییر وضعیت سفارش: {str(e)}')

    return redirect('admin_order_detail', order_id=order.id)

def toggle_order_final(request, order_id):
    """تغییر وضعیت نهایی بودن سفارش"""
    order = get_object_or_404(Order, id=order_id)

    if request.method == 'POST':
        try:
            order.isFinally = not order.isFinally
            order.save()

            status = 'نهایی' if order.isFinally else 'غیرنهایی'
            messages.success(request, f'سفارش با موفقیت {status} شد')
        except Exception as e:
            messages.error(request, f'خطا در تغییر وضعیت سفارش: {str(e)}')

    return redirect('admin_order_detail', order_id=order.id)


# ========================
# ORDER DETAIL MANAGEMENT
# ========================

def add_order_item(request, order_id):
    """اضافه کردن آیتم به سفارش"""
    order = get_object_or_404(Order, id=order_id)
    products = Product.objects.filter(isActive=True)

    if request.method == 'POST':
        try:
            product = get_object_or_404(Product, id=request.POST.get('product'))

            OrderDetail.objects.create(
                order=order,
                product=product,
                brand=product.brand,
                qty=int(request.POST.get('qty', 1)),
                price=int(request.POST.get('price', 0)),
                selectedOptions=request.POST.get('selectedOptions')
            )

            messages.success(request, 'محصول با موفقیت به سفارش اضافه شد')
            return redirect('admin_order_detail', order_id=order.id)

        except Exception as e:
            messages.error(request, f'خطا در اضافه کردن محصول: {str(e)}')

    return render(request, 'panelAdmin/order/order/add_item.html', {
        'order': order,
        'products': products
    })

def update_order_item(request, item_id):
    """ویرایش آیتم سفارش"""
    order_item = get_object_or_404(OrderDetail, id=item_id)

    if request.method == 'POST':
        try:
            order_item.qty = int(request.POST.get('qty', order_item.qty))
            order_item.price = int(request.POST.get('price', order_item.price))
            order_item.selectedOptions = request.POST.get('selectedOptions', order_item.selectedOptions)
            order_item.save()

            messages.success(request, 'آیتم سفارش با موفقیت ویرایش شد')
            return redirect('admin_order_detail', order_id=order_item.order.id)

        except Exception as e:
            messages.error(request, f'خطا در ویرایش آیتم سفارش: {str(e)}')

    products = Product.objects.filter(isActive=True)

    return render(request, 'panelAdmin/order/order/update_item.html', {
        'order_item': order_item,
        'products': products
    })

def delete_order_item(request, item_id):
    """حذف آیتم از سفارش"""
    order_item = get_object_or_404(OrderDetail, id=item_id)
    order_id = order_item.order.id

    if request.method == 'POST':
        try:
            order_item.delete()
            messages.success(request, 'آیتم با موفقیت از سفارش حذف شد')
        except Exception as e:
            messages.error(request, f'خطا در حذف آیتم: {str(e)}')

    return redirect('admin_order_detail', order_id=order_id)


# ========================
# AJAX VIEWS
# ========================

def get_user_addresses(request):
    """دریافت آدرس‌های کاربر"""
    user_id = request.GET.get('user_id')
    if user_id:
        addresses = UserAddress.objects.filter(user_id=user_id).select_related('city__state')
        data = []
        for address in addresses:
            data.append({
                'id': address.id,
                'full_address': address.fullAddress(),
                'postal_code': address.postalCode or '',
                'state': address.state.name,
                'city': address.city.name
            })
        return JsonResponse({'addresses': data})
    return JsonResponse({'addresses': []})

def get_product_price(request):
    """دریافت قیمت محصول"""
    product_id = request.GET.get('product_id')
    if product_id:
        try:
            product = Product.objects.get(id=product_id)
            sale_type = product.saleTypes.first()
            price = sale_type.price if sale_type else 0

            return JsonResponse({
                'price': price,
                'title': product.title,
                'brand': product.brand.title if product.brand else 'بدون برند'
            })
        except Product.DoesNotExist:
            return JsonResponse({'error': 'محصول یافت نشد'}, status=404)
    return JsonResponse({'error': 'آیدی محصول ارسال نشده'}, status=400)


# ========================
# REPORT VIEWS
# ========================

def order_report(request):
    """گزارش سفارشات"""
    # تاریخ‌های پیش‌فرض (30 روز اخیر)
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)

    # دریافت تاریخ از پارامترها
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if date_from:
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d')
        except:
            pass

    if date_to:
        try:
            end_date = datetime.strptime(date_to, '%Y-%m-%d')
        except:
            pass

    # فیلتر سفارشات بر اساس تاریخ
    orders = Order.objects.filter(
        registerDate__date__range=[start_date, end_date]
    )

    # آمار کلی
    total_orders = orders.count()
    total_revenue = sum(order.getFinalPrice() for order in orders)
    total_items = OrderDetail.objects.filter(
        order__registerDate__date__range=[start_date, end_date]
    ).aggregate(Sum('qty'))['qty__sum'] or 0

    # آمار بر اساس وضعیت
    status_stats = {}
    for status_code, status_name in Order.STATUS_CHOICES:
        count = orders.filter(status=status_code).count()
        if count > 0:
            status_stats[status_name] = {
                'count': count,
                'percentage': round((count / total_orders * 100), 2) if total_orders > 0 else 0
            }

    # آمار بر اساس روز
    daily_stats = []
    current_date = start_date
    while current_date <= end_date:
        day_orders = orders.filter(registerDate__date=current_date)
        day_count = day_orders.count()
        day_revenue = sum(order.getFinalPrice() for order in day_orders)

        daily_stats.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'date_jalali': utils.to_jalali(current_date),
            'order_count': day_count,
            'revenue': day_revenue
        })

        current_date += timedelta(days=1)

    # محصولات پرفروش
    top_products = OrderDetail.objects.filter(
        order__registerDate__date__range=[start_date, end_date]
    ).values('product__title').annotate(
        total_qty=Sum('qty'),
        total_revenue=Sum(F('price') * F('qty'))
    ).order_by('-total_qty')[:10]

    # کاربران فعال
    top_customers = orders.values('customer__mobileNumber', 'customer__name', 'customer__family').annotate(
        order_count=Count('id'),
        total_spent=Sum('price')
    ).order_by('-order_count')[:10]

    context = {
        # تاریخ‌ها
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'start_date_jalali': utils.to_jalali(start_date),
        'end_date_jalali': utils.to_jalali(end_date),

        # آمار کلی
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_items': total_items,

        # آمار وضعیت
        'status_stats': status_stats,

        # آمار روزانه
        'daily_stats': daily_stats,

        # محصولات پرفروش
        'top_products': top_products,

        # کاربران فعال
        'top_customers': top_customers,

        # تنظیمات گزارش
        'date_range_options': [
            ('7days', '۷ روز اخیر'),
            ('30days', '۳۰ روز اخیر'),
            ('90days', '۹۰ روز اخیر'),
            ('custom', 'تاریخ دلخواه'),
        ]
    }

    return render(request, 'panelAdmin/order/report.html', context)