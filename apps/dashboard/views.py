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
        "recent_orders": orders[:5],
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



from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

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