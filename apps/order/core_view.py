from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from .models import State, City, UserAddress, Order
import json
from decimal import Decimal

@login_required
@require_GET
def get_cities_by_state(request, state_id):
    """
    دریافت شهرهای یک استان (API)
    """
    try:
        state = State.objects.get(id=state_id)
        cities = state.cities.all().values('id', 'name')
        return JsonResponse({
            'success': True,
            'cities': list(cities)
        })
    except State.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'استان مورد نظر یافت نشد'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_POST
@csrf_exempt
def create_user_address(request):
    """
    ایجاد آدرس جدید برای کاربر (API)
    """
    try:
        # پشتیبانی از هر دو نوع داده (JSON و FormData)
        if request.content_type and 'application/json' in request.content_type:
            data = json.loads(request.body)
            state_id = data.get('state')
            city_id = data.get('city')
            address_detail = data.get('address_detail')
            postal_code = data.get('postal_code', '')
        else:
            state_id = request.POST.get('state')
            city_id = request.POST.get('city')
            address_detail = request.POST.get('address_detail')
            postal_code = request.POST.get('postal_code', '')

        # اعتبارسنجی
        if not state_id:
            return JsonResponse({
                'success': False,
                'error': 'لطفاً استان را انتخاب کنید'
            })

        if not city_id:
            return JsonResponse({
                'success': False,
                'error': 'لطفاً شهر را انتخاب کنید'
            })

        if not address_detail:
            return JsonResponse({
                'success': False,
                'error': 'لطفاً آدرس کامل را وارد کنید'
            })

        # دریافت استان و شهر
        try:
            state = State.objects.get(id=state_id)
            city = City.objects.get(id=city_id, state=state)
        except State.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'استان انتخاب شده معتبر نیست'
            })
        except City.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'شهر انتخاب شده معتبر نیست'
            })

        # ایجاد آدرس جدید
        user_address = UserAddress.objects.create(
            user=request.user,
            state=state,
            city=city,
            addressDetail=address_detail,
            postalCode=postal_code if postal_code else ''
        )

        # برگرداندن اطلاعات آدرس جدید
        return JsonResponse({
            'success': True,
            'message': 'آدرس با موفقیت اضافه شد',
            'address_id': user_address.id,
            'state_name': state.name,
            'city_name': city.name,
            'address_detail': address_detail,
            'postal_code': postal_code
        })

    except Exception as e:
        print(f"Error in create_user_address: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'خطا در ذخیره آدرس: {str(e)}'
        })


@login_required
@csrf_exempt
def ajax_save_checkout_info(request):
    """
    ذخیره اطلاعات تسویه حساب به صورت AJAX (API)
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'روش غیرمجاز'})

    try:
        # پشتیبانی از JSON
        if request.content_type and 'application/json' in request.content_type:
            data = json.loads(request.body)
        else:
            data = request.POST.dict()

        order_id = data.get('order_id')
        field_name = data.get('field_name')
        field_value = data.get('field_value')

        if not order_id or not field_name:
            return JsonResponse({
                'success': False,
                'error': 'پارامترهای ناقص'
            })

        # دریافت سفارش
        try:
            order = Order.objects.get(id=order_id, customer=request.user)
        except Order.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'سفارش یافت نشد'
            })

        # ذخیره فیلد مربوطه
        if field_name == 'first_name':
            request.user.name = field_value
            request.user.save()
        elif field_name == 'last_name':
            request.user.family = field_value
            request.user.save()
        elif field_name == 'phone':
            # اعتبارسنجی ساده تلفن
            if field_value and len(field_value) > 0:
                if not field_value.isdigit():
                    return JsonResponse({
                        'success': False,
                        'error': 'شماره تلفن باید فقط شامل اعداد باشد'
                    })
                if not field_value.startswith('0'):
                    return JsonResponse({
                        'success': False,
                        'error': 'شماره تلفن باید با 0 شروع شود'
                    })
            # ذخیره در session
            request.session['checkout_phone'] = field_value
        elif field_name == 'description':
            order.description = field_value
            order.save()
        elif field_name == 'selected_address':
            if field_value and field_value != 'null' and field_value != '':
                try:
                    address = UserAddress.objects.get(id=field_value, user=request.user)
                    order.address = address
                    order.save()
                except UserAddress.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'error': 'آدرس انتخاب شده معتبر نیست'
                    })

        return JsonResponse({'success': True})

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'فرمت داده نامعتبر است'
        })
    except Exception as e:
        print(f"Error in ajax_save_checkout_info: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_POST
@csrf_exempt
def save_user_location(request):
    """
    ذخیره موقعیت مکانی کاربر (API)
    """
    try:
        if request.content_type and 'application/json' in request.content_type:
            data = json.loads(request.body)
        else:
            data = request.POST.dict()

        state_id = data.get('state_id')
        city_id = data.get('city_id')
        state_name = data.get('state_name')
        city_name = data.get('city_name')

        if not all([state_id, city_id, state_name, city_name]):
            return JsonResponse({
                'success': False,
                'error': 'تمام اطلاعات استان و شهر الزامی است'
            })

        # ایجاد یا آپدیت رکورد استان
        state, state_created = State.objects.get_or_create(
            externalId=state_id,
            defaults={
                'name': state_name,
                'center': state_name,
            }
        )

        # ایجاد یا آپدیت رکورد شهر
        try:
            city = City.objects.get(externalId=city_id, state=state)
            if city.name != city_name:
                city.name = city_name
                city.save()
        except City.DoesNotExist:
            city = City.objects.create(
                externalId=city_id,
                state=state,
                name=city_name
            )

        # ایجاد یا آپدیت آدرس کاربر
        user_address, created = UserAddress.objects.update_or_create(
            user=request.user,
            defaults={
                'state': state,
                'city': city,
                'addressDetail': f'موقعیت اصلی کاربر - {city_name}، {state_name}',
            }
        )

        # ذخیره در سشن
        request.session['user_location'] = {
            'state_id': state.id,
            'state_name': state.name,
            'city_id': city.id,
            'city_name': city.name,
            'full_address': f'{city_name}، {state_name}'
        }

        return JsonResponse({
            'success': True,
            'message': 'موقعیت شما با موفقیت ذخیره شد',
            'data': {
                'state': state.name,
                'city': city.name,
                'full_address': f'{city_name}، {state_name}'
            }
        })

    except Exception as e:
        print(f"Error in save_user_location: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'خطا در ذخیره موقعیت: {str(e)}'
        })


@login_required
def get_user_location(request):
    """دریافت موقعیت فعلی کاربر (API)"""
    try:
        user_address = UserAddress.objects.filter(user=request.user).first()
        if user_address:
            return JsonResponse({
                'success': True,
                'data': {
                    'state': user_address.state.name,
                    'city': user_address.city.name,
                    'full_address': f'{user_address.city.name}، {user_address.state.name}'
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'موقعیتی ثبت نشده است'
            })
    except Exception as e:
        print(f"Error in get_user_location: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })