from django.db import models
from django.utils import timezone
import uuid
from apps.product.models import Product, Brand
from apps.user.models import CustomUser
import utils
# ========================
# مدل سفارش (Order)
# ========================
class Order(models.Model):
    STATUS_CHOICES = (
        ("pending", "در حال بررسی"),
        ("processing", "در حال پردازش"),
        ("shipped", "ارسال شده"),
        ("delivered", "تحویل داده شده"),
        ("canceled", "لغو شده"),
    )

    customer = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE,
        related_name="orders", verbose_name="مشتری"
    )
    orderCode = models.UUIDField(
        unique=True, default=uuid.uuid4,
        verbose_name="کد سفارش", editable=False
    )
    registerDate = models.DateTimeField(default=timezone.now, verbose_name="تاریخ ثبت")
    updateDate = models.DateTimeField(auto_now=True, verbose_name="تاریخ ویرایش")
    addressDetail = models.TextField(verbose_name="آدرس دقیق",null=True,blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default="pending", verbose_name="وضعیت سفارش"
    )
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")

    discount = models.PositiveIntegerField(default=0, verbose_name="تخفیف روی فاکتور")
    isFinally = models.BooleanField(default=False, verbose_name="نهایی شده")

    def __str__(self):
        return f"سفارش {self.customer} - {self.orderCode}"


    def get_order_total_price(self):
        sum = 0
        for item in self.details.all():
            sum+=item.product.get_price_by_discount()*item.qty
        finaly_total_price,tax = utils.price_by_delivery_tax(sum,self.discount)
        return int(finaly_total_price*10)

    def getTotalPrice(self):
        """محاسبه جمع کل سفارش قبل از تخفیف"""
        return sum(item.price * item.qty for item in self.details.all())

    def getFinalPrice(self):
        """محاسبه مبلغ نهایی با تخفیف"""
        total = self.getTotalPrice()
        if self.discount:
            total -= (total * self.discount) // 100
        return total

    class Meta:
        verbose_name = "سفارش"
        verbose_name_plural = "سفارش‌ها"


# ========================
# مدل جزئیات سفارش (OrderDetail)
# ========================
class OrderDetail(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE,
        related_name="details", verbose_name="سفارش"
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE,
        related_name="orderItems", verbose_name="محصول"
    )
    brand = models.ForeignKey(
        Brand, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="برند"
    )


    qty = models.PositiveIntegerField(default=1, verbose_name="تعداد")
    price = models.PositiveIntegerField(verbose_name="قیمت واحد در فاکتور")

    # ویژگی‌های انتخابی (به صورت رشته ذخیره می‌کنیم)
    selectedOptions = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="ویژگی‌های انتخابی"
    )

    def __str__(self):
        return f"{self.order.orderCode} - {self.product.title} × {self.qty}"

    def getTotalPrice(self):
        return self.qty * self.price

    class Meta:
        verbose_name = "جزئیات سفارش"
        verbose_name_plural = "جزئیات سفارش‌ها"


from django.db import models
from django.conf import settings


class State(models.Model):
    """
    مدل استان‌ها
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="نام استان")
    center = models.CharField(max_length=100, verbose_name="مرکز استان", blank=True, null=True)
    lat = models.DecimalField(max_digits=9, decimal_places=6, verbose_name="عرض جغرافیایی", blank=True, null=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, verbose_name="طول جغرافیایی", blank=True, null=True)
    externalId = models.PositiveIntegerField(unique=True, verbose_name="آیدی API", help_text="شناسه استان در API خارجی")

    class Meta:
        verbose_name = "استان"
        verbose_name_plural = "استان‌ها"
        ordering = ["name"]

    def __str__(self):
        return self.name


class City(models.Model):
    """
    مدل شهرها (وابسته به استان)
    """
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name="cities", verbose_name="استان")
    name = models.CharField(max_length=100, verbose_name="نام شهر")
    lat = models.DecimalField(max_digits=9, decimal_places=6, verbose_name="عرض جغرافیایی", blank=True, null=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, verbose_name="طول جغرافیایی", blank=True, null=True)
    externalId = models.PositiveIntegerField(unique=True, verbose_name="آیدی API", help_text="شناسه شهر در API خارجی")

    class Meta:
        verbose_name = "شهر"
        verbose_name_plural = "شهرها"
        ordering = ["name"]
        unique_together = ("state", "name")

    def __str__(self):
        return f"{self.name} ({self.state.name})"


class UserAddress(models.Model):
    """
    آدرس کاربر شامل استان و شهر
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses", verbose_name="کاربر")
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
        """
        در صورت خالی بودن مختصات کاربر، از مختصات شهر استفاده می‌کند.
        """
        return (
            self.lat or self.city.lat,
            self.lng or self.city.lng,
        )
