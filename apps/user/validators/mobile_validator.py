import re
from django.core.exceptions import ValidationError


def validate_iranian_mobile(value):
    """
    اعتبارسنجی شماره موبایل ایرانی
    فرمت: 09XXXXXXXXX
    """
    if not re.fullmatch(r"09\d{9}", value):
        raise ValidationError("شماره موبایل معتبر نیست. باید با 09 شروع شود و 11 رقم باشد.")
