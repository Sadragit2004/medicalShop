from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Count, Sum, Q, F, Value, DecimalField, Subquery, OuterRef
import json
from decimal import Decimal

from apps.user.models import CustomUser
from apps.order.models import Order, OrderDetail
from apps.product.models import Product
from apps.peyment.models import Peyment

def admin_check(user):
    return user.is_authenticated and user.is_staff

@login_required
@user_passes_test(admin_check, login_url='/admin/login/')
def admin_dashboard(request):
    """صفحه اصلی داشبورد ادمین"""
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)

    # آمار کاربران
    total_users = CustomUser.objects.count()
    new_users_today = CustomUser.objects.filter(createAt__date=today).count()

    # آمار سفارشات
    total_orders = Order.objects.count()
    today_orders = Order.objects.filter(registerDate__date=today).count()

    # آمار محصولات
    total_products = Product.objects.count()
    active_products = Product.objects.filter(isActive=True).count()

    # آمار مالی
    total_revenue = Peyment.objects.filter(isFinaly=True).aggregate(
        Sum('amount')
    )['amount__sum'] or Decimal('0')

    today_revenue = Peyment.objects.filter(
        isFinaly=True,
        createAt__date=today
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')

    # سفارشات اخیر
    recent_orders = Order.objects.select_related('customer').order_by('-registerDate')[:5]

    # کاربران جدید
    recent_users = CustomUser.objects.order_by('-createAt')[:5]

    # محصولات پرفروش - روش جایگزین
    # ابتدا آمار فروش هر محصول را محاسبه می‌کنیم
    top_products_list = []

    # محاسبه فروش برای هر محصول
    all_products = Product.objects.all()[:10]  # محدود کردن برای کارایی

    for product in all_products:
        # محاسبه تعداد فروش
        total_sold = OrderDetail.objects.filter(product=product).aggregate(
            total=Sum('qty')
        )['total'] or 0

        if total_sold > 0:
            # محاسبه درآمد
            total_revenue = OrderDetail.objects.filter(product=product).aggregate(
                total=Sum(F('price') * F('qty'), output_field=DecimalField())
            )['total'] or Decimal('0')

            product.total_sold = total_sold
            product.total_revenue = total_revenue
            top_products_list.append(product)

    # مرتب‌سازی بر اساس فروش
    top_products = sorted(top_products_list, key=lambda x: x.total_sold, reverse=True)[:5]

    # داده‌های نمودار ۷ روز اخیر
    chart_labels = []
    chart_data = []

    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        chart_labels.append(date.strftime('%Y/%m/%d'))

        day_orders = Order.objects.filter(registerDate__date=date)
        day_revenue = Decimal('0')
        for order in day_orders:
            try:
                final_price = order.getFinalPrice()
                if final_price:
                    day_revenue += Decimal(str(final_price))
            except:
                pass
        chart_data.append(float(day_revenue))

    context = {
        'stats': {
            'total_users': total_users,
            'new_users_today': new_users_today,
            'total_orders': total_orders,
            'today_orders': today_orders,
            'total_products': total_products,
            'active_products': active_products,
            'total_revenue': total_revenue,
            'today_revenue': today_revenue,
        },
        'recent_orders': recent_orders,
        'recent_users': recent_users,
        'top_products': top_products,
        'chart_labels': json.dumps(chart_labels, ensure_ascii=False),
        'chart_data': json.dumps(chart_data),
    }

    return render(request, 'panelAdmin/dashboard/index.html', context)