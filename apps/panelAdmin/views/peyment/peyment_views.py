# views/payments_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count, F
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
import jdatetime
from apps.peyment.models import Peyment, Order, CustomUser
import utils

# ========================
# PAYMENT LIST
# ========================

def payment_list(request):
    """لیست پرداخت‌ها"""
    payments = Peyment.objects.select_related('order', 'customer').all()

    # فیلتر بر اساس وضعیت پرداخت
    status = request.GET.get('status')
    if status == 'success':
        payments = payments.filter(isFinaly=True)
    elif status == 'failed':
        payments = payments.filter(isFinaly=False)

    # فیلتر بر اساس کاربر
    user_id = request.GET.get('user')
    if user_id:
        payments = payments.filter(customer_id=user_id)

    # فیلتر بر اساس سفارش
    order_code = request.GET.get('order_code')
    if order_code:
        payments = payments.filter(order__orderCode__icontains=order_code)

    # فیلتر بر اساس کد پیگیری
    ref_id = request.GET.get('ref_id')
    if ref_id:
        payments = payments.filter(refId__icontains=ref_id)

    # فیلتر بر اساس تاریخ
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d')
            payments = payments.filter(createAt__date__gte=date_from)
        except:
            pass
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d')
            payments = payments.filter(createAt__date__lte=date_to)
        except:
            pass

    # فیلتر بر اساس مبلغ
    amount_min = request.GET.get('amount_min')
    amount_max = request.GET.get('amount_max')
    if amount_min:
        try:
            payments = payments.filter(amount__gte=int(amount_min))
        except:
            pass
    if amount_max:
        try:
            payments = payments.filter(amount__lte=int(amount_max))
        except:
            pass

    # مرتب‌سازی
    sort_by = request.GET.get('sort_by', '-createAt')
    if sort_by in ['createAt', '-createAt', 'amount', '-amount']:
        if sort_by == 'amount':
            payments = payments.order_by('amount')
        elif sort_by == '-amount':
            payments = payments.order_by('-amount')
        else:
            payments = payments.order_by(sort_by)

    # محاسبه آمار برای هر پرداخت
    for payment in payments:
        payment.jalali_date = payment.get_jalali_register_date()

    # مجموع مبالغ
    total_amount = payments.aggregate(Sum('amount'))['amount__sum'] or 0
    success_amount = payments.filter(isFinaly=True).aggregate(Sum('amount'))['amount__sum'] or 0
    failed_amount = payments.filter(isFinaly=False).aggregate(Sum('amount'))['amount__sum'] or 0

    paginator = Paginator(payments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    users = CustomUser.objects.all()

    return render(request, 'panelAdmin/payments/list.html', {
        'page_obj': page_obj,
        'users': users,
        'total_amount': total_amount,
        'success_amount': success_amount,
        'failed_amount': failed_amount,
        'selected_status': status,
        'selected_user': user_id,
        'order_code': order_code,
        'ref_id': ref_id,
        'date_from': date_from.strftime('%Y-%m-%d') if isinstance(date_from, datetime) else date_from,
        'date_to': date_to.strftime('%Y-%m-%d') if isinstance(date_to, datetime) else date_to,
        'amount_min': amount_min,
        'amount_max': amount_max,
        'sort_by': sort_by
    })


# ========================
# PAYMENT DETAIL
# ========================

def payment_detail(request, payment_id):
    """مشاهده جزئیات پرداخت"""
    payment = get_object_or_404(
        Peyment.objects.select_related('order', 'customer', 'order__address__city__state'),
        id=payment_id
    )

    # تاریخ شمسی
    jalali_date = payment.get_jalali_register_date()

    # وضعیت پرداخت به فارسی
    status_text = "موفق" if payment.isFinaly else "ناموفق"

    # اطلاعات سفارش مرتبط
    order = payment.order
    order_total = order.getTotalPrice()
    order_final = order.getFinalPrice()

    return render(request, 'panelAdmin/payments/detail.html', {
        'payment': payment,
        'jalali_date': jalali_date,
        'status_text': status_text,
        'order': order,
        'order_total': order_total,
        'order_final': order_final,
        'order_details': order.details.all() if hasattr(order, 'details') else []
    })


# ========================
# PAYMENT CREATE
# ========================

def payment_create(request):
    """ایجاد پرداخت جدید"""
    orders = Order.objects.filter(isFinally=True).select_related('customer')

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # ایجاد پرداخت
                order = get_object_or_404(Order, id=request.POST.get('order'))

                payment = Peyment.objects.create(
                    order=order,
                    customer=order.customer,
                    amount=int(request.POST.get('amount', 0)),
                    description=request.POST.get('description', ''),
                    isFinaly=request.POST.get('isFinaly') == 'on',
                    statusCode=request.POST.get('statusCode') if request.POST.get('statusCode') else None,
                    refId=request.POST.get('refId')
                )

                # اگر پرداخت موفق بود، وضعیت سفارش را به پرداخت شده تغییر بده
                if payment.isFinaly:
                    order.status = 'processing'
                    order.save()

                messages.success(request, f'پرداخت برای سفارش {order.orderCode} با موفقیت ثبت شد')
                return redirect('admin_payment_detail', payment_id=payment.id)

        except Exception as e:
            messages.error(request, f'خطا در ثبت پرداخت: {str(e)}')

    return render(request, 'panelAdmin/payments/create.html', {
        'orders': orders
    })


# ========================
# PAYMENT UPDATE
# ========================

def payment_update(request, payment_id):
    """ویرایش پرداخت"""
    payment = get_object_or_404(
        Peyment.objects.select_related('order'),
        id=payment_id
    )

    if request.method == 'POST':
        try:
            with transaction.atomic():
                old_status = payment.isFinaly

                payment.amount = int(request.POST.get('amount', payment.amount))
                payment.description = request.POST.get('description', payment.description)
                payment.isFinaly = request.POST.get('isFinaly') == 'on'
                payment.statusCode = request.POST.get('statusCode') if request.POST.get('statusCode') else None
                payment.refId = request.POST.get('refId', payment.refId)
                payment.save()

                # اگر وضعیت پرداخت تغییر کرده بود
                if old_status != payment.isFinaly:
                    order = payment.order
                    if payment.isFinaly:
                        # اگر پرداخت موفق شد
                        order.status = 'processing'
                    else:
                        # اگر پرداخت ناموفق شد
                        order.status = 'pending'
                    order.save()

                messages.success(request, 'پرداخت با موفقیت ویرایش شد')
                return redirect('admin_payment_detail', payment_id=payment.id)

        except Exception as e:
            messages.error(request, f'خطا در ویرایش پرداخت: {str(e)}')

    return render(request, 'panelAdmin/payments/update.html', {
        'payment': payment
    })


# ========================
# PAYMENT DELETE
# ========================

# views/payment_views.py
def payment_delete(request, payment_id):
    """حذف پرداخت"""
    payment = get_object_or_404(Peyment, id=payment_id)

    if request.method == 'POST':
        try:
            # اگر پرداخت موفق بود، قبل از حذف وضعیت سفارش را برگردان
            if payment.isFinaly:
                order = payment.order
                order.status = 'pending'
                order.save()

            payment_ref = payment.refId or payment.id
            payment.delete()

            messages.success(request, f'پرداخت {payment_ref} با موفقیت حذف شد')
            return redirect('panelAdmin:admin_payment_list')  # تغییر اینجا
        except Exception as e:
            messages.error(request, f'خطا در حذف پرداخت: {str(e)}')

    return render(request, 'panelAdmin/payments/delete_confirm.html', {
        'payment': payment  # مطمئن شویم payment به تمپلیت پاس داده می‌شود
    })


# ========================
# PAYMENT ACTIONS
# ========================

def toggle_payment_status(request, payment_id):
    """تغییر وضعیت پرداخت (موفق/ناموفق)"""
    payment = get_object_or_404(Peyment, id=payment_id)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                payment.isFinaly = not payment.isFinaly
                payment.save()

                # بروزرسانی وضعیت سفارش
                order = payment.order
                if payment.isFinaly:
                    order.status = 'processing'
                    status_text = 'موفق'
                else:
                    order.status = 'pending'
                    status_text = 'ناموفق'
                order.save()

                messages.success(request, f'وضعیت پرداخت به {status_text} تغییر یافت')
        except Exception as e:
            messages.error(request, f'خطا در تغییر وضعیت پرداخت: {str(e)}')

    return redirect('admin_payment_detail', payment_id=payment.id)


def verify_payment(request, payment_id):
    """تأیید دستی پرداخت"""
    payment = get_object_or_404(Peyment, id=payment_id)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                payment.isFinaly = True
                payment.statusCode = 200
                payment.save()

                # بروزرسانی وضعیت سفارش
                order = payment.order
                order.status = 'processing'
                order.save()

                messages.success(request, 'پرداخت با موفقیت تأیید شد')
        except Exception as e:
            messages.error(request, f'خطا در تأیید پرداخت: {str(e)}')

    return redirect('admin_payment_detail', payment_id=payment.id)


def cancel_payment(request, payment_id):
    """لغو پرداخت (تبدیل به ناموفق)"""
    payment = get_object_or_404(Peyment, id=payment_id)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                payment.isFinaly = False
                payment.statusCode = 400
                payment.save()

                # بروزرسانی وضعیت سفارش
                order = payment.order
                order.status = 'pending'
                order.save()

                messages.success(request, 'پرداخت با موفقیت لغو شد')
        except Exception as e:
            messages.error(request, f'خطا در لغو پرداخت: {str(e)}')

    return redirect('admin_payment_detail', payment_id=payment.id)


# ========================
# BULK ACTIONS
# ========================

def bulk_verify_payments(request):
    """تأیید گروهی پرداخت‌ها"""
    if request.method == 'POST':
        try:
            payment_ids = request.POST.getlist('payment_ids')
            if not payment_ids:
                messages.warning(request, 'هیچ پرداختی انتخاب نشده است')
                return redirect('admin_payment_list')

            with transaction.atomic():
                payments = Peyment.objects.filter(id__in=payment_ids, isFinaly=False)
                count = 0

                for payment in payments:
                    payment.isFinaly = True
                    payment.statusCode = 200
                    payment.save()

                    # بروزرسانی وضعیت سفارش
                    order = payment.order
                    order.status = 'processing'
                    order.save()

                    count += 1

                messages.success(request, f'{count} پرداخت با موفقیت تأیید شدند')

        except Exception as e:
            messages.error(request, f'خطا در تأیید گروهی پرداخت‌ها: {str(e)}')

    return redirect('admin_payment_list')


def bulk_delete_payments(request):
    """حذف گروهی پرداخت‌ها"""
    if request.method == 'POST':
        try:
            payment_ids = request.POST.getlist('payment_ids')
            if not payment_ids:
                messages.warning(request, 'هیچ پرداختی انتخاب نشده است')
                return redirect('admin_payment_list')

            with transaction.atomic():
                payments = Peyment.objects.filter(id__in=payment_ids)
                count = payments.count()

                # برگرداندن وضعیت سفارش‌هایی که پرداخت موفق داشتند
                successful_payments = payments.filter(isFinaly=True)
                for payment in successful_payments:
                    order = payment.order
                    order.status = 'pending'
                    order.save()

                payments.delete()

                messages.success(request, f'{count} پرداخت با موفقیت حذف شدند')

        except Exception as e:
            messages.error(request, f'خطا در حذف گروهی پرداخت‌ها: {str(e)}')

    return redirect('admin_payment_list')


# ========================
# PAYMENT REPORTS
# ========================

def payment_report(request):
    """گزارش پرداخت‌ها"""
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

    # فیلتر پرداخت‌ها بر اساس تاریخ
    payments = Peyment.objects.filter(
        createAt__date__range=[start_date, end_date]
    )

    # آمار کلی
    total_payments = payments.count()
    total_amount = payments.aggregate(Sum('amount'))['amount__sum'] or 0

    # پرداخت‌های موفق
    successful_payments = payments.filter(isFinaly=True)
    successful_count = successful_payments.count()
    successful_amount = successful_payments.aggregate(Sum('amount'))['amount__sum'] or 0

    # پرداخت‌های ناموفق
    failed_payments = payments.filter(isFinaly=False)
    failed_count = failed_payments.count()
    failed_amount = failed_payments.aggregate(Sum('amount'))['amount__sum'] or 0

    # آمار بر اساس روز
    daily_stats = []
    current_date = start_date
    while current_date <= end_date:
        day_payments = payments.filter(createAt__date=current_date)
        day_count = day_payments.count()
        day_amount = day_payments.aggregate(Sum('amount'))['amount__sum'] or 0

        day_successful = day_payments.filter(isFinaly=True).count()
        day_failed = day_payments.filter(isFinaly=False).count()

        daily_stats.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'date_jalali': utils.to_jalali(current_date),
            'payment_count': day_count,
            'total_amount': day_amount,
            'successful_count': day_successful,
            'failed_count': day_failed,
        })

        current_date += timedelta(days=1)

    # کاربران برتر بر اساس تعداد پرداخت
    top_users_by_count = payments.values(
        'customer__mobileNumber',
        'customer__name',
        'customer__family'
    ).annotate(
        payment_count=Count('id'),
        total_paid=Sum('amount')
    ).order_by('-payment_count')[:10]

    # کاربران برتر بر اساس مبلغ پرداختی
    top_users_by_amount = payments.values(
        'customer__mobileNumber',
        'customer__name',
        'customer__family'
    ).annotate(
        payment_count=Count('id'),
        total_paid=Sum('amount')
    ).order_by('-total_paid')[:10]

    # میانگین مبلغ پرداخت
    avg_payment = total_amount / total_payments if total_payments > 0 else 0

    context = {
        # تاریخ‌ها
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'start_date_jalali': utils.to_jalali(start_date),
        'end_date_jalali': utils.to_jalali(end_date),

        # آمار کلی
        'total_payments': total_payments,
        'total_amount': total_amount,
        'avg_payment': int(avg_payment),

        # آمار موفق/ناموفق
        'successful_count': successful_count,
        'successful_amount': successful_amount,
        'successful_percentage': round((successful_count / total_payments * 100), 2) if total_payments > 0 else 0,

        'failed_count': failed_count,
        'failed_amount': failed_amount,
        'failed_percentage': round((failed_count / total_payments * 100), 2) if total_payments > 0 else 0,

        # آمار روزانه
        'daily_stats': daily_stats,

        # کاربران برتر
        'top_users_by_count': top_users_by_count,
        'top_users_by_amount': top_users_by_amount,

        # تنظیمات گزارش
        'date_range_options': [
            ('7days', '۷ روز اخیر'),
            ('30days', '۳۰ روز اخیر'),
            ('90days', '۹۰ روز اخیر'),
            ('custom', 'تاریخ دلخواه'),
        ]
    }

    return render(request, 'panelAdmin/payments/report.html', context)


# ========================
# AJAX VIEWS
# ========================

def get_order_details(request):
    """دریافت جزئیات سفارش برای ایجاد پرداخت"""
    order_id = request.GET.get('order_id')
    if order_id:
        try:
            order = Order.objects.get(id=order_id)

            data = {
                'order_code': str(order.orderCode),
                'customer_name': f"{order.customer.name or ''} {order.customer.family or ''}".strip() or order.customer.mobileNumber,
                'customer_mobile': order.customer.mobileNumber,
                'order_total': order.getTotalPrice(),
                'order_final': order.getFinalPrice(),
                'order_status': order.get_status_display(),
                'order_discount': order.discount,
                'order_items_count': order.details.count() if hasattr(order, 'details') else 0,
            }
            return JsonResponse(data)
        except Order.DoesNotExist:
            return JsonResponse({'error': 'سفارش یافت نشد'}, status=404)

    return JsonResponse({'error': 'آیدی سفارش ارسال نشده'}, status=400)


def search_payments_ajax(request):
    """جستجوی پرداخت‌ها برای انتخاب گروهی"""
    search_term = request.GET.get('q', '')
    status = request.GET.get('status', '')

    payments = Peyment.objects.all()

    if status == 'success':
        payments = payments.filter(isFinaly=True)
    elif status == 'failed':
        payments = payments.filter(isFinaly=False)

    if search_term:
        payments = payments.filter(
            Q(refId__icontains=search_term) |
            Q(order__orderCode__icontains=search_term) |
            Q(customer__mobileNumber__icontains=search_term) |
            Q(customer__name__icontains=search_term) |
            Q(customer__family__icontains=search_term)
        )

    payments = payments[:20]  # محدود کردن نتایج

    results = []
    for payment in payments:
        results.append({
            'id': payment.id,
            'ref_id': payment.refId or 'بدون کد پیگیری',
            'order_code': str(payment.order.orderCode),
            'customer': payment.customer.mobileNumber,
            'amount': f"{payment.amount:,}",
            'status': 'موفق' if payment.isFinaly else 'ناموفق',
            'date': payment.get_jalali_register_date(),
        })

    return JsonResponse({'results': results})


# ========================
# DASHBOARD WIDGETS
# ========================

def payment_dashboard_widget(request):
    """ویجت داشبورد برای پرداخت‌ها"""
    now = timezone.now()
    today = now.date()

    # پرداخت‌های امروز
    today_payments = Peyment.objects.filter(createAt__date=today)
    today_count = today_payments.count()
    today_amount = today_payments.aggregate(Sum('amount'))['amount__sum'] or 0

    # پرداخت‌های موفق امروز
    today_successful = today_payments.filter(isFinaly=True)
    today_successful_count = today_successful.count()
    today_successful_amount = today_successful.aggregate(Sum('amount'))['amount__sum'] or 0

    # پرداخت‌های هفته جاری
    week_start = today - timedelta(days=today.weekday())
    week_payments = Peyment.objects.filter(createAt__date__gte=week_start)
    week_amount = week_payments.aggregate(Sum('amount'))['amount__sum'] or 0

    # پرداخت‌های ماه جاری
    month_start = today.replace(day=1)
    month_payments = Peyment.objects.filter(createAt__date__gte=month_start)
    month_amount = month_payments.aggregate(Sum('amount'))['amount__sum'] or 0

    # آخرین پرداخت‌ها
    recent_payments = Peyment.objects.select_related('order', 'customer').order_by('-createAt')[:10]

    # پرداخت‌های نیازمند توجه (ناموفق)
    failed_payments = Peyment.objects.filter(isFinaly=False).order_by('-createAt')[:5]

    context = {
        # آمار امروز
        'today_count': today_count,
        'today_amount': today_amount,
        'today_successful_count': today_successful_count,
        'today_successful_amount': today_successful_amount,
        'today_success_rate': round((today_successful_count / today_count * 100), 2) if today_count > 0 else 0,

        # آمار هفته و ماه
        'week_amount': week_amount,
        'month_amount': month_amount,

        # لیست‌ها
        'recent_payments': recent_payments,
        'failed_payments': failed_payments,

        'now': now,
    }

    return render(request, 'panelAdmin/payments/dashboard_widget.html', context)