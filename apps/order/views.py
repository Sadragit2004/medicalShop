from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json
from apps.product.models import Product
from django.shortcuts import get_object_or_404, redirect, render
from .shop_cart import ShopCart
from .models import Order, OrderDetail, State, City
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import UserAddress
import logging

logger = logging.getLogger(__name__)


# ==================== Helper Functions ====================

def render_checkout_page(request, order, checkout_data=None):
    """
    Helper function to render checkout page with all necessary context
    """
    try:
        # Ensure checkout_data is always a dictionary
        if checkout_data is None:
            checkout_data = {}

        # Get user addresses
        user_addresses = UserAddress.objects.filter(user=request.user)

        # Calculate order totals
        order_items = order.details.all()
        total_items = order_items.count()
        total_qty = sum(item.qty for item in order_items)

        # Calculate subtotal (sum of all items without discount)
        subtotal = sum(item.price * item.qty for item in order_items)

        # Calculate discount amount (applied to subtotal)
        discount_amount = (subtotal * order.discount) // 100 if order.discount else 0

        # Calculate final total
        final_total = subtotal - discount_amount

        # Prepare context
        context = {
            'order': order,
            'order_items': order_items,
            'user_addresses': user_addresses,
            'checkout_data': checkout_data,

            # Order summary
            'total_items': total_items,
            'total_qty': total_qty,
            'subtotal': subtotal,
            'discount_percent': order.discount,
            'discount_amount': discount_amount,
            'final_total': final_total,

            # For template
            'now': timezone.now(),
            'states': State.objects.all().order_by('name'),
        }

        return render(request, 'order_app/checkout.html', context)

    except Exception as e:
        logger.error(f"Error in render_checkout_page: {str(e)}", exc_info=True)
        messages.error(request, "خطا در نمایش صفحه تسویه حساب")
        return redirect('order:cart_page')


# ==================== Cart Views ====================

@require_GET
def cart_summary(request):
    """نمایش خلاصه سبد خرید"""
    try:
        cart = ShopCart(request)

        return JsonResponse({
            'success': True,
            'cart_count': cart.count,
            'total_price': cart.calc_total_price(),
            'items': cart.get_cart_items()
        })
    except Exception as e:
        logger.error(f"Error in cart_summary: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


def cart_page(request):
    """صفحه نمایش سبد خرید"""
    try:
        shop_cart = ShopCart(request)
        cart_items = shop_cart.get_cart_items()
        total_price = shop_cart.calc_total_price()

        context = {
            'cart_items': cart_items,
            'total_price': total_price,
            'cart_count': shop_cart.count
        }

        return render(request, 'order_app/cart_page.html', context)

    except Exception as e:
        logger.error(f"Error in cart_page: {str(e)}")
        messages.error(request, "خطا در نمایش سبد خرید")
        return redirect('main:index')


@require_POST
@csrf_exempt
def add_to_cart(request):
    """افزودن محصول به سبد خرید"""
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))
        sale_type_id = data.get('sale_type', 1)
        detail = data.get('detail', '')

        product = get_object_or_404(Product, id=product_id)
        cart = ShopCart(request)
        cart.add_to_shop_cart(product, quantity, detail, sale_type_id)

        return JsonResponse({
            'success': True,
            'cart_count': cart.count,
            'total_price': cart.calc_total_price(),
            'items': cart.get_cart_items(),
            'message': 'محصول به سبد خرید اضافه شد'
        })

    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'محصول یافت نشد'
        })
    except Exception as e:
        logger.error(f"Error in add_to_cart: {str(e)}")
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
            'items': cart.get_cart_items(),
            'message': 'محصول از سبد خرید حذف شد'
        })

    except Exception as e:
        logger.error(f"Error in remove_from_cart: {str(e)}")
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
                'items': cart.get_cart_items(),
                'message': 'تعداد محصول به‌روزرسانی شد'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'محصول در سبد خرید یافت نشد'
            })

    except Exception as e:
        logger.error(f"Error in update_cart_quantity: {str(e)}")
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
        logger.error(f"Error in clear_cart: {str(e)}")
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
        logger.error(f"Error in get_cart_count: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


# ==================== Order Views ====================

class CreateOrderView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            shop_cart = ShopCart(request)

            # بررسی اینکه سبد خرید خالی نباشد
            if shop_cart.count == 0:
                messages.error(request, "سبد خرید شما خالی است.", "danger")
                return redirect("main:index")

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
            return redirect('order:checkout', order.id)

        except Exception as e:
            logger.error(f"Error in CreateOrderView: {str(e)}", exc_info=True)
            messages.error(
                request,
                f"خطا در ایجاد سفارش: {str(e)}",
                "danger"
            )
            return redirect("main:index")


@login_required
def order_invoice(request, order_id):
    """View for displaying order invoice"""
    try:
        order = get_object_or_404(Order, id=order_id, customer=request.user)

        # Calculate order totals (same logic as checkout)
        order_items = order.details.all()
        total_items = order_items.count()
        total_qty = sum(item.qty for item in order_items)

        # Calculate subtotal (sum of all items without discount)
        subtotal = sum(item.price * item.qty for item in order_items)

        # Calculate discount amount (applied to subtotal)
        discount_amount = (subtotal * order.discount) // 100 if order.discount else 0

        # Calculate final total
        final_total = subtotal - discount_amount

        context = {
            'order': order,
            'order_items': order_items,
            'total_items': total_items,
            'total_qty': total_qty,
            'subtotal': subtotal,
            'discount_percent': order.discount,
            'discount_amount': discount_amount,
            'final_total': final_total,
        }

        return render(request, 'order_app/invoice.html', context)

    except Exception as e:
        logger.error(f"Error in order_invoice: {str(e)}", exc_info=True)
        messages.error(request, "خطا در نمایش فاکتور")
        return redirect('order:cart_page')


from django.urls import reverse
@login_required
def checkout(request, order_id):
    """Checkout page for order confirmation"""
    try:
        order = get_object_or_404(Order, id=order_id, customer=request.user, isFinally=False)

        if request.method == 'POST':
            action = request.POST.get('action')
            is_payment = request.POST.get('is_payment')
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

            # دریافت و تریم فیلدها
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            phone = request.POST.get('phone', '').strip()
            description = request.POST.get('description', '').strip()
            selected_address_id = request.POST.get('selected_address')

            checkout_data = {
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone,
                'selected_address_id': selected_address_id,
                'description': description,
            }

            # اعتبارسنجی فیلدهای ضروری
            validation_errors = []

            if not first_name:
                validation_errors.append('نام')
            if not last_name:
                validation_errors.append('نام‌خانوادگی')
            if not phone:
                validation_errors.append('تلفن')
            if not selected_address_id:
                validation_errors.append('آدرس')

            if validation_errors:
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'error': f"لطفاً موارد زیر را کامل کنید: {', '.join(validation_errors)}"
                    })
                messages.error(request, f"لطفاً موارد زیر را کامل کنید: {', '.join(validation_errors)}")
                return render_checkout_page(request, order, checkout_data)

            # بررسی وجود آدرس انتخاب شده
            try:
                selected_address = UserAddress.objects.get(id=selected_address_id, user=request.user)
            except UserAddress.DoesNotExist:
                if is_ajax:
                    return JsonResponse({'success': False, 'error': 'آدرس انتخاب شده نامعتبر است.'})
                messages.error(request, "آدرس انتخاب شده نامعتبر است.")
                return render_checkout_page(request, order, checkout_data)

            # ذخیره نام و نام‌خانوادگی در پروفایل کاربر
            if first_name:
                request.user.name = first_name
            if last_name:
                request.user.family = last_name
            request.user.save()

            # ذخیره اطلاعات در سفارش
            order.address = selected_address
            order.description = description
            order.save()

            # ذخیره در session
            request.session['checkout_data'] = checkout_data

            # اگر درخواست پرداخت مستقیم است
            if is_payment == 'true' or action == 'pay':
                order.isFinally = True
                order.save()

                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'redirect_url': reverse('peyment:request', args=[order.id])
                    })
                return redirect('peyment:request', order_id=order.id)

            # اگر فقط ذخیره اطلاعات بوده
            if is_ajax:
                return JsonResponse({'success': True, 'message': 'اطلاعات با موفقیت ذخیره شد'})

            messages.success(request, "اطلاعات سفارش با موفقیت ذخیره شد.")
            return redirect('order:checkout', order_id=order.id)

        # GET Request - نمایش صفحه
        checkout_data = request.session.get('checkout_data', {})
        return render_checkout_page(request, order, checkout_data)

    except Exception as e:
        logger.error(f"Error in checkout view: {str(e)}", exc_info=True)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)})
        messages.error(request, "خطا در صفحه تسویه حساب")
        return redirect('order:cart_page')

# ==================== Address API Views ====================

@require_GET
@login_required
def get_cities_by_state(request, state_id):
    """دریافت شهرهای یک استان"""
    try:
        cities = City.objects.filter(state_id=state_id).order_by('name')
        cities_data = [{'id': city.id, 'name': city.name} for city in cities]

        return JsonResponse({
            'success': True,
            'cities': cities_data
        })
    except Exception as e:
        logger.error(f"Error in get_cities_by_state: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_POST
@login_required
@csrf_exempt
def create_user_address(request):
    try:
        # چاپ برای دیباگ
        print("POST data:", request.POST)

        state_id = request.POST.get('state')
        city_id = request.POST.get('city')
        address_detail = request.POST.get('address_detail', '').strip()
        postal_code = request.POST.get('postal_code', '').strip()

        # Validation
        if not all([state_id, city_id, address_detail]):
            return JsonResponse({
                'success': False,
                'error': 'لطفاً تمام فیلدهای ضروری را پر کنید'
            })

        # تبدیل به int
        try:
            state_id = int(state_id)
            city_id = int(city_id)
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'شناسه استان یا شهر نامعتبر است'
            })

        # Verify state and city
        try:
            state = State.objects.get(id=state_id)
            city = City.objects.get(id=city_id, state=state)
        except State.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'استان انتخاب شده نامعتبر است'
            })
        except City.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'شهر انتخاب شده نامعتبر است'
            })

        # Create address
        address = UserAddress.objects.create(
            user=request.user,
            state=state,
            city=city,
            addressDetail=address_detail,
            postalCode=postal_code if postal_code else None
        )

        return JsonResponse({
            'success': True,
            'address_id': address.id,  # مهم: این اسم باید با جاوااسکریپت هماهنگ باشه
            'state_name': state.name,
            'city_name': city.name,
            'address_detail': address_detail,
            'postal_code': postal_code,
            'message': 'آدرس با موفقیت اضافه شد'
        })

    except Exception as e:
        print(f"Error in create_user_address: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })




# اضافه کردن این API ها به فایل views.py در اپ order
@login_required
@csrf_exempt
def ajax_save_checkout_info(request):
    """ذخیره خودکار اطلاعات هنگام خروج از فیلدها"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'روش غیرمجاز'})

    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        field_name = data.get('field_name')
        field_value = str(data.get('field_value', '')).strip()

        order = get_object_or_404(Order, id=order_id, customer=request.user)

        # ذخیره در session
        checkout_data = request.session.get('checkout_data', {})

        if field_name == 'first_name':
            checkout_data['first_name'] = field_value
            request.user.name = field_value
            request.user.save()

        elif field_name == 'last_name':
            checkout_data['last_name'] = field_value
            request.user.family = field_value
            request.user.save()

        elif field_name == 'phone':
            checkout_data['phone'] = field_value

        elif field_name == 'description':
            checkout_data['description'] = field_value

        elif field_name == 'selected_address':
            # ** مهم: اگر مقدار خالی بود، ذخیره نکن **
            if field_value and field_value != '':
                checkout_data['selected_address_id'] = field_value
                try:
                    address = UserAddress.objects.get(id=int(field_value), user=request.user)
                    order.address = address
                    order.save()
                except (UserAddress.DoesNotExist, ValueError):
                    pass  # اگر آدرس وجود نداشت، هیچ کاری نکن

        request.session['checkout_data'] = checkout_data

        return JsonResponse({
            'success': True,
            'message': 'اطلاعات با موفقیت ذخیره شد'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'فرمت داده نامعتبر است'
        })
    except Order.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'سفارش یافت نشد'
        })
    except Exception as e:
        logger.error(f"Error in ajax_save_checkout_info: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_POST
@csrf_exempt
def ajax_save_all_info(request):
    """ذخیره تمام اطلاعات یکجا (قبل از پرداخت)"""
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        phone = data.get('phone', '').strip()
        description = data.get('description', '').strip()
        selected_address_id = data.get('selected_address_id', '').strip()

        order = get_object_or_404(Order, id=order_id, customer=request.user, isFinally=False)

        # اعتبارسنجی
        errors = []
        if not first_name:
            errors.append('نام')
        if not last_name:
            errors.append('نام خانوادگی')
        if not phone:
            errors.append('تلفن')
        if not selected_address_id:
            errors.append('آدرس')

        if errors:
            return JsonResponse({
                'success': False,
                'error': f'لطفاً موارد زیر را کامل کنید: {", ".join(errors)}'
            })

        # ذخیره در پروفایل کاربر
        request.user.name = first_name
        request.user.family = last_name
        request.user.save()

        # ذخیره در session
        checkout_data = {
            'first_name': first_name,
            'last_name': last_name,
            'phone': phone,
            'description': description,
            'selected_address_id': selected_address_id
        }
        request.session['checkout_data'] = checkout_data

        # ذخیره آدرس در سفارش
        try:
            address = UserAddress.objects.get(id=selected_address_id, user=request.user)
            order.address = address
            order.save()
        except UserAddress.DoesNotExist:
            pass

        # نهایی کردن سفارش
        order.isFinally = True
        order.save()

        return JsonResponse({
            'success': True,
            'redirect_url': reverse('peyment:request', args=[order.id])
        })

    except Exception as e:
        logger.error(f"Error in ajax_save_all_info: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })