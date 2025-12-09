import random
from datetime import datetime, timedelta

def generate_activation_code(length=6):
    """
    تولید کد فعال‌سازی عددی
    """
    return "".join([str(random.randint(0, 9)) for _ in range(length)])

def generate_expiration_time(minutes=10):
    """
    تولید زمان انقضای کد (پیش‌فرض ۱۰ دقیقه از زمان حال)
    """
    return datetime.now() + timedelta(minutes=minutes)

def validate_numeric(value):
    """
    اعتبارسنجی رشته فقط شامل عدد
    """
    if not str(value).isdigit():
        raise ValueError("فقط مقادیر عددی معتبر هستند")
