from django.utils import timezone

def validate_activation_code(security_obj, code):
    """
    بررسی صحت کد فعال‌سازی برای یک کاربر
    - کد باید برابر با activeCode باشد
    - کد نباید منقضی شده باشد
    """
    if not security_obj.activeCode or security_obj.activeCode != code:
        return False

    if not security_obj.expireCode or security_obj.expireCode < timezone.now():
        return False

    return True
