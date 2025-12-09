import re
import random
from datetime import timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError

# 📱 اعتبارسنجی شماره موبایل ایرانی
def validate_iranian_mobile(value):
    if not re.fullmatch(r"^09\d{9}$", value):
        raise ValidationError("شماره موبایل معتبر نیست. باید با 09 شروع شود و 11 رقم باشد.")

# 🔢 فقط عدد بودن مقدار
def validate_numeric(value):
    if not str(value).isdigit():
        raise ValidationError("فقط اعداد مجاز هستند.")

# 🔒 تولید کد فعال‌سازی تصادفی
def generate_activation_code(length=6):
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])

# ⏳ تولید زمان انقضا - استفاده از timezone.now() به جای datetime.now()
def generate_expiration_time(minutes=5):
    return timezone.now() + timedelta(minutes=minutes)

# ✅ بررسی صحت کد فعال‌سازی - استفاده از timezone.now() به جای datetime.now()
def validate_activation_code(user_security, code):
    if not user_security.activeCode:
        raise ValidationError("کد فعال‌سازی برای این کاربر وجود ندارد.")
    if user_security.activeCode != str(code):
        raise ValidationError("کد فعال‌سازی اشتباه است.")
    if user_security.expireCode < timezone.now():
        raise ValidationError("زمان اعتبار کد فعال‌سازی به پایان رسیده است.")
    return True