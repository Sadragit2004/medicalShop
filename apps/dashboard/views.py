
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import (
    Count,
    Sum,
    F,
    Q,
    BigIntegerField,
    ExpressionWrapper,
)
from django.shortcuts import render
from django.utils import timezone

from apps.order.models import Order, UserAddress, State


@login_required
def loadDashboard(request):
    user = request.user

    # ============================================================
    # Base QuerySets
    # ============================================================

    user_orders = Order.objects.filter(
        customer=user
    )

    user_addresses = UserAddress.objects.filter(
        user=user
    ).select_related(
        "state",
        "city",
    )

    # ============================================================
    # Order Statistics
    # ============================================================

    order_statistics = user_orders.aggregate(
        total_orders=Count("id"),

        pending_orders=Count(
            "id",
            filter=Q(status="pending"),
        ),

        processing_orders=Count(
            "id",
            filter=Q(status="processing"),
        ),

        paid_orders=Count(
            "id",
            filter=Q(status="paid"),
        ),

        shipped_orders=Count(
            "id",
            filter=Q(status="shipped"),
        ),

        delivered_orders=Count(
            "id",
            filter=Q(status="delivered"),
        ),

        canceled_orders=Count(
            "id",
            filter=Q(status="canceled"),
        ),
    )

    # ============================================================
    # Product Purchase Statistics
    # ============================================================

    order_details = Order.objects.filter(
        customer=user
    ).values(
        "details__id",
        "details__product_id",
    ).annotate(
        total_quantity=Sum("details__qty"),
    )

    product_statistics = Order.objects.filter(
        customer=user
    ).aggregate(
        total_items=Sum("details__qty"),

        unique_products=Count(
            "details__product_id",
            distinct=True,
        ),

        total_purchase_amount=Sum(
            ExpressionWrapper(
                F("details__price") * F("details__qty"),
                output_field=BigIntegerField(),
            )
        ),
    )

    # ============================================================
    # Payment Statistics
    # ============================================================

    payment_statistics = user_orders.aggregate(
        total_payments=Count(
            "peyment_order",
            distinct=True,
        ),

        successful_payments=Count(
            "peyment_order",
            filter=Q(
                peyment_order__isFinaly=True
            ),
            distinct=True,
        ),

        failed_or_pending_payments=Count(
            "peyment_order",
            filter=Q(
                peyment_order__isFinaly=False
            ),
            distinct=True,
        ),

        total_paid_amount=Sum(
            "peyment_order__amount",
            filter=Q(
                peyment_order__isFinaly=True
            ),
        ),
    )

    # ============================================================
    # Address Statistics
    # ============================================================

    address_count = user_addresses.count()

    default_address = user_addresses.first()

    # ============================================================
    # Recent Orders
    # ============================================================

    recent_orders_queryset = (
        user_orders
        .select_related(
            "customer",
            "address",
            "address__state",
            "address__city",
        )
        .prefetch_related(
            "details",
            "details__product",
            "details__brand",
            "peyment_order",
        )
        .order_by("-registerDate")
    )

    recent_orders = recent_orders_queryset[:5]

    # ============================================================
    # Paginated Orders
    # ============================================================

    paginator = Paginator(
        recent_orders_queryset,
        10,
    )

    page_number = request.GET.get("page")

    orders_page = paginator.get_page(page_number)

    # ============================================================
    # Order Status Information
    # ============================================================

    order_statuses = [
        {
            "value": value,
            "label": label,
            "count": order_statistics.get(
                f"{value}_orders",
                0,
            ),
        }
        for value, label in Order.STATUS_CHOICES
    ]

    # ============================================================
    # Final Statistics
    # ============================================================

    statistics = {
        "total_orders": order_statistics["total_orders"] or 0,

        "pending_orders": order_statistics["pending_orders"] or 0,

        "processing_orders": order_statistics["processing_orders"] or 0,

        "paid_orders": order_statistics["paid_orders"] or 0,

        "shipped_orders": order_statistics["shipped_orders"] or 0,

        "delivered_orders": order_statistics["delivered_orders"] or 0,

        "canceled_orders": order_statistics["canceled_orders"] or 0,

        "total_items": product_statistics["total_items"] or 0,

        "unique_products": product_statistics["unique_products"] or 0,

        "total_purchase_amount": (
            product_statistics["total_purchase_amount"] or 0
        ),

        "total_payments": payment_statistics["total_payments"] or 0,

        "successful_payments": (
            payment_statistics["successful_payments"] or 0
        ),

        "failed_or_pending_payments": (
            payment_statistics["failed_or_pending_payments"] or 0
        ),

        "total_paid_amount": (
            payment_statistics["total_paid_amount"] or 0
        ),

        "address_count": address_count,
    }

    # ============================================================
    # Dashboard Context
    # ============================================================

    context = {
        # User
        "user": user,

        # Statistics
        "statistics": statistics,

        # Orders
        "orders": orders_page,
        "orders_page": orders_page,
        "recent_orders": recent_orders,

        # Order Status
        "order_statuses": order_statuses,

        # Addresses
        "addresses": user_addresses,
        "address_count": address_count,
        "default_address": default_address,

        # States
        "states": State.objects.all().order_by("name"),

        # Pagination
        "paginator": paginator,

        # Dashboard Information
        "dashboard_date": timezone.now(),
    }

    return render(
        request,
        "dashboard_app/dashboard.html",
        context,
    )


from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import (
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.utils.dateparse import parse_date

from apps.order.models import Order, State


@login_required
def orders_page(request):
    user = request.user

    # --------------------------------------------------
    # Base QuerySet
    # --------------------------------------------------

    base_qs = (
        Order.objects
        .filter(customer=user)
        .select_related(
            "address",
            "address__state",
            "address__city",
        )
        .prefetch_related(
            "details",
            "details__product",
            "details__brand",
            "peyment_order",
        )
        .order_by("-registerDate")
    )

    # --------------------------------------------------
    # Annotate Order Items Total
    # --------------------------------------------------

    item_total_expression = ExpressionWrapper(
        F("details__price") * F("details__qty"),
        output_field=DecimalField(
            max_digits=30,
            decimal_places=3,
        ),
    )

    base_qs = base_qs.annotate(
        items_total_price=Coalesce(
            Sum(item_total_expression),
            Value(Decimal("0")),
            output_field=DecimalField(
                max_digits=30,
                decimal_places=3,
            ),
        ),
        items_count=Count("details", distinct=True),
    )

    # --------------------------------------------------
    # Filters
    # --------------------------------------------------

    status_filter = request.GET.get("status", "").strip()
    date_from_value = request.GET.get("date_from", "").strip()
    date_to_value = request.GET.get("date_to", "").strip()
    price_min_value = request.GET.get("price_min", "").strip()
    price_max_value = request.GET.get("price_max", "").strip()

    qs = base_qs

    # Status Filter
    valid_statuses = {
        value
        for value, label in Order._meta.get_field("status").choices
    }

    if status_filter and status_filter in valid_statuses:
        qs = qs.filter(status=status_filter)
    else:
        status_filter = ""

    # Date Filters
    date_from = parse_date(date_from_value) if date_from_value else None
    date_to = parse_date(date_to_value) if date_to_value else None

    if date_from:
        qs = qs.filter(registerDate__date__gte=date_from)
    else:
        date_from_value = ""

    if date_to:
        qs = qs.filter(registerDate__date__lte=date_to)
    else:
        date_to_value = ""

    # Price Filters
    price_min = None
    price_max = None

    if price_min_value:
        try:
            price_min = Decimal(price_min_value)

            if not price_min.is_finite() or price_min < 0:
                price_min = None
                price_min_value = ""

        except (InvalidOperation, ValueError):
            price_min_value = ""

    if price_max_value:
        try:
            price_max = Decimal(price_max_value)

            if not price_max.is_finite() or price_max < 0:
                price_max = None
                price_max_value = ""

        except (InvalidOperation, ValueError):
            price_max_value = ""

    if price_min is not None:
        qs = qs.filter(items_total_price__gte=price_min)

    if price_max is not None:
        qs = qs.filter(items_total_price__lte=price_max)

    # --------------------------------------------------
    # Pagination
    # --------------------------------------------------

    paginator = Paginator(qs, 10)

    page_number = request.GET.get("page", 1)
    orders_page = paginator.get_page(page_number)

    # --------------------------------------------------
    # Overall Statistics
    # --------------------------------------------------

    total_orders = base_qs.count()

    status_statistics = (
        Order.objects
        .filter(customer=user)
        .values("status")
        .annotate(count=Count("id"))
    )

    status_counts = {
        item["status"]: item["count"]
        for item in status_statistics
    }

    order_statuses = [
        {
            "value": value,
            "label": label,
            "count": status_counts.get(value, 0),
        }
        for value, label in Order._meta.get_field("status").choices
    ]

    total_items = (
        Order.objects
        .filter(customer=user)
        .aggregate(
            total=Coalesce(
                Sum("details__qty"),
                Value(Decimal("0")),
                output_field=DecimalField(
                    max_digits=30,
                    decimal_places=3,
                ),
            )
        )["total"]
    )

    total_items_amount = (
        Order.objects
        .filter(customer=user)
        .aggregate(
            total=Coalesce(
                Sum(item_total_expression),
                Value(Decimal("0")),
                output_field=DecimalField(
                    max_digits=30,
                    decimal_places=3,
                ),
            )
        )["total"]
    )

    # --------------------------------------------------
    # Payment Statistics
    # --------------------------------------------------

    payment_qs = user.peyment_customer.all()

    payment_statistics = payment_qs.aggregate(
        total_payments=Count("id"),
        successful_payments=Count(
            "id",
            filter=F("isFinaly"),
        ),
        total_paid_amount=Coalesce(
            Sum(
                "amount",
                filter=F("isFinaly"),
            ),
            Value(Decimal("0")),
            output_field=DecimalField(
                max_digits=30,
                decimal_places=3,
            ),
        ),
    )

    # --------------------------------------------------
    # Filtered Results Statistics
    # --------------------------------------------------

    filtered_statistics = {
        "count": paginator.count,
        "items_total": qs.aggregate(
            total=Coalesce(
                Sum("items_total_price"),
                Value(Decimal("0")),
                output_field=DecimalField(
                    max_digits=30,
                    decimal_places=3,
                ),
            )
        )["total"],
    }

    # --------------------------------------------------
    # Context
    # --------------------------------------------------

    context = {
        # Orders
        "orders": orders_page,
        "orders_page": orders_page,

        # Status
        "order_statuses": order_statuses,
        "status_filter": status_filter,

        # Date Filters
        "date_from": date_from_value,
        "date_to": date_to_value,

        # Price Filters
        "price_min": price_min_value,
        "price_max": price_max_value,

        # Overall Statistics
        "statistics": {
            "total_orders": total_orders,
            "total_items": total_items,
            "total_items_amount": total_items_amount,
            "total_paid_amount": payment_statistics["total_paid_amount"],
            "total_payments": payment_statistics["total_payments"],
            "successful_payments": payment_statistics["successful_payments"],
            "delivered_orders": status_counts.get("delivered", 0),
            "processing_orders": status_counts.get("processing", 0),
            "shipped_orders": status_counts.get("shipped", 0),
            "paid_orders": status_counts.get("paid", 0),
            "pending_orders": status_counts.get("pending", 0),
            "canceled_orders": status_counts.get("canceled", 0),
        },

        # Filtered Statistics
        "filtered_statistics": filtered_statistics,

        # Pagination
        "has_next": orders_page.has_next(),
        "has_previous": orders_page.has_previous(),
        "next_page_number": (
            orders_page.next_page_number()
            if orders_page.has_next()
            else None
        ),
        "previous_page_number": (
            orders_page.previous_page_number()
            if orders_page.has_previous()
            else None
        ),
        "page_number": orders_page.number,
        "num_pages": paginator.num_pages,
        "total_results": paginator.count,

        # Other Data
        "states": State.objects.all().order_by("name"),

        # Filter State
        "has_active_filters": any([
            status_filter,
            date_from_value,
            date_to_value,
            price_min_value,
            price_max_value,
        ]),
    }

    return render(
        request,
        "dashboard_app/orders.html",
        context,
    )


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