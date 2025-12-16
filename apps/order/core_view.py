# order/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from .models import State, City, UserAddress
import json

@login_required
@require_POST
@csrf_exempt
def save_user_location(request):
    """
    ذخیره استان و شهر انتخاب شده توسط کاربر
    """
    try:
        data = json.loads(request.body)
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

        # ایجاد یا آپدیت رکورد شهر - با منطق بهبود یافته
        try:
            # ابتدا سعی می‌کنیم شهر را با externalId و state پیدا کنیم
            city = City.objects.get(externalId=city_id, state=state)
            # اگر پیدا شد و نام تغییر کرده، آپدیت می‌کنیم
            if city.name != city_name:
                city.name = city_name
                city.save()
        except City.DoesNotExist:
            try:
                # اگر پیدا نشد، شهر جدید ایجاد می‌کنیم
                city = City.objects.create(
                    externalId=city_id,
                    state=state,
                    name=city_name
                )
            except IntegrityError:
                # اگر خطای تکراری داد، یعنی externalId تکراری است
                # در این حالت سعی می‌کنیم شهر را فقط با externalId پیدا کنیم
                city = City.objects.get(externalId=city_id)
                # اطمینان حاصل می‌کنیم که state درست باشد
                if city.state != state:
                    city.state = state
                if city.name != city_name:
                    city.name = city_name
                city.save()

        # ایجاد یا آپدیت آدرس کاربر
        user_address, created = UserAddress.objects.update_or_create(
            user=request.user,
            defaults={
                'state': state,
                'city': city,
                'addressDetail': f'موقعیت اصلی کاربر - {city.name}، {state.name}',
            }
        )

        # ذخیره در سشن
        request.session['user_location'] = {
            'state_id': state.id,
            'state_name': state.name,
            'city_id': city.id,
            'city_name': city.name,
            'full_address': f'{city.name}، {state.name}'
        }

        return JsonResponse({
            'success': True,
            'message': 'موقعیت شما با موفقیت ذخیره شد',
            'data': {
                'state': state.name,
                'city': city.name,
                'full_address': f'{city.name}، {state.name}'
            }
        })

    except Exception as e:
        print(f"Error in save_user_location: {e}")
        return JsonResponse({
            'success': False,
            'error': f'خطا در ذخیره موقعیت: {str(e)}'
        })

@login_required
def get_user_location(request):
    """دریافت موقعیت فعلی کاربر"""
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
        print(f"Error in get_user_location: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })