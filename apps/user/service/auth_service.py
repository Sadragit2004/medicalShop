# service/auth_service.py
from django.utils import timezone
from datetime import timedelta
from ..models.user import CustomUser
from ..models.security import UserSecurity
from ..validators.common import generate_activation_code
from ..validators.code_validator import validate_activation_code

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
    def send_activation_code(security, code_length=5, expire_minutes=2):
        """
        تولید و ذخیره کد فعال‌سازی
        """
        code = generate_activation_code(code_length)
        expire_time = timezone.now() + timedelta(minutes=expire_minutes)
        security.activeCode = code
        security.expireCode = expire_time
        security.isBan = False
        security.save()
        # TODO: ارسال پیامک واقعی
        print(f"کد فعال‌سازی برای {security.user.mobileNumber}: {code}")
        return code

    @staticmethod
    def verify_code(security, code):
        """
        بررسی صحت و انقضای کد
        """
        if security.expireCode and security.expireCode < timezone.now():
            raise ValueError("⏳ کد منقضی شده است.")
        if not validate_activation_code(security, code):
            raise ValueError("❌ کد واردشده معتبر نیست")
        # پاکسازی کد بعد از موفقیت
        security.activeCode = None
        security.expireCode = None
        security.save()
        return True

    @staticmethod
    def activate_user(user):
        user.is_active = True
        user.save()

    @staticmethod
    def get_code_status(security):
        """
        دریافت وضعیت کد (زمان باقی‌مانده، امکان ارسال مجدد)
        """
        remaining_seconds = 0
        can_resend = True

        if security.expireCode:
            remaining_time = security.expireCode - timezone.now()
            if remaining_time.total_seconds() > 0:
                remaining_seconds = int(remaining_time.total_seconds())
                can_resend = False

        # تبدیل زمان به فرمت MM:SS
        minutes = remaining_seconds // 60
        seconds = remaining_seconds % 60
        remaining_time_display = f"{minutes:02d}:{seconds:02d}"

        return {
            'remaining_seconds': remaining_seconds,
            'remaining_time_display': remaining_time_display,
            'can_resend': can_resend
        }

    @staticmethod
    def resend_activation_code(security):
        """
        ارسال مجدد کد فعال‌سازی
        """
       
        if security.expireCode:
            remaining_time = security.expireCode - timezone.now()
            if remaining_time.total_seconds() > 0:
                remaining_seconds = int(remaining_time.total_seconds())
                raise ValueError(f"⏳ لطفاً {remaining_seconds} ثانیه دیگر مجدداً تلاش کنید.")

        # تولید کد جدید
        code = generate_activation_code(5)
        expire_time = timezone.now() + timedelta(minutes=2)
        security.activeCode = code
        security.expireCode = expire_time
        security.save()

        # TODO: ارسال پیامک واقعی
        print(f"کد جدید برای {security.user.mobileNumber}: {code}")

        # محاسبه زمان باقی‌مانده جدید
        remaining_seconds = 120  # 2 دقیقه

        return {
            'message': f"✅ کد جدید به شماره {security.user.mobileNumber} ارسال شد.",
            'remaining_seconds': remaining_seconds
        }