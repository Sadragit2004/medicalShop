from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Count, Sum, Q, F, Value, DecimalField, Subquery, OuterRef, Prefetch
import json
from decimal import Decimal

from apps.user.models.user import CustomUser
from apps.order.models import Order, OrderDetail
from apps.product.models import Product
from apps.peyment.models import Peyment

def admin_check(user):
    return user.is_authenticated and user.is_staff

@login_required
@user_passes_test(admin_check, login_url='/admin/login/')
def admin_dashboard(request):
    """صفحه اصلی داشبورد ادمین با آمار دقیق"""

    today = timezone.now().date()
    now = timezone.now()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # ========== آمار کاربران ==========
    # تعداد کل کاربران
    total_users = CustomUser.objects.count()

    # کاربران جدید امروز
    new_users_today = CustomUser.objects.filter(
        createAt__date=today
    ).count()

    # کاربران جدید این هفته
    new_users_week = CustomUser.objects.filter(
        createAt__date__gte=week_ago
    ).count()

    # کاربران فعال (کسانی که سفارش داشتن)
    active_users = CustomUser.objects.filter(
        orders__isnull=False
    ).distinct().count()

    # ========== آمار سفارشات ==========
    # کل سفارشات
    total_orders = Order.objects.count()

    # سفارشات امروز
    today_orders = Order.objects.filter(
        registerDate__date=today
    ).count()

    # سفارشات این هفته
    week_orders = Order.objects.filter(
        registerDate__date__gte=week_ago
    ).count()

    # سفارشات در انتظار
    pending_orders = Order.objects.filter(
        status='pending'
    ).count()

    # سفارشات در حال پردازش
    processing_orders = Order.objects.filter(
        status='processing'
    ).count()

    # سفارشات پرداخت شده
    paid_orders = Order.objects.filter(
        status='paid'
    ).count()

    # سفارشات تحویل شده امروز
    delivered_today = Order.objects.filter(
        status='delivered',
        updateDate__date=today
    ).count()

    # ========== آمار محصولات ==========
    # کل محصولات
    total_products = Product.objects.count()

    # محصولات فعال
    active_products = Product.objects.filter(isActive=True).count()

    # محصولات ناموجود
    out_of_stock = Product.objects.filter(
        Q(stock=0) | Q(stock__isnull=True)
    ).count()

    # محصولات با موجودی کم (کمتر از 5)
    low_stock = Product.objects.filter(
        stock__lte=5,
        stock__gt=0
    ).count()

    # ========== آمار مالی ==========
    # محاسبه درآمد فقط از پرداخت‌های نهایی شده (isFinaly=True)

    # کل درآمد (همه زمان‌ها)
    total_revenue = Peyment.objects.filter(
        isFinaly=True  # فقط پرداخت‌های نهایی شده
    ).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')

    # درآمد امروز
    today_revenue = Peyment.objects.filter(
        isFinaly=True,
        createAt__date=today
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    # درآمد این هفته
    week_revenue = Peyment.objects.filter(
        isFinaly=True,
        createAt__date__gte=week_ago
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    # درآمد این ماه
    month_revenue = Peyment.objects.filter(
        isFinaly=True,
        createAt__date__gte=month_ago
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    # میانگین ارزش هر سفارش
    # برای محاسبه میانگین، از سفارش‌هایی که پرداخت نهایی شدن استفاده می‌کنیم
    paid_orders_count = Order.objects.filter(
        status='paid',
        isFinally=True
    ).count()

    if paid_orders_count > 0:
        avg_order_value = total_revenue / paid_orders_count
    else:
        avg_order_value = Decimal('0')

    # ========== سفارشات اخیر با جزئیات کامل ==========
    recent_orders = Order.objects.select_related(
        'customer', 'address__state', 'address__city'
    ).prefetch_related(
        Prefetch('details', queryset=OrderDetail.objects.select_related('product', 'brand'))
    ).order_by('-registerDate')[:10]

    # اضافه کردن اطلاعات اضافی به هر سفارش
    for order in recent_orders:
        # محاسبه قیمت نهایی
        order.final_price = order.getFinalPrice()
        # تعداد آیتم‌ها
        order.items_count = order.details.count()
        # وضعیت به فارسی
        order.status_display = dict(Order.STATUS_CHOICES).get(order.status, order.status)

    # ========== کاربران جدید با آخرین فعالیت ==========
    recent_users = CustomUser.objects.annotate(
        orders_count=Count('orders'),
        last_order_date=Subquery(
            Order.objects.filter(
                customer=OuterRef('pk')
            ).order_by('-registerDate').values('registerDate')[:1]
        )
    ).order_by('-createAt')[:10]

    # ========== محصولات پرفروش ==========
    # محاسبه دقیق پرفروش‌ترین محصولات
    top_products = []

    # دریافت همه محصولات فعال
    all_products = Product.objects.filter(isActive=True).prefetch_related('category', 'brand')[:20]

    for product in all_products:
        # محاسبه تعداد فروش (تعداد آیتم‌های فروخته شده) - فقط سفارشات نهایی شده
        total_sold = OrderDetail.objects.filter(
            product=product,
            order__status__in=['delivered', 'paid', 'processing'],
            order__isFinally=True
        ).aggregate(total=Sum('qty'))['total'] or 0

        if total_sold > 0:  # فقط محصولاتی که فروش داشتن
            # محاسبه درآمد از این محصول
            total_revenue_product = OrderDetail.objects.filter(
                product=product,
                order__status__in=['delivered', 'paid', 'processing'],
                order__isFinally=True
            ).aggregate(
                total=Sum(F('price') * F('qty'), output_field=DecimalField())
            )['total'] or Decimal('0')

            product.total_sold = total_sold
            product.total_revenue = total_revenue_product
            top_products.append(product)

    # مرتب‌سازی بر اساس تعداد فروش
    top_products = sorted(top_products, key=lambda x: x.total_sold, reverse=True)[:5]

    # ========== آخرین پرداخت‌ها ==========
    recent_payments = Peyment.objects.filter(
        isFinaly=True
    ).select_related('order__customer').order_by('-createAt')[:5]

    # ========== آمار وضعیت سفارشات ==========
    order_status_stats = []
    for status_code, status_name in Order.STATUS_CHOICES:
        count = Order.objects.filter(status=status_code).count()
        if count > 0:
            order_status_stats.append({
                'code': status_code,
                'name': status_name,
                'count': count,
                'percentage': round((count / total_orders * 100), 1) if total_orders > 0 else 0
            })

    # ========== محاسبه نرخ رشد ==========
    # مقایسه با هفته قبل
    last_week_orders = Order.objects.filter(
        registerDate__date__gte=week_ago - timedelta(days=7),
        registerDate__date__lt=week_ago
    ).count()

    if last_week_orders > 0:
        order_growth = ((week_orders - last_week_orders) / last_week_orders) * 100
    else:
        order_growth = 100 if week_orders > 0 else 0

    # ========== هشدارها و اعلان‌ها ==========
    alerts = []

    # هشدار موجودی کم
    if low_stock > 0:
        alerts.append({
            'type': 'warning',
            'message': f'{low_stock} محصول موجودی کم دارند (کمتر از 5 عدد)',
            'icon': 'exclamation-triangle',
            'link': 'panelAdmin:admin_product_list?stock=low'
        })

    # هشدار سفارشات در انتظار
    if pending_orders > 5:
        alerts.append({
            'type': 'info',
            'message': f'{pending_orders} سفارش در انتظار بررسی هستند',
            'icon': 'clock',
            'link': 'panelAdmin:admin_order_list?status=pending'
        })

    # هشدار محصولات ناموجود
    if out_of_stock > 0:
        alerts.append({
            'type': 'danger',
            'message': f'{out_of_stock} محصول ناموجود هستند',
            'icon': 'times-circle',
            'link': 'panelAdmin:admin_product_list?stock=0'
        })

    # ========== داده‌های نمودار فروش ۷ روز اخیر ==========
    chart_labels = []
    chart_data = []
    chart_orders_count = []

    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        chart_labels.append(date.strftime('%Y/%m/%d'))

        # درآمد هر روز (فقط پرداخت‌های نهایی شده)
        day_revenue = Peyment.objects.filter(
            isFinaly=True,
            createAt__date=date
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # تعداد سفارشات هر روز
        day_orders = Order.objects.filter(
            registerDate__date=date
        ).count()

        chart_data.append(float(day_revenue))
        chart_orders_count.append(day_orders)

    context = {
        'stats': {
            # کاربران
            'total_users': total_users,
            'new_users_today': new_users_today,
            'new_users_week': new_users_week,
            'active_users': active_users,

            # سفارشات
            'total_orders': total_orders,
            'today_orders': today_orders,
            'week_orders': week_orders,
            'pending_orders': pending_orders,
            'processing_orders': processing_orders,
            'paid_orders': paid_orders,
            'delivered_today': delivered_today,
            'order_growth': round(order_growth, 1),

            # محصولات
            'total_products': total_products,
            'active_products': active_products,
            'out_of_stock': out_of_stock,
            'low_stock': low_stock,

            # مالی
            'total_revenue': total_revenue,
            'today_revenue': today_revenue,
            'week_revenue': week_revenue,
            'month_revenue': month_revenue,
            'avg_order_value': round(avg_order_value, 0),

            # فرمت‌بندی شده برای نمایش
            'total_revenue_formatted': f"{int(total_revenue):,}",
            'today_revenue_formatted': f"{int(today_revenue):,}",
            'week_revenue_formatted': f"{int(week_revenue):,}",
            'month_revenue_formatted': f"{int(month_revenue):,}",
            'avg_order_value_formatted': f"{int(avg_order_value):,}",
        },
        'recent_orders': recent_orders,
        'recent_users': recent_users,
        'top_products': top_products,
        'recent_payments': recent_payments,
        'order_status_stats': order_status_stats,
        'alerts': alerts,
        'chart_labels': json.dumps(chart_labels, ensure_ascii=False),
        'chart_data': json.dumps(chart_data),
        'chart_orders_count': json.dumps(chart_orders_count),
        'last_update': timezone.now(),
    }

    return render(request, 'panelAdmin/dashboard/index.html', context)