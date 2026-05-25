from django.db import models
from django.utils import timezone
from decimal import Decimal
from apps.product.models import Product, ProductSaleType
from apps.user.models.user import CustomUser


class ProductPriceHistory(models.Model):
    """تاریخچه قیمت محصولات"""

    SOURCE_CHOICES = [
        ('manual_phone', 'تماس تلفنی'),
        ('manual_whatsapp', 'پیامک/واتساپ'),
        ('manual_excel', 'وارد کردن از اکسل'),
        ('wholesaler', 'عمده‌فروش'),
        ('union', 'اتحادیه'),
        ('website', 'سایت دیگر'),
        ('other', 'سایر'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="محصول", related_name='price_history')
    sale_type = models.ForeignKey(ProductSaleType, on_delete=models.CASCADE, verbose_name="نوع فروش", related_name='price_history', null=True, blank=True)

    price_old = models.PositiveIntegerField(verbose_name="قیمت قبلی")
    price_new = models.PositiveIntegerField(verbose_name="قیمت جدید")

    percent_change = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="درصد تغییر", null=True, blank=True)

    CHANGE_TYPE_CHOICES = [('increase', 'افزایش'), ('decrease', 'کاهش'), ('same', 'بدون تغییر')]
    change_type = models.CharField(max_length=10, choices=CHANGE_TYPE_CHOICES, verbose_name="نوع تغییر", null=True, blank=True)

    changed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="تغییردهنده", related_name='price_changes')
    changed_by_name = models.CharField(max_length=200, verbose_name="نام تغییردهنده", null=True, blank=True)

    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='manual_phone', verbose_name="منبع قیمت")
    source_detail = models.CharField(max_length=300, verbose_name="توضیحات منبع", null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now, verbose_name="زمان ثبت تغییر")
    is_current = models.BooleanField(default=False, verbose_name="قیمت جاری")
    note = models.TextField(verbose_name="یادداشت", null=True, blank=True)

    class Meta:
        verbose_name = "تاریخچه قیمت"
        verbose_name_plural = "تاریخچه قیمت‌ها"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'sale_type', '-created_at']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_current']),
        ]

    def save(self, *args, **kwargs):
        if self.price_old and self.price_new:
            if self.price_old > 0:
                diff = self.price_new - self.price_old
                self.percent_change = round((diff / self.price_old) * 100, 2)
                self.change_type = 'increase' if diff > 0 else 'decrease' if diff < 0 else 'same'
            else:
                self.percent_change = None
                self.change_type = 'same'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.title} - {self.price_old} → {self.price_new} ({self.percent_change}%)"


class ProductStockHistory(models.Model):
    """تاریخچه موجودی محصولات - ذخیره موجودی قبل از غیرفعال شدن"""

    CHANGE_TYPE_CHOICES = [
        ('manual', 'تغییر دستی'),
        ('toggle_off', 'غیرفعال شدن محصول'),
        ('toggle_on', 'فعال شدن محصول'),
        ('sale', 'فروش'),
        ('restock', 'افزایش موجودی'),
        ('system', 'تغییر سیستمی'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="محصول", related_name='stock_history')

    stock_old = models.PositiveIntegerField(verbose_name="موجودی قبلی")
    stock_new = models.PositiveIntegerField(verbose_name="موجودی جدید")

    # برای بازیابی موجودی هنگام فعال شدن
    saved_stock_before_disable = models.PositiveIntegerField(
        verbose_name="موجودی ذخیره شده قبل از غیرفعال شدن",
        null=True, blank=True,
        help_text="هنگام غیرفعال کردن محصول، موجودی قبلی اینجا ذخیره می‌شود"
    )

    change_type = models.CharField(max_length=20, choices=CHANGE_TYPE_CHOICES, verbose_name="نوع تغییر")

    changed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="تغییردهنده", related_name='stock_changes')
    changed_by_name = models.CharField(max_length=200, verbose_name="نام تغییردهنده", null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now, verbose_name="زمان ثبت تغییر")
    note = models.TextField(verbose_name="یادداشت", null=True, blank=True)

    class Meta:
        verbose_name = "تاریخچه موجودی"
        verbose_name_plural = "تاریخچه موجودی‌ها"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', '-created_at']),
            models.Index(fields=['change_type']),
        ]

    def __str__(self):
        return f"{self.product.title}: {self.stock_old} → {self.stock_new} ({self.get_change_type_display()})"