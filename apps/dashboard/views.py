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
        qs = qs.filter(details__price__gte=price_min)
    if price_max:
        qs = qs.filter(details__price__lte=price_max)

    qs = qs.distinct()

    context = {
        "orders": qs,
        "states": State.objects.all().order_by("name"),
        "status_filter": status or "",
        "date_from": date_from or "",
        "date_to": date_to or "",
        "price_min": price_min or "",
        "price_max": price_max or "",
    }
    return render(request, "dashboard_app/orders.html", context)