# from django.db import models
# from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
# from django.utils import timezone
# from datetime import date
# import uuid

# from ..validators.model import (
#     validate_iranian_mobile,
#     validate_numeric,
#     generate_activation_code,
#     generate_expiration_time,
#     validate_activation_code,
# )


# # =========================
# # 👤 Custom User Manager
# # =========================

# class CustomUserManager(BaseUserManager):

#     def create_user(self, mobileNumber, password=None, email=None, name=None, family=None, gender="True"):
#         if not mobileNumber:
#             raise ValueError("شماره موبایل الزامی است")

#         # اعتبارسنجی شماره موبایل
#         validate_iranian_mobile(mobileNumber)

#         user = self.model(
#             mobileNumber=mobileNumber,
#             email=email,
#             name=name,
#             family=family,
#             gender=gender,
#         )
#         user.set_password(password)
#         user.save(using=self._db)
#         return user

#     def create_superuser(self, mobileNumber, password, email=None, name=None, family=None, gender="True"):
#         user = self.create_user(
#             mobileNumber=mobileNumber,
#             password=password,
#             email=email,
#             name=name,
#             family=family,
#             gender=gender,
#         )
#         user.is_staff = True
#         user.is_superuser = True
#         user.is_active = True
#         user.save(using=self._db)
#         return user


# # =========================
# # 👥 User Model
# # =========================
# class CustomUser(AbstractBaseUser, PermissionsMixin):
#     id = models.UUIDField(primary_key=True, verbose_name='ایدی', editable=False, default=uuid.uuid4)
#     mobileNumber = models.CharField(
#         max_length=11,
#         unique=True,
#         verbose_name="شماره موبایل",
#         validators=[validate_iranian_mobile]
#     )
#     email = models.EmailField(max_length=100, blank=True, null=True, verbose_name="ایمیل")
#     name = models.CharField(max_length=60, blank=True, null=True, verbose_name="نام")
#     family = models.CharField(max_length=60, blank=True, null=True, verbose_name="نام خانوادگی")

#     GENDER_CHOICES = (
#         ("True", "مرد"),
#         ("False", "زن"),
#     )
#     gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default="True")

#     birth_date = models.DateField(null=True, blank=True, verbose_name="تاریخ تولد")
#     is_admin = models.BooleanField(default=False, verbose_name='ادمین اختصاصی')
#     is_active = models.BooleanField(default=False, verbose_name="فعال/غیرفعال")
#     is_staff = models.BooleanField(default=False, verbose_name="کارمند (دسترسی ادمین)")
#     is_superuser = models.BooleanField(default=False, verbose_name="کاربر اصلی")

#     objects = CustomUserManager()

#     USERNAME_FIELD = "mobileNumber"
#     REQUIRED_FIELDS = ["name", "email", "family"]

#     def __str__(self):
#         return f"{self.mobileNumber} - {self.name or ''} {self.family or ''}"

#     @property
#     def age(self):
#         if self.birth_date:
#             today = date.today()
#             return today.year - self.birth_date.year - (
#                 (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
#             )
#         return None




# class UserSecurity(models.Model):
#     user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="security")
#     activeCode = models.CharField(max_length=16, verbose_name="کد فعال‌سازی", blank=True, null=True)
#     expireCode = models.DateTimeField(verbose_name="تاریخ انقضای کد", blank=True, null=True)
#     isBan = models.BooleanField(default=False, verbose_name="بن شده/نشده")
#     isInfoFiled = models.BooleanField(default=False, verbose_name='وضعیت تکمیل اطلاعات')
#     createdAt = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")

#     def __str__(self):
#         return f"Security for {self.user.mobileNumber}"

#     def set_activation_code(self):
#         """
#         ایجاد کد فعال‌سازی جدید برای کاربر
#         """
#         self.activeCode = generate_activation_code()
#         self.expireCode = generate_expiration_time()
#         self.save(update_fields=["activeCode", "expireCode"])

#     def validate_code(self, code):
#         """
#         بررسی صحت کد فعال‌سازی
#         """
#         return validate_activation_code(self, code)


# # =========================
# # 💻 User Device Model
# # =========================
# class UserDevice(models.Model):

#     user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="devices")
#     deviceInfo = models.CharField(max_length=255, verbose_name="اطلاعات دستگاه")
#     ipAddress = models.GenericIPAddressField(verbose_name="آی‌پی", blank=True, null=True)
#     createdAt = models.DateTimeField(default=timezone.now, verbose_name="تاریخ ثبت")

#     def __str__(self):
#         return f"Device of {self.user.mobileNumber} - {self.deviceInfo}"
