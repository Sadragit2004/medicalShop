from django.db import models
from django.utils import timezone
import uuid
import jdatetime
from apps.product.models import Product, Brand
from apps.user.models.user import CustomUser
import utils


class State(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="نام استان")
    center = models.CharField(max_length=100, verbose_name="مرکز استان", blank=True, null=True)
    lat = models.DecimalField(max_digits=9, decimal_places=6, verbose_name="عرض جغرافیایی", blank=True, null=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, verbose_name="طول جغرافیایی", blank=True, null=True)
    externalId = models.UUIDField(unique=True, default=uuid.uuid4, verbose_name="آیدی API", help_text="شناسه استان در API خارجی")

    class Meta:
        verbose_name = "استان"
        verbose_name_plural = "استان‌ها"
        ordering = ["name"]

    def __str__(self):
        return self.name


class City(models.Model):
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name="cities", verbose_name="استان")
    name = models.CharField(max_length=100, verbose_name="نام شهر")
    lat = models.DecimalField(max_digits=9, decimal_places=6, verbose_name="عرض جغرافیایی", blank=True, null=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, verbose_name="طول جغرافیایی", blank=True, null=True)
    externalId = models.UUIDField(unique=True, default=uuid.uuid4, verbose_name="آیدی API", help_text="شناسه استان در API خارجی")

    class Meta:
        verbose_name = "شهر"
        verbose_name_plural = "شهرها"
        ordering = ["name"]
        unique_together = ("state", "name")

    def __str__(self):
        return f"{self.name} ({self.state.name})"


class UserAddress(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="addresses", verbose_name="کاربر")
    state = models.ForeignKey(State, on_delete=models.PROTECT, verbose_name="استان")
    city = models.ForeignKey(City, on_delete=models.PROTECT, verbose_name="شهر")
    addressDetail = models.TextField(verbose_name="آدرس دقیق")
    postalCode = models.CharField(max_length=20, verbose_name="کد پستی", blank=True, null=True)
    lat = models.DecimalField(max_digits=9, decimal_places=6, verbose_name="عرض جغرافیایی", blank=True, null=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, verbose_name="طول جغرافیایی", blank=True, null=True)
    createdAt = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")

    class Meta:
        verbose_name = "آدرس کاربر"
        verbose_name_plural = "آدرس‌های کاربران"
        ordering = ["-createdAt"]

    def __str__(self):
        return f"{self.user} - {self.city.name}"

    def fullAddress(self):
        return f"{self.state.name}، {self.city.name}، {self.addressDetail}"

    def coordinates(self):
        return (
            self.lat or self.city.lat,
            self.lng or self.city.lng,
        )


class Order(models.Model):
    STATUS_CHOICES = (
        ("pending", "در حال بررسی"),
        ("processing", "در حال پردازش"),
        ("paid", "پرداخت شده"),
        ("shipped", "ارسال شده"),
        ("delivered", "تحویل داده شده"),
        ("canceled", "لغو شده"),
    )

    customer = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="orders",
        verbose_name="مشتری"
    )

    address = models.ForeignKey(
        UserAddress,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name="آدرس سفارش"
    )

    orderCode = models.UUIDField(
        unique=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="کد سفارش"
    )

    registerDate = models.DateTimeField(
        default=timezone.now,
        verbose_name="تاریخ ثبت"
    )

    updateDate = models.DateTimeField(
        auto_now=True,
        verbose_name="تاریخ ویرایش"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name="وضعیت سفارش"
    )

    description = models.TextField(
        null=True,
        blank=True,
        verbose_name="توضیحات"
    )

    discount = models.PositiveIntegerField(
        default=0,
        verbose_name="تخفیف (%)"
    )

    isFinally = models.BooleanField(
        default=False,
        verbose_name="نهایی شده"
    )

    _original_status = None

    def __str__(self):
        return f"سفارش {self.orderCode}"

    def getTotalPrice(self):
        return sum(item.price * item.qty for item in self.details.all())

    def getFinalPrice(self):
        total = self.getTotalPrice()
        if self.discount:
            total -= (total * self.discount) // 100
        return total

    def get_order_total_price(self):
        total = self.getTotalPrice()
        final_price, tax = utils.price_by_delivery_tax(total, self.discount)
        return int(final_price * 10)

    # ======================== توابع تبدیل تاریخ به شمسی با jdatetime (اصلاح شده) ========================

    def _to_naive_datetime(self, dt):
        """تبدیل timezone-aware به timezone-naive"""
        if dt is None:
            return None
        if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
            return dt.astimezone(timezone.get_current_timezone()).replace(tzinfo=None)
        return dt

    def get_jalali_register_date(self):
        """تاریخ ثبت به شمسی - فقط تاریخ"""
        if not self.registerDate:
            return "-"
        dt = self._to_naive_datetime(self.registerDate)
        jalali = jdatetime.datetime.fromgregorian(datetime=dt)
        return jalali.strftime("%Y/%m/%d")

    def get_jalali_register_time(self):
        """ساعت ثبت به شمسی - فقط ساعت"""
        if not self.registerDate:
            return "-"
        dt = self._to_naive_datetime(self.registerDate)
        return dt.strftime("%H:%M")

    def get_jalali_register_datetime(self):
        """تاریخ و ساعت ثبت به شمسی"""
        if not self.registerDate:
            return "-"
        dt = self._to_naive_datetime(self.registerDate)
        jalali = jdatetime.datetime.fromgregorian(datetime=dt)
        return jalali.strftime("%Y/%m/%d %H:%M")

    def get_jalali_register_with_month_name(self):
        """تاریخ ثبت با نام ماه"""
        if not self.registerDate:
            return "-"
        dt = self._to_naive_datetime(self.registerDate)
        jalali = jdatetime.datetime.fromgregorian(datetime=dt)
        month_names = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
                       'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند']
        return f"{jalali.strftime('%Y/%m/%d')} {month_names[jalali.month - 1]} {jalali.strftime('%H:%M')}"

    def get_jalali_update_date(self):
        """تاریخ بروزرسانی به شمسی"""
        if not self.updateDate:
            return "-"
        dt = self._to_naive_datetime(self.updateDate)
        jalali = jdatetime.datetime.fromgregorian(datetime=dt)
        return jalali.strftime("%Y/%m/%d")

    def get_jalali_update_datetime(self):
        """تاریخ و ساعت بروزرسانی به شمسی"""
        if not self.updateDate:
            return "-"
        dt = self._to_naive_datetime(self.updateDate)
        jalali = jdatetime.datetime.fromgregorian(datetime=dt)
        return jalali.strftime("%Y/%m/%d %H:%M")

    class Meta:
        verbose_name = "سفارش"
        verbose_name_plural = "سفارش‌ها"
        ordering = ['-registerDate']


class OrderDetail(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="details",
        verbose_name="سفارش"
    )

    product = models.ForeignKey(
        "product.Product",
        on_delete=models.CASCADE,
        related_name="orderItems",
        verbose_name="محصول"
    )

    brand = models.ForeignKey(
        "product.Brand",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="برند"
    )

    qty = models.PositiveIntegerField(
        default=1,
        verbose_name="تعداد"
    )

    price = models.PositiveIntegerField(
        verbose_name="قیمت واحد"
    )

    selectedOptions = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="ویژگی‌های انتخابی"
    )

    def __str__(self):
        return f"{self.order.orderCode} | {self.product} × {self.qty}"

    def getTotalPrice(self):
        return self.qty * self.price

    class Meta:
        verbose_name = "جزئیات سفارش"
        verbose_name_plural = "جزئیات سفارش‌ها"