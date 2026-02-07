# =======================
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils import timezone

from apps.order.models import Order, UserAddress, State


@login_required
def loadDashboard(request):
    orders = (
        Order.objects.filter(customer=request.user)
        .order_by("-registerDate")
        .prefetch_related("details", "address__state", "address__city")
    )

    context = {
        "order_count": orders.count(),
        "recent_orders": orders[:20],
        "addresses": UserAddress.objects.filter(user=request.user).select_related("state", "city"),
        "states": State.objects.all().order_by("name"),
    }

    return render(request, "dashboard_app/dashboard.html", context)

from django.core.paginator import Paginator

@login_required
def orders_page(request):
    qs = (
        Order.objects.filter(customer=request.user)
        .order_by("-registerDate")
        .prefetch_related("details", "address__state", "address__city")
    )

    # Filters
    status = request.GET.get("status")
    if status:
        qs = qs.filter(status=status)

    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    if date_from:
        qs = qs.filter(registerDate__date__gte=date_from)
    if date_to:
        qs = qs.filter(registerDate__date__lte=date_to)

    price_min = request.GET.get("price_min")
    price_max = request.GET.get("price_max")
    if price_min:
        qs = qs.filter(total_price__gte=price_min)  # تغییر به total_price
    if price_max:
        qs = qs.filter(total_price__lte=price_max)  # تغییر به total_price

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(qs, 10)
    orders_page = paginator.get_page(page)

    context = {
        "orders": orders_page,
        "states": State.objects.all().order_by("name"),
        "status_filter": status or "",
        "date_from": date_from or "",
        "date_to": date_to or "",
        "price_min": price_min or "",
        "price_max": price_max or "",
        "has_next": orders_page.has_next(),
        "next_page_number": orders_page.next_page_number() if orders_page.has_next() else None,
    }
    return render(request, "dashboard_app/orders.html", context)


# =======================
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from apps.product.models import Product
from apps.dashboard.models import Favorite

@login_required
@require_POST
def toggle_favorite(request, product_id):
    """
    اضافه یا حذف محصول از علاقه‌مندی‌ها
    """
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'محصول یافت نشد'
        })

    # بررسی آیا محصول در علاقه‌مندی‌های کاربر هست یا نه
    favorite_exists = Favorite.objects.filter(
        user=request.user,
        product=product
    ).exists()

    if favorite_exists:
        # اگر وجود دارد، حذف کن
        Favorite.objects.filter(user=request.user, product=product).delete()
        is_favorite = False
        action = 'removed'
    else:
        # اگر وجود ندارد، اضافه کن
        Favorite.objects.create(user=request.user, product=product)
        is_favorite = True
        action = 'added'

    # تعداد علاقه‌مندی‌های این محصول
    total_favorites = Favorite.objects.filter(product=product).count()

    return JsonResponse({
        'success': True,
        'is_favorite': is_favorite,
        'action': action,
        'total_favorites': total_favorites
    })

@login_required
def check_favorite(request, product_id):
    """
    بررسی اینکه آیا محصول در علاقه‌مندی‌های کاربر هست
    """
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'محصول یافت نشد'
        })

    is_favorite = Favorite.objects.filter(
        user=request.user,
        product=product
    ).exists()

    return JsonResponse({
        'success': True,
        'is_favorite': is_favorite
    })


from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from apps.product.models import ProductSaleType
from .models import Favorite

@login_required
def favorite_list(request):
    # دریافت علاقه‌مندی‌های کاربر با اطلاعات کامل محصول
    favorites = Favorite.objects.filter(user=request.user).select_related('product')

    # برای هر محصول، اولین نوع فروش فعال را پیدا می‌کنیم
    for favorite in favorites:
        sale_type = ProductSaleType.objects.filter(
            product=favorite.product,
            isActive=True
        ).first()

        # اضافه کردن قیمت به context محصول
        if sale_type:
            favorite.product.current_price = sale_type.price
            favorite.product.discount_price = sale_type.finalPrice if sale_type.finalPrice != sale_type.price else None
        else:
            favorite.product.current_price = 0
            favorite.product.discount_price = None

        # بررسی تصاویر محصول
        favorite.product.primary_image = favorite.product.mainImage
        galleries = favorite.product.galleries.filter(isActive=True)
        favorite.product.secondary_image = galleries.first().image if galleries.exists() else favorite.product.mainImage

    return render(request, 'dashboard_app/favorites/favorite_list.html', {'favorites': favorites})

from django.views.decorators.csrf import csrf_exempt


@login_required
@csrf_exempt
def remove_favorite(request, favorite_id):
    # پیدا کردن و حذف علاقه‌مندی
    favorite = Favorite.objects.get(id=favorite_id, user=request.user)
    product_name = favorite.product.title
    favorite.delete()

    return JsonResponse({
        'success': True,
        'message': f'محصول "{product_name}" از لیست علاقه‌مندی‌ها حذف شد'
    })

# =======================
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from apps.order.models import UserAddress, State, City
import json

@login_required
def address_list(request):
    """نمایش صفحه آدرس‌های کاربر"""
    addresses = UserAddress.objects.filter(user=request.user)
    states = State.objects.all().order_by('name')

    return render(request, 'dashboard_app/address/address_list.html', {
        'addresses': addresses,
        'states': states,
    })

@require_GET
@login_required
def get_cities(request):
    """دریافت شهرهای یک استان"""
    state_id = request.GET.get('state_id')
    if not state_id:
        return JsonResponse({'cities': []})

    cities = City.objects.filter(state_id=state_id).order_by('name')
    cities_data = [{'id': city.id, 'name': city.name} for city in cities]

    return JsonResponse({'cities': cities_data})

@require_POST
@login_required
@csrf_exempt
def create_user_address(request):
    """ایجاد آدرس جدید برای کاربر"""
    try:
        data = json.loads(request.body) if request.body else request.POST

        state_id = data.get('state')
        city_id = data.get('city')
        address_detail = data.get('address_detail', '').strip()
        postal_code = data.get('postal_code', '').strip()

        # Validation - فقط فیلدهای ضروری
        if not all([state_id, city_id, address_detail]):
            return JsonResponse({
                'success': False,
                'error': 'لطفاً تمام فیلدهای ضروری (استان، شهر، آدرس دقیق) را پر کنید'
            })

        # Verify state and city exist and are related
        try:
            state = State.objects.get(id=state_id)
            city = City.objects.get(id=city_id, state=state)
        except (State.DoesNotExist, City.DoesNotExist):
            return JsonResponse({
                'success': False,
                'error': 'استان یا شهر انتخاب شده نامعتبر است'
            })

        # Create address - بدون نام و نام گیرنده
        address = UserAddress.objects.create(
            user=request.user,
            state=state,
            city=city,
            addressDetail=address_detail,
            postalCode=postal_code if postal_code else None
        )

        return JsonResponse({
            'success': True,
            'address': {
                'id': address.id,
                'state': address.state.name,
                'state_id': address.state.id,
                'city': address.city.name,
                'city_id': address.city.id,
                'addressDetail': address.addressDetail,
                'postalCode': address.postalCode,
                'createdAt': address.createdAt.strftime('%Y/%m/%d')
            },
            'message': 'آدرس با موفقیت اضافه شد'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@require_GET
@login_required
def get_address_detail(request):
    """دریافت جزئیات یک آدرس"""
    address_id = request.GET.get('address_id')

    if not address_id:
        return JsonResponse({'success': False, 'error': 'آدرس مشخص نشده است'})

    try:
        address = UserAddress.objects.get(id=address_id, user=request.user)

        return JsonResponse({
            'success': True,
            'address': {
                'id': address.id,
                'state': address.state.id,
                'city': address.city.id,
                'address_detail': address.addressDetail,
                'postal_code': address.postalCode
            }
        })
    except UserAddress.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'آدرس پیدا نشد'})

@require_http_methods(["PUT"])
@login_required
@csrf_exempt
def update_user_address(request):
    """به‌روزرسانی آدرس کاربر"""
    try:
        data = json.loads(request.body)
        address_id = data.get('id')

        if not address_id:
            return JsonResponse({'success': False, 'error': 'آدرس مشخص نشده است'})

        address = UserAddress.objects.get(id=address_id, user=request.user)

        # به‌روزرسانی فقط فیلدهای اصلی
        if 'state' in data:
            address.state = State.objects.get(id=data['state'])
        if 'city' in data:
            address.city = City.objects.get(id=data['city'])
        if 'address_detail' in data:
            address.addressDetail = data['address_detail'].strip()
        if 'postal_code' in data:
            address.postalCode = data['postal_code'].strip()

        address.save()

        return JsonResponse({
            'success': True,
            'message': 'آدرس با موفقیت به‌روزرسانی شد',
            'address': {
                'id': address.id,
                'state': address.state.name,
                'city': address.city.name,
                'addressDetail': address.addressDetail,
                'postalCode': address.postalCode
            }
        })

    except UserAddress.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'آدرس پیدا نشد'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_POST
@login_required
@csrf_exempt
def delete_user_address(request):
    """حذف آدرس کاربر"""
    try:
        data = json.loads(request.body) if request.body else request.POST
        address_id = data.get('id')

        if not address_id:
            return JsonResponse({'success': False, 'error': 'آدرس مشخص نشده است'})

        # حذف فیزیکی
        address = UserAddress.objects.get(id=address_id, user=request.user)
        address.delete()

        return JsonResponse({
            'success': True,
            'message': 'آدرس با موفقیت حذف شد'
        })

    except UserAddress.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'آدرس پیدا نشد'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# =======================


# views.py در اپ dashboard
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import Notification
import json
from django.db import transaction

@login_required
def notifications_page(request):
    """صفحه نمایش اعلان‌ها"""
    # دریافت همه اعلان‌های کاربر
    notifications = Notification.objects.filter(user=request.user)

    # شمارش اعلان‌های خوانده نشده قبل از بروزرسانی
    unread_count = notifications.filter(is_read=False).count()

    # علامت‌گذاری همه اعلان‌ها به عنوان خوانده شده
    if unread_count > 0:
        # استفاده از تراکنش برای اطمینان از یکپارچگی داده‌ها
        with transaction.atomic():
            notifications.filter(is_read=False).update(is_read=True)

        # ریفرش کوئری‌ست برای دریافت داده‌های به‌روز شده
        notifications = Notification.objects.filter(user=request.user)

    return render(request, 'dashboard_app/notifications/notifications.html', {
        'notifications': notifications,
        'unread_count': 0  # پس از بروزرسانی، همه خوانده شده‌اند
    })

@require_GET
@login_required
def get_unread_count(request):
    """دریافت تعداد اعلان‌های خوانده نشده"""
    unread_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()

    return JsonResponse({
        'unread_count': unread_count
    })

@require_GET
@login_required
def get_notifications(request):
    """دریافت اعلان‌های کاربر"""
    try:
        limit = int(request.GET.get('limit', 10))
        notifications = Notification.objects.filter(
            user=request.user
        ).order_by('-created_at')[:limit]

        notifications_data = []
        for notification in notifications:
            notifications_data.append({
                'id': notification.id,
                'title': notification.title,
                'message': notification.message,
                'type': notification.notification_type,
                'icon': notification.icon or 'bell',
                'is_read': notification.is_read,
                'created_at': notification.get_time_ago(),
                'order_id': notification.order.id if notification.order else None,
            })

        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()

        return JsonResponse({
            'success': True,
            'notifications': notifications_data,
            'unread_count': unread_count
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_POST
@login_required
@csrf_exempt
def mark_as_read(request):
    """علامت‌گذاری اعلان به عنوان خوانده شده"""
    try:
        data = json.loads(request.body) if request.body else request.POST
        notification_id = data.get('notification_id')

        if notification_id:
            notification = Notification.objects.get(
                id=notification_id,
                user=request.user
            )
            notification.is_read = True
            notification.save()
        else:
            # علامت‌گذاری همه
            Notification.objects.filter(
                user=request.user,
                is_read=False
            ).update(is_read=True)

        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()

        return JsonResponse({
            'success': True,
            'message': 'اعلان خوانده شد',
            'unread_count': unread_count
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@require_POST
@login_required
@csrf_exempt
def delete_notification(request):
    """حذف اعلان"""
    try:
        data = json.loads(request.body) if request.body else request.POST
        notification_id = data.get('notification_id')

        notification = Notification.objects.get(
            id=notification_id,
            user=request.user
        )
        notification.delete()

        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()

        return JsonResponse({
            'success': True,
            'message': 'اعلان حذف شد',
            'unread_count': unread_count
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


# =======================


# views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.user.models.user import CustomUser
import jdatetime

@login_required
def complete_profile(request):
    user = request.user

    if request.method == 'POST':
        # دریافت داده‌ها از فرم
        name = request.POST.get('name', '').strip()
        family = request.POST.get('family', '').strip()
        email = request.POST.get('email', '').strip()
        birth_date_str = request.POST.get('birth_date', '').strip()
        gender = request.POST.get('gender')

        # به‌روزرسانی اطلاعات
        if name:
            user.name = name
        if family:
            user.family = family
        if email:
            user.email = email
        if gender in ['M', 'F']:
            user.gender = gender

        # پردازش تاریخ تولد شمسی
        if birth_date_str:
            try:
                # تبدیل تاریخ شمسی به میلادی
                jalali_parts = birth_date_str.split('/')
                if len(jalali_parts) == 3:
                    year = int(jalali_parts[0])
                    month = int(jalali_parts[1])
                    day = int(jalali_parts[2])

                    # تبدیل به میلادی
                    jalali_date = jdatetime.date(year, month, day)
                    gregorian_date = jalali_date.togregorian()

                    user.birth_date = gregorian_date
            except (ValueError, IndexError, jdatetime.JalaliDateOutsideRangeError):
                messages.error(request, 'فرمت تاریخ تولد صحیح نیست. مثال: 1400/1/1')

        # ذخیره کاربر
        user.save()
        messages.success(request, 'اطلاعات با موفقیت به‌روزرسانی شد')
        return redirect('dashboard:complete_profile')

    # آماده کردن داده‌ها برای نمایش
    context = {
        'user': user,
        'birth_date_jalali': None
    }

    # تبدیل تاریخ میلادی به شمسی برای نمایش
    if user.birth_date:
        try:
            gregorian_date = user.birth_date
            jalali_date = jdatetime.date.fromgregorian(
                year=gregorian_date.year,
                month=gregorian_date.month,
                day=gregorian_date.day
            )
            context['birth_date_jalali'] = f"{jalali_date.year}/{jalali_date.month}/{jalali_date.day}"
        except:
            context['birth_date_jalali'] = None

    return render(request, 'dashboard_app/profile/complete_profile.html', context)