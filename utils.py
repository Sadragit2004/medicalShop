import logging
logger = logging.getLogger(__name__)
from django.utils import timezone
from django.http import HttpResponseForbidden
from datetime import timedelta
import random
import web.settings as settings
import os
from uuid import uuid4
from functools import wraps


import socket

def has_internet_connection():
    """
    Check if the device has an active internet connection.

    Returns:
        bool: True if the device has an active internet connection, False otherwise.
    """
    try:
        # Try to connect to a well-known website
        socket.create_connection(("www.google.com", 80))
        return True
    except OSError:
        pass

    try:
        # Try to connect to a different well-known website
        socket.create_connection(("www.example.com", 80))
        return True
    except OSError:
        pass

    return False

def create_random_code(num):
    import random
    num-=1
    return random.randint(10**num,10**(num+1)-1)



class FileUpload:


    def __init__(self,dir,prefix):
        self.dir = dir
        self.prefix = prefix



    def upload_to(self,instance,filename):
        filename,ext=os.path.splitext(filename)
        return f'{self.dir}/{self.prefix}/{uuid4()}{filename}{ext}'





def rate_limit_ip(max_requests, time_frame_seconds=None, time_frame_minutes=None, time_frame_hours=None):


    def decorator(view_func):

        from apps.user.models.loguser_model import BlockedIP,RequestLog

        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # محاسبه کل زمان بر حسب ثانیه
            total_seconds = 0
            if time_frame_seconds:
                total_seconds += time_frame_seconds
            if time_frame_minutes:
                total_seconds += time_frame_minutes * 60
            if time_frame_hours:
                total_seconds += time_frame_hours * 3600

            if not total_seconds:
                total_seconds = 3600  # مقدار پیش‌فرض: 1 ساعت

            # دریافت IP کاربر
            ip = get_client_ip(request)

            # بررسی وجود IP در لیست بلاک‌شده‌های فعال
            blocked_ip = BlockedIP.objects.filter(
                ip_address=ip,
                is_active=True
            ).first()

            if blocked_ip:
                # بررسی انقضای بلاک
                if blocked_ip.is_block_expired():
                    blocked_ip.is_active = False
                    blocked_ip.save()
                else:
                    return HttpResponseForbidden(
                        f'دسترسی شما به این سرویس موقتاً محدود شده است. دلیل: {blocked_ip.reason}'
                    )

            # ساخت کلید برای لاگ درخواست‌ها
            request_log_key = f'request_log_{ip}'
            request_log = RequestLog.objects.filter(ip_address=ip).order_by('-timestamp')

            # محاسبه درخواست‌های اخیر
            time_threshold = timezone.now() - timedelta(seconds=total_seconds)
            recent_requests = request_log.filter(timestamp__gte=time_threshold).count()

            # ذخیره لاگ درخواست فعلی
            RequestLog.objects.create(ip_address=ip)

            # بررسی تعداد درخواست‌ها
            if recent_requests >= max_requests:
                # بلاک کردن IP
                BlockedIP.objects.create(
                    ip_address=ip,
                    max_requests=max_requests,
                    time_frame_seconds=total_seconds,
                    requests_count=recent_requests,
                    reason=f'تعداد درخواست‌ها بیش از حد مجاز ({max_requests} درخواست در {total_seconds} ثانیه)'
                )
                return HttpResponseForbidden(
                    f'تعداد درخواست‌های شما بیش از حد مجاز است. IP شما برای {total_seconds} ثانیه بلاک شد.'
                )

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def get_client_ip(request):
    """
    دریافت IP واقعی کاربر با در نظر گرفتن X-Forwarded-For
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip



from decimal import Decimal

def price_by_delivery_tax(price, discount=0):
    # تبدیل قیمت به Decimal برای دقت بیشتر
    price_decimal = Decimal(str(price))

    tax = price_decimal * Decimal('0.09')
    total_sum = price_decimal + tax
    total_sum = total_sum - (total_sum * Decimal(str(discount)) / Decimal('100'))

    return int(total_sum), int(tax)







from sms_ir import SmsIr
def send_sms(number,code):

    pass
    sms_ir = SmsIr('aOdP7bVrffnd5D56iRlaYbtKs6Cm4zIcsaxhoe3aQXLT04u8')

    result = sms_ir.send_verify_code(
        number=str(number),
        template_id=143712,
        parameters=[
            {

                "name" : "CODE",
                "value": str(code)

            }
        ],
    )