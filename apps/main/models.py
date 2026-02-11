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
