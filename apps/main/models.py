from django.db import models
from django.utils import timezone
import os
from PIL import Image
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import utils

# Create your models here.
class SliderSite(models.Model):

    textSlider = models.CharField(max_length=100, verbose_name='متن اسلایدر')
    imageFile = utils.FileUpload('images', 'slider')
    imageName = models.ImageField(upload_to=imageFile.upload_to, verbose_name='عکس اسلایدر', blank=True, null=True)
    imageMobile = models.ImageField(upload_to=imageFile.upload_to, verbose_name='عکس برای موبایل', blank=True, null=True)
    altSlide = models.CharField(verbose_name='نوشتار عکس', max_length=100, blank=True, null=True)
    isActive = models.BooleanField(verbose_name='فعال', default=True)
    registerData = models.DateTimeField(verbose_name='تاریخ شروع', default=timezone.now)
    endData = models.DateTimeField(verbose_name='تاریخ پایان', default=timezone.now)
    link = models.CharField(max_length=300, verbose_name='لینک', null=True, blank=True)

    def __str__(self) -> str:
        return self.textSlider

    def deactivateIfExpired(self):
        if self.endData and self.endData < timezone.now():
            self.isActive = False
            self.save()

    class Meta:
        verbose_name = 'اسلایدر'
        verbose_name_plural = 'اسلایدرها'


class SliderMain(models.Model):
    textSlider = models.CharField(max_length=100, verbose_name='متن اسلایدر')
    imageFile = utils.FileUpload('images', 'slider')
    imageName = models.ImageField(upload_to=imageFile.upload_to, verbose_name='عکس اسلایدر')
    altSlide = models.CharField(verbose_name='نوشتار عکس', max_length=100, blank=True, null=True)
    isActive = models.BooleanField(verbose_name='فعال', default=True)
    registerData = models.DateTimeField(verbose_name='تاریخ شروع', default=timezone.now)
    endData = models.DateTimeField(verbose_name='تاریخ پایان', default=timezone.now)
    link = models.CharField(max_length=300, verbose_name='لینک', null=True, blank=True)

    def __str__(self) -> str:
        return self.textSlider

    def deactivateIfExpired(self):
        if self.endData and self.endData < timezone.now():
            self.isActive = False
            self.save()

    class Meta:
        verbose_name = 'اسلایدر مرکز'
        verbose_name_plural = 'اسلایدرها مرکز ها'


class Banner(models.Model):
    nameBanner = models.CharField(max_length=100, verbose_name='نام بنر')
    textBanner = models.CharField(max_length=300, verbose_name='متن بنر')
    altSlide = models.CharField(verbose_name='نوشتار عکس', max_length=100, blank=True, null=True)
    imageFile = utils.FileUpload('images', 'banners')
    imageName = models.ImageField(upload_to=imageFile.upload_to)
    isActive = models.BooleanField(default=False)
    registerData = models.DateTimeField(verbose_name='تاریخ شروع', default=timezone.now)
    endData = models.DateTimeField(verbose_name='تاریخ پایان', default=timezone.now)

    def deactivateIfExpired(self):
        if self.endData and self.endData < timezone.now():
            self.isActive = False
            self.save()

    def __str__(self) -> str:
        return self.nameBanner

    class Meta:
        verbose_name = 'بنر'
        verbose_name_plural = 'بنرها'


def validateImageOrSvg(file):
    """
    Validator to check if the uploaded file is an image or an SVG.
    """
    ext = os.path.splitext(file.name)[1].lower()
    if ext == '.svg':
        return  # Valid SVG file
    try:
        img = Image.open(file)
        img.verify()
    except Exception as exc:
        raise ValidationError(
            _('Invalid file. Only images or SVGs are allowed.')
        ) from exc





class ContactPhone(models.Model):
    PHONE_TYPE_CHOICES = (
        ('mobile', 'موبایل'),
        ('phone', 'تلفن ثابت'),
        ('support', 'پشتیبانی'),
        ('sales', 'فروش'),
        ('whatsapp', 'واتساپ'),
    )

    title = models.CharField(
        max_length=100,
        verbose_name="عنوان شماره"
    )

    phone_number = models.CharField(
        max_length=20,
        verbose_name="شماره تماس"
    )

    phone_type = models.CharField(
        max_length=20,
        choices=PHONE_TYPE_CHOICES,
        default='mobile',
        verbose_name="نوع شماره"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="فعال"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ ایجاد"
    )

    class Meta:
        verbose_name = "شماره تماس"
        verbose_name_plural = "شماره‌های تماس"

    def __str__(self):
        return f"{self.title} - {self.phone_number}"




class SettingShop(models.Model):
    name_shop = models.CharField(
        max_length=200,
        verbose_name="نام فروشگاه"
    )

    establishment_year = models.PositiveIntegerField(
        verbose_name="سال تأسیس"
    )

    about_shop = models.TextField(
        blank=True,
        verbose_name="درباره فروشگاه"
    )

    is_call = models.BooleanField(
        default=True,
        verbose_name="امکان تماس"
    )

    emergency_phone = models.ForeignKey(
        ContactPhone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='emergency_for_shop',
        verbose_name="شماره تماس اضطراری"
    )

    logo = models.ImageField(
        upload_to="shop/logo/",
        blank=True,
        null=True,
        verbose_name="لوگوی فروشگاه"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ ایجاد"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="آخرین بروزرسانی"
    )

    class Meta:
        verbose_name = "تنظیمات فروشگاه"
        verbose_name_plural = "تنظیمات فروشگاه"

    def __str__(self):
        return self.name_shop



from django.db import models
from django.utils import timezone
from django.contrib.sessions.models import Session
from django.conf import settings

from apps.user.models.user import CustomUser

class UniqueVisit(models.Model):
    """
    مدل ثبت بازدید یکتا
    """
    session_key = models.CharField(
        max_length=40,
        unique=True,
        verbose_name="کلید جلسه"
    )
    ip_address = models.GenericIPAddressField(
        verbose_name="آدرس IP",
        blank=True,
        null=True
    )
    user = models.ForeignKey(
        CustomUser,  # استفاده از CustomUser شما
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="کاربر (لاگین شده)"
    )

    first_visit = models.DateTimeField(
        auto_now_add=True,
        verbose_name="اولین بازدید"
    )
    last_visit = models.DateTimeField(
        auto_now=True,
        verbose_name="آخرین بازدید"
    )
    visit_count = models.PositiveIntegerField(
        default=1,
        verbose_name="تعداد بازدیدها"
    )

    user_agent = models.TextField(
        verbose_name="مرورگر و دستگاه",
        blank=True,
        null=True
    )
    referer = models.URLField(
        verbose_name="صفحه قبلی",
        blank=True,
        null=True
    )

    country = models.CharField(
        max_length=100,
        verbose_name="کشور",
        blank=True,
        null=True
    )
    city = models.CharField(
        max_length=100,
        verbose_name="شهر",
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = "بازدید یکتا"
        verbose_name_plural = "بازدیدهای یکتا"
        ordering = ['-first_visit']

    def __str__(self):
        if self.user:
            # دسترسی به mobileNumber و name/family از CustomUser
            user_display = str(self.user.mobileNumber)
            if self.user.name or self.user.family:
                user_display = f"{self.user.name or ''} {self.user.family or ''}".strip()
            return f"{user_display} - {self.first_visit.strftime('%Y/%m/%d %H:%M')}"
        return f"کاربر ناشناس - {self.first_visit.strftime('%Y/%m/%d %H:%M')}"


class DailyStat(models.Model):
    """
    مدل آمار روزانه
    """
    date = models.DateField(
        unique=True,
        verbose_name="تاریخ"
    )
    unique_visitors = models.PositiveIntegerField(
        default=0,
        verbose_name="بازدیدکنندگان یکتا"
    )
    total_visits = models.PositiveIntegerField(
        default=0,
        verbose_name="کل بازدیدها"
    )
    page_views = models.PositiveIntegerField(
        default=0,
        verbose_name="نمایش صفحات"
    )

    class Meta:
        verbose_name = "آمار روزانه"
        verbose_name_plural = "آمار روزانه"
        ordering = ['-date']

    def __str__(self):
        return f"{self.date} - {self.unique_visitors} بازدیدکننده"


class PageVisit(models.Model):
    """
    مدل ثبت بازدید هر صفحه
    """
    visit = models.ForeignKey(
        UniqueVisit,
        on_delete=models.CASCADE,
        related_name="page_visits",
        verbose_name="بازدید"
    )
    url = models.URLField(
        max_length=500,
        verbose_name="آدرس صفحه"
    )
    path = models.CharField(
        max_length=500,
        verbose_name="مسیر صفحه"
    )
    method = models.CharField(
        max_length=10,
        default='GET',
        verbose_name="متد درخواست"
    )
    status_code = models.PositiveIntegerField(
        default=200,
        verbose_name="وضعیت پاسخ"
    )
    response_time = models.FloatField(
        null=True,
        blank=True,
        verbose_name="زمان پاسخ (میلی‌ثانیه)"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="زمان بازدید"
    )

    class Meta:
        verbose_name = "بازدید صفحه"
        verbose_name_plural = "بازدیدهای صفحات"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.visit} - {self.path}"