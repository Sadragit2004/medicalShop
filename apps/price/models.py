from django.db import models
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from apps.product.models import Product, ProductSaleType
from apps.user.models.user import CustomUser


# =========================================================
# حداکثر درصد قابل ذخیره در فیلد percent_change
# با max_digits=12, decimal_places=2 → حداکثر 9999999999.99
# =========================================================
MAX_PERCENT_CHANGE = Decimal("9999999999.99")


def calculate_safe_percent_change(price_old, price_new):
    """
    محاسبه امن درصد تغییر قیمت.

    در شرایط تورمی، ممکن است قیمت از یک عدد خیلی کوچک (مثل 1)
    به یک عدد بزرگ (مثل 100000) تغییر کند که درصد آن از محدودیت
    فیلد دیتابیس فراتر می‌رود. این تابع مقدار را کلمپ می‌کند.

    Returns:
        tuple: (percent_change: Decimal | None, change_type: str)
    """
    try:
        price_old = int(price_old or 0)
        price_new = int(price_new or 0)
    except (TypeError, ValueError):
        return None, "same"

    if price_old <= 0:
        # وقتی قیمت قبلی صفر یا منفی است، درصد قابل محاسبه نیست
        if price_new > 0:
            return None, "increase"
        if price_new < 0:
            return None, "decrease"
        return None, "same"

    diff = price_new - price_old

    if diff == 0:
        return Decimal("0.00"), "same"

    try:
        percent = (
            Decimal(diff) / Decimal(price_old) * Decimal("100")
        ).quantize(Decimal("0.01"))
    except (InvalidOperation, ZeroDivisionError):
        return None, ("increase" if diff > 0 else "decrease")

    # کلمپ کردن به محدوده مجاز فیلد دیتابیس
    if percent > MAX_PERCENT_CHANGE:
        percent = MAX_PERCENT_CHANGE
    elif percent < -MAX_PERCENT_CHANGE:
        percent = -MAX_PERCENT_CHANGE

    change_type = "increase" if diff > 0 else "decrease"
    return percent, change_type


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

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name="محصول",
        related_name='price_history',
    )
    sale_type = models.ForeignKey(
        ProductSaleType,
        on_delete=models.CASCADE,
        verbose_name="نوع فروش",
        related_name='price_history',
        null=True,
        blank=True,
    )

    price_old = models.PositiveIntegerField(verbose_name="قیمت قبلی")
    price_new = models.PositiveIntegerField(verbose_name="قیمت جدید")

    # max_digits از 8 به 12 افزایش یافت تا درصدهای بزرگ تورمی جا بشن
    percent_change = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="درصد تغییر",
        null=True,
        blank=True,
    )

    CHANGE_TYPE_CHOICES = [
        ('increase', 'افزایش'),
        ('decrease', 'کاهش'),
        ('same', 'بدون تغییر'),
    ]
    change_type = models.CharField(
        max_length=10,
        choices=CHANGE_TYPE_CHOICES,
        verbose_name="نوع تغییر",
        null=True,
        blank=True,
    )

    changed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="تغییردهنده",
        related_name='price_changes',
    )
    changed_by_name = models.CharField(
        max_length=200,
        verbose_name="نام تغییردهنده",
        null=True,
        blank=True,
    )

    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default='manual_phone',
        verbose_name="منبع قیمت",
    )
    source_detail = models.CharField(
        max_length=300,
        verbose_name="توضیحات منبع",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="زمان ثبت تغییر",
    )
    is_current = models.BooleanField(
        default=False,
        verbose_name="قیمت جاری",
    )
    note = models.TextField(
        verbose_name="یادداشت",
        null=True,
        blank=True,
    )

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
        percent, change_type = calculate_safe_percent_change(
            self.price_old, self.price_new
        )
        self.percent_change = percent
        self.change_type = change_type
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.product.title} - "
            f"{self.price_old} → {self.price_new} "
            f"({self.percent_change}%)"
        )


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

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name="محصول",
        related_name='stock_history',
    )

    stock_old = models.PositiveIntegerField(verbose_name="موجودی قبلی")
    stock_new = models.PositiveIntegerField(verbose_name="موجودی جدید")

    # برای بازیابی موجودی هنگام فعال شدن
    saved_stock_before_disable = models.PositiveIntegerField(
        verbose_name="موجودی ذخیره شده قبل از غیرفعال شدن",
        null=True,
        blank=True,
        help_text="هنگام غیرفعال کردن محصول، موجودی قبلی اینجا ذخیره می‌شود",
    )

    change_type = models.CharField(
        max_length=20,
        choices=CHANGE_TYPE_CHOICES,
        verbose_name="نوع تغییر",
    )

    changed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="تغییردهنده",
        related_name='stock_changes',
    )
    changed_by_name = models.CharField(
        max_length=200,
        verbose_name="نام تغییردهنده",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="زمان ثبت تغییر",
    )
    note = models.TextField(
        verbose_name="یادداشت",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "تاریخچه موجودی"
        verbose_name_plural = "تاریخچه موجودی‌ها"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', '-created_at']),
            models.Index(fields=['change_type']),
        ]

    def __str__(self):
        return (
            f"{self.product.title}: "
            f"{self.stock_old} → {self.stock_new} "
            f"({self.get_change_type_display()})"
        )