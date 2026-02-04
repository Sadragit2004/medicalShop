from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import login
from django.contrib import messages
from ..models.user import CustomUser
from ..models.security import UserSecurity
from ..validators.common import generate_activation_code
from ..validators.code_validator import validate_activation_code
import utils

class AuthService:
    @staticmethod
    def get_or_create_user(mobile):
        """
        بررسی وجود کاربر یا ساخت کاربر جدید
        """
        user, created = CustomUser.objects.get_or_create(mobileNumber=mobile)
        if created:
            user.is_active = False
            user.save()
        return user

    @staticmethod
    def get_or_create_security(user):
        """
        گرفتن یا ایجاد UserSecurity
        """
        security, created = UserSecurity.objects.get_or_create(user=user)
        return security

    @staticmethod
    def send_activation_code(security,mobile='',code_length=5, expire_minutes=2,):
        """
        تولید و ذخیره کد فعال‌سازی
        """
        code = generate_activation_code(code_length)
        expire_time = timezone.now() + timedelta(minutes=expire_minutes)
        security.activeCode = code
        utils.send_sms(mobile, code)
        security.expireCode = expire_time
        security.isBan = False
        security.save()

        return code

    @staticmethod
    def verify_code(security, code):
        """
        بررسی صحت و انقضای کد
        """
        if security.expireCode < timezone.now():
            raise ValueError(" کد منقضی شده است.")
        if not validate_activation_code(security, code):
            raise ValueError(" کد واردشده معتبر نیست")
        # پاکسازی کد بعد از موفقیت
        security.activeCode = None
        security.expireCode = None
        security.save()
        return True

    @staticmethod
    def activate_user(user):
        user.is_active = True
        user.save()
