# views.py
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
import json
from apps.product.models import Product
from django.shortcuts import get_object_or_404,redirect,render
from .shop_cart import ShopCart
from .models import Order,OrderDetail
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import UserAddress

@require_GET
def cart_summary(request):
    """نمایش خلاصه سبد خرید"""
    cart = ShopCart(request)

    return JsonResponse({
        'success': True,
        'cart_count': cart.count,
        'total_price': cart.calc_total_price(),
        'items': cart.get_cart_items()  # استفاده از متد جدید
    })


@login_required
def cart_page(request):
    """صفحه نمایش سبد خرید"""
    shop_cart = ShopCart(request)
    cart_items = shop_cart.get_cart_items()
    total_price = shop_cart.calc_total_price()

    context = {
        'cart_items': cart_items,
        'total_price': total_price,
        'cart_count': shop_cart.count
    }

    return render(request, 'order_app/cart_page.html', context)


@require_POST
@csrf_exempt
def add_to_cart(request):
    """افزودن محصول به سبد خرید"""
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))
        sale_type_id = data.get('sale_type', 1)  # Get sale type from request
        detail = data.get('detail', '')

        product = get_object_or_404(Product, id=product_id)
        cart = ShopCart(request)
        cart.add_to_shop_cart(product, quantity, detail, sale_type_id)

        return JsonResponse({
            'success': True,
            'cart_count': cart.count,
            'total_price': cart.calc_total_price(),
            'items': cart.get_cart_items(),  # استفاده از متد جدید
            'message': 'محصول به سبد خرید اضافه شد'
        })

    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'محصول یافت نشد'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@require_POST
@csrf_exempt
def remove_from_cart(request):
    """حذف محصول از سبد خرید"""
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        detail = data.get('detail', '')
        sale_type_id = data.get('sale_type')

        # Convert sale_type_id to int if it's not None
        if sale_type_id is not None:
            try:
                sale_type_id = int(sale_type_id)
            except (ValueError, TypeError):
                sale_type_id = 1

        product = get_object_or_404(Product, id=product_id)
        cart = ShopCart(request)
        cart.delete_from_shop_cart(product, detail, sale_type_id)

        return JsonResponse({
            'success': True,
            'cart_count': cart.count,
            'total_price': cart.calc_total_price(),
            'items': cart.get_cart_items(),  # استفاده از متد جدید
            'message': 'محصول از سبد خرید حذف شد'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@require_POST
@csrf_exempt
def update_cart_quantity(request):
    """به‌روزرسانی تعداد محصول در سبد خرید"""
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))
        detail = data.get('detail', '')
        sale_type_id = data.get('sale_type')

        # Convert sale_type_id to int if it's not None
        if sale_type_id is not None:
            try:
                sale_type_id = int(sale_type_id)
            except (ValueError, TypeError):
                sale_type_id = 1

        product = get_object_or_404(Product, id=product_id)
        cart = ShopCart(request)

        # پیدا کردن کلید محصول در سبد خرید (با احتساب نوع فروش)
        actual_sale_type = sale_type_id or 1
        key = cart._get_key(product_id, detail, actual_sale_type)

        if key in cart.shop_cart:
            if quantity <= 0:
                cart.delete_from_shop_cart(product, detail, actual_sale_type)
            else:
                cart.shop_cart[key]['qty'] = quantity
                cart.session.modified = True

            return JsonResponse({
                'success': True,
                'cart_count': cart.count,
                'total_price': cart.calc_total_price(),
                'items': cart.get_cart_items(),  # استفاده از متد جدید
                'message': 'تعداد محصول به‌روزرسانی شد'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'محصول در سبد خرید یافت نشد'
            })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@require_POST
@csrf_exempt
def clear_cart(request):
    """پاک کردن کامل سبد خرید"""
    try:
        cart = ShopCart(request)
        cart.delete_all_list()

        return JsonResponse({
            'success': True,
            'cart_count': 0,
            'total_price': 0,
            'items': [],
            'message': 'سبد خرید پاک شد'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@require_GET
def get_cart_count(request):
    """دریافت تعداد محصولات در سبد خرید"""
    try:
        cart = ShopCart(request)
        return JsonResponse({
            'success': True,
            'cart_count': cart.count,
            'total_price': cart.calc_total_price()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })




class CreateOrderView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        shop_cart = ShopCart(request)

        # بررسی اینکه سبد خرید خالی نباشد
        if shop_cart.count == 0:
            messages.error(request, "سبد خرید شما خالی است.", "danger")
            return redirect("main:index")

        try:
            order = Order.objects.create(
                customer=request.user,
                status="pending",
            )

            for item in shop_cart.get_cart_items():
                try:
                    product = Product.objects.get(id=item['id'])

                    OrderDetail.objects.create(
                        order=order,
                        product=product,
                        brand=product.brand,
                        qty=item['quantity'],
                        price=item['price'],
                        selectedOptions=item.get('detail', '')
                    )

                except Product.DoesNotExist:
                    messages.warning(request, f"محصول با شناسه {item['id']} یافت نشد و از سفارش حذف شد.")
                    continue

            # پاک کردن سبد خرید پس از ایجاد سفارش موفق
            shop_cart.delete_all_list()

            messages.success(
                request,
                f"سفارش شما با کد {order.orderCode} با موفقیت ایجاد شد و در انتظار پرداخت است."
            )
            return redirect('order:checkout',order.id)

        except Exception as e:
            messages.error(
                request,
                f"خطا در ایجاد سفارش: {str(e)}",
                "danger"
            )
            return redirect("main:index")



from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

@login_required
def checkout(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    user_addresses = UserAddress.objects.filter(user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        # دریافت و تریم فیلدها
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        postal_code = request.POST.get('postal_code', '').strip()
        address_detail = request.POST.get('address_detail', '').strip()
        description = request.POST.get('description', '').strip()

        # اعتبارسنجی فیلدهای ضروری
        missing = []
        if not first_name: missing.append('نام')
        if not last_name:  missing.append('نام‌خانوادگی')
        if not phone:      missing.append('تلفن')
        if not postal_code:missing.append('کد پستی')
        if not address_detail: missing.append('آدرس دقیق')

        if missing:
            messages.warning(request, "لطفاً موارد زیر را کامل کنید: " + "، ".join(missing), extra_tags='warning')
            return render_checkout_page(request, order, {
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone,
                'postal_code': postal_code,
                'address_detail': address_detail,
                'description': description,
            })

        # بررسی وجود آدرس کاربر
        if not user_addresses.exists():
            messages.warning(request, "شهر/آدرس برای تحویل ثبت نشده است. لطفاً ابتدا یک آدرس انتخاب یا ثبت کنید.", extra_tags='warning')
            return render_checkout_page(request, order, {
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone,
                'postal_code': postal_code,
                'address_detail': address_detail,
                'description': description,
            })

        # ذخیره اطلاعات در session
        request.session['checkout_data'] = {
            'first_name': first_name,
            'last_name': last_name,
            'phone': phone,
            'postal_code': postal_code,
            'address_detail': address_detail,
            'description': description,
        }

        # ذخیره آدرس در مدل Order
        try:
            order.addressDetail = f"{first_name} {last_name} - تلفن: {phone} - کدپستی: {postal_code} - آدرس: {address_detail}" + (f" - توضیحات: {description}" if description else "")
            order.save()
            messages.success(request, "اطلاعات آدرس با موفقیت ذخیره شد.", extra_tags='success')
        except Exception as e:
            messages.error(request, f"خطا در ذخیره اطلاعات آدرس: {str(e)}", extra_tags='error')
            return render_checkout_page(request, order, {
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone,
                'postal_code': postal_code,
                'address_detail': address_detail,
                'description': description,
            })

        # اگر کاربر دکمه پرداخت را زده باشد
        if action == 'pay':
            return redirect('peyment:request', order_id=order.id)

        # اگر فقط ذخیره اطلاعات بوده
        return redirect('order:checkout', order_id=order.id)

    # GET Request
    checkout_data = request.session.get('checkout_data', {})
    return render_checkout_page(request, order, checkout_data)


def render_checkout_page(request, order, checkout_data):
    """تابع کمکی برای رندر کردن صفحه چک‌اوت"""
    tax_rate = 9
    tax_amount = (order.getFinalPrice() * tax_rate) // 100
    final_price_with_tax = order.getFinalPrice() + tax_amount

    context = {
        'order': order,
        'checkout_data': checkout_data,
        'tax_rate': tax_rate,
        'tax_amount': tax_amount,
        'final_price_with_tax': final_price_with_tax,
    }
    return render(request, 'order_app/checkout.html', context)