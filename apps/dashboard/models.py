from django.db import models
from apps.user.models.user import CustomUser
from apps.product.models import Product
# Create your models here.

# ========================
# علاقه‌مندی‌ها (Favorite/Wishlist)
# ========================

class Favorite(models.Model):
    """
    مدل برای ذخیره علاقه‌مندی‌های کاربران
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="کاربر",
                            related_name='favorites')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="محصول",
                               related_name='favorited_by')
    createdAt = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")

    class Meta:
        verbose_name = "علاقه‌مندی"
        verbose_name_plural = "علاقه‌مندی‌ها"
        unique_together = ['user', 'product']
        ordering = ['-createdAt']

    def __str__(self):
        return f"{self.user} → {self.product}"


# apps/dashboard/models.py
from django.db import models
from django.utils import timezone
from django.apps import apps  # اضافه کردن این خط
from apps.user.models.user import CustomUser
from apps.discount.models import Copon

class Notification(models.Model):
    """
    مدل اعلان‌های سیستم
    """
    NOTIFICATION_TYPES = (
        ('order', 'سفارش'),
        ('system', 'سیستم'),
        ('promotion', 'تخفیف'),
        ('other', 'سایر'),
    )

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="کاربر"
    )

    # استفاده از string reference برای جلوگیری از circular import
    order = models.ForeignKey(
        'order.Order',  # <-- تغییر این خط
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="سفارش مرتبط",
        null=True,
        blank=True
    )

    copon = models.ForeignKey(
        Copon,
        on_delete=models.SET_NULL,
        related_name="notifications",
        verbose_name="کوپن مرتبط",
        null=True,
        blank=True
    )

    title = models.CharField(
        max_length=200,
        verbose_name="عنوان اعلان"
    )

    message = models.TextField(
        verbose_name="متن اعلان"
    )

    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default='system',
        verbose_name="نوع اعلان"
    )

    is_read = models.BooleanField(
        default=False,
        verbose_name="خوانده شده"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ ایجاد"
    )

    icon = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="آیکون",
        help_text="نام کلاس آیکون (اختیاری)"
    )

    class Meta:
        verbose_name = "اعلان"
        verbose_name_plural = "اعلان‌ها"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.title}"

    def get_time_ago(self):
        """زمان گذشته از ایجاد اعلان"""
        now = timezone.now()
        diff = now - self.created_at

        if diff.days > 365:
            years = diff.days // 365
            return f"{years} سال پیش"
        elif diff.days > 30:
            months = diff.days // 30
            return f"{months} ماه پیش"
        elif diff.days > 7:
            weeks = diff.days // 7
            return f"{weeks} هفته پیش"
        elif diff.days > 0:
            return f"{diff.days} روز پیش"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} ساعت پیش"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} دقیقه پیش"
        else:
            return "همین الان"