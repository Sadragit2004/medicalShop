from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse
import json

from apps.order.models import Order, OrderDetail


class AdminRequiredMixin(UserPassesTestMixin):
    """میکسین برای بررسی ادمین بودن کاربر"""

    def test_func(self):
        # فقط superuser یا is_staff=True میتونن دسترسی داشته باشن
        return self.request.user.is_authenticated and (
            self.request.user.is_superuser or self.request.user.is_staff
        )

    def handle_no_permission(self):
        # اگر دسترسی نداشت، به صفحه اصلی یا لاگین هدایت کن
        return redirect('main:index')  # اسم url صفحه اصلی رو بذار


class OrderListView(AdminRequiredMixin, LoginRequiredMixin, View):
    """
    ویو لیست سفارشات - فقط ادمین‌ها
    """
    template_name = 'order_app/order_list2.html'
    login_url = '/login/'

    def get(self, request):
        # ... کد قبلی (همون کدی که کار میکرد)
        search_query = request.GET.get('search', '').strip()
        status_filter = request.GET.get('status', 'all')
        price_filter = request.GET.get('price', 'all')

        orders = Order.objects.select_related(
            'customer', 'address__state', 'address__city'
        ).prefetch_related('details__product', 'details__brand').all()

        if search_query:
            orders = orders.filter(
                Q(orderCode__icontains=search_query) |
                Q(customer__mobileNumber__icontains=search_query) |
                Q(customer__name__icontains=search_query) |
                Q(customer__family__icontains=search_query) |
                Q(details__product__title__icontains=search_query) |
                Q(details__product__brand__title__icontains=search_query)
            ).distinct()

        if status_filter != 'all':
            orders = orders.filter(status=status_filter)

        order_list = []
        for order in orders:
            final_price = order.get_order_total_price() / 10
            if price_filter == 'above5' and final_price <= 5000000:
                continue
            elif price_filter == 'above10' and final_price <= 10000000:
                continue
            order_list.append(order)

        total_orders = Order.objects.count()
        pending_count = Order.objects.filter(status='pending').count()
        processing_count = Order.objects.filter(status='processing').count()
        paid_count = Order.objects.filter(status='paid').count()
        shipped_count = Order.objects.filter(status='shipped').count()
        completed_count = Order.objects.filter(status='delivered').count()
        canceled_count = Order.objects.filter(status='canceled').count()

        today = timezone.now().date()
        today_orders = Order.objects.filter(registerDate__date=today)
        today_revenue = sum(order.get_order_total_price() for order in today_orders) / 10

        orders_data = []
        for order in order_list:
            address_text = ""
            if order.address:
                address_text = f"{order.address.state.name}، {order.address.city.name}، {order.address.addressDetail}"
                if order.address.postalCode:
                    address_text += f" - کد پستی: {order.address.postalCode}"

            products_list = []
            for detail in order.details.all()[:3]:
                products_list.append(detail.product.title)
            products_preview = "، ".join(products_list)
            if order.details.count() > 3:
                products_preview += f" و {order.details.count() - 3} محصول دیگر"

            orders_data.append({
                'id': str(order.orderCode),
                'order_code': str(order.orderCode),
                'order_code_short': str(order.orderCode)[:8],
                'customer_name': str(order.customer.family) or order.customer.mobileNumber,
                'customer_mobile': order.customer.mobileNumber,
                'status': order.status,
                'status_display': order.get_status_display(),
                'amount': order.get_order_total_price() / 10,
                'amount_display': f"{int(order.get_order_total_price() / 10):,}",
                'jalali_date': order.get_jalali_register_datetime(),
                'address': address_text,
                'products_preview': products_preview,
            })

        status_stats = {
            'pending': pending_count,
            'processing': processing_count,
            'paid': paid_count,
            'shipped': shipped_count,
            'delivered': completed_count,
            'canceled': canceled_count,
        }

        context = {
            'orders': json.dumps(orders_data, cls=DjangoJSONEncoder),
            'total_orders': total_orders,
            'pending_count': pending_count,
            'processing_count': processing_count,
            'completed_count': completed_count,
            'canceled_count': canceled_count,
            'today_revenue': int(today_revenue),
            'today_revenue_display': f"{int(today_revenue):,}",
            'status_stats': json.dumps(status_stats, cls=DjangoJSONEncoder),
            'search_query': search_query,
            'status_filter': status_filter,
            'price_filter': price_filter,
        }

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'orders': orders_data,
                'total_orders': total_orders,
                'pending_count': pending_count,
                'completed_count': completed_count,
                'today_revenue': int(today_revenue),
            }, safe=False)

        return render(request, self.template_name, context)

    def post(self, request):
        if not (request.user.is_superuser or request.user.is_staff):
            return JsonResponse({'success': False, 'message': 'دسترسی غیرمجاز'}, status=403)

        try:
            data = json.loads(request.body)
            order = Order.objects.get(orderCode=data.get('order_id'))
            order.status = data.get('status')
            order.save()
            return JsonResponse({
                'success': True,
                'message': 'وضعیت سفارش با موفقیت بروزرسانی شد',
                'status_display': order.get_status_display()
            })
        except Order.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'سفارش یافت نشد'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)


class OrderDetailView(AdminRequiredMixin, LoginRequiredMixin, View):
    """
    ویو نمایش جزئیات کامل یک سفارش - فقط ادمین‌ها
    """
    template_name = 'order_app/order_detail2.html'
    login_url = '/login/'

    def get(self, request, order_code):
        # ... کد قبلی (همون کدی که کار میکرد)
        order = get_object_or_404(
            Order.objects.select_related('customer', 'address__state', 'address__city'),
            orderCode=order_code
        )

        order_details = OrderDetail.objects.select_related(
            'product', 'brand'
        ).filter(order=order)

        products_list = []
        for detail in order_details:
            products_list.append({
                'product_id': detail.product.id,
                'product_name': detail.product.title,
                'brand_name': detail.brand.title if detail.brand else '-',
                'quantity': detail.qty,
                'unit_price': detail.price,
                'unit_price_display': f"{detail.price:,}",
                'total_price': detail.getTotalPrice(),
                'total_price_display': f"{detail.getTotalPrice():,}",
                'selected_options': detail.selectedOptions or '-',
                'product_image': detail.product.mainImage.url if detail.product.mainImage else None,
            })

        address_info = {}
        if order.address:
            address_info = {
                'state': order.address.state.name,
                'city': order.address.city.name,
                'detail': order.address.addressDetail,
                'postal_code': order.address.postalCode or '-',
                'lat': str(order.address.lat) if order.address.lat else '-',
                'lng': str(order.address.lng) if order.address.lng else '-',
            }

        subtotal = order.getTotalPrice()
        discount_amount = (subtotal * order.discount) // 100 if order.discount else 0
        final_price = order.get_order_total_price() / 10

        context = {
            'order': order,
            'order_code': str(order.orderCode),
            'order_code_display': str(order.orderCode),
            'status_display': order.get_status_display(),
            'register_date_jalali': order.get_jalali_register_datetime(),
            'register_time': order.get_jalali_register_time(),
            'update_date_jalali': order.get_jalali_update_datetime(),
            'customer_name': str(order.customer.family) or order.customer.mobileNumber,
            'customer_mobile': order.customer.mobileNumber,
            'customer_mobile_display': f"{order.customer.mobileNumber[:4]}****{order.customer.mobileNumber[-4:]}",
            'customer_email': order.customer.email or '-',
            'customer_gender': 'مرد' if order.customer.gender == 'M' else 'زن',
            'customer_birth_date': order.customer.birth_date.strftime('%Y/%m/%d') if order.customer.birth_date else '-',
            'products': products_list,
            'address': address_info,
            'subtotal': subtotal,
            'subtotal_display': f"{subtotal:,}",
            'discount_percent': order.discount,
            'discount_amount': discount_amount,
            'discount_amount_display': f"{discount_amount:,}",
            'final_price': final_price,
            'final_price_display': f"{int(final_price):,}",
            'description': order.description or '-',
            'is_finally': order.isFinally,
            'STATUS_CHOICES': Order.STATUS_CHOICES,
        }

        return render(request, self.template_name, context)

    def post(self, request, order_code):
        if not (request.user.is_superuser or request.user.is_staff):
            return redirect('main:index')

        order = get_object_or_404(Order, orderCode=order_code)
        new_status = request.POST.get('status')

        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()

        return self.get(request, order_code)