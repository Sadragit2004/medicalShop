from django.db import models
from apps.product.models import *
from django.core.validators import MaxValueValidator, MinValueValidator
from datetime import datetime

# Create your models here.

class Copon(models.Model):
    copon = models.CharField(max_length=10, verbose_name='کد تخفیف', unique=True)
    startDate = models.DateTimeField(verbose_name='تاریخ شروع', default=timezone.now())
    endDate = models.DateTimeField(verbose_name='تاریخ پایان', default=timezone.now())
    discount = models.IntegerField(verbose_name='درصد تخفیف')
    isActive = models.BooleanField(verbose_name='فعال', default=False)

    def __str__(self) -> str:
        return f'{self.copon}'

    class Meta:
        verbose_name = 'کوپن تخفیف'
        verbose_name_plural = 'کوپن تخفیفات'


class DiscountBasket(models.Model):

    discountTitle = models.CharField(max_length=100, verbose_name='وضوع تخفیف')
    startDate = models.DateTimeField(verbose_name='تاریخ شروع', default=timezone.now())
    endDate = models.DateTimeField(verbose_name='تاریخ پایان', default=timezone.now())
    discount = models.IntegerField(verbose_name='درصد تخفیف', validators=[MinValueValidator(0), MaxValueValidator(100)])
    isActive = models.BooleanField(verbose_name='وضعیت', default=False)

    class Meta:
        verbose_name = ' سبد تخفیف '
        verbose_name_plural =  'سبد تخفیف ها '


class DiscountDetail(models.Model):
    
    discountBasket = models.ForeignKey(DiscountBasket, on_delete=models.CASCADE, verbose_name='سبد تخفیف', related_name='discountOfBasket')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='سایت', related_name='productOfDiscount')

    class Meta:
        verbose_name = 'جزییات سبد خرید'
        verbose_name_plural = 'جزییات سبد تخفیف ها'