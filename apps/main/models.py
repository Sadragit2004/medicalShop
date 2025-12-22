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


