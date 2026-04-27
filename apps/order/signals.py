from django.db.models.signals import post_save, post_init
from django.dispatch import receiver
from django.apps import apps
from .models import Order


@receiver(post_init, sender=Order)
def store_original_status(sender, instance, **kwargs):
    """
    ذخیره وضعیت اولیه هنگام لود شدن آبجکت
    """
    instance._original_status = instance.status


@receiver(post_save, sender=Order)
def create_order_notifications(sender, instance, created, **kwargs):
    """
    ایجاد نوتیفیکیشن سفارش
    """
    Notification = apps.get_model('dashboard', 'Notification')

    status_display = {
        'pending': 'در حال بررسی',
        'processing': 'در حال پردازش',
        'shipped': 'ارسال شده',
        'delivered': 'تحویل داده شده',
        'canceled': 'لغو شده',
    }

    icon_map = {
        'pending': 'clock',
        'processing': 'settings',
        'shipped': 'truck',
        'delivered': 'check-circle',
        'canceled': 'x-circle',
    }

    try:
        if created:
            # نوتیف ثبت سفارش
            Notification.objects.create(
                user=instance.customer,
                order=instance,
                title="سفارش جدید",
                message=f"سفارش شما با کد #{instance.orderCode} با موفقیت ثبت شد.",
                notification_type="order",
                icon="shopping-cart"
            )

        else:
            # نوتیف تغییر وضعیت
            if instance._original_status != instance.status:
                Notification.objects.create(
                    user=instance.customer,
                    order=instance,
                    title="تغییر وضعیت سفارش",
                    message=(
                        f"وضعیت سفارش #{instance.orderCode} "
                        f"از «{status_display.get(instance._original_status)}» "
                        f"به «{status_display.get(instance.status)}» تغییر کرد."
                    ),
                    notification_type="order",
                    icon=icon_map.get(instance.status, "bell")
                )

                # آپدیت وضعیت قبلی
                instance._original_status = instance.status

    except Exception as e:
        print(f"Notification error: {e}")




from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.order.models import Order, OrderDetail
from apps.product.models import Product
from apps.peyment.models import Peyment


@receiver(post_save, sender=Peyment)
def decrease_stock_on_successful_payment(sender, instance, created, **kwargs):
    """
    بعد از پرداخت موفق، موجودی محصولات رو کم کن.
    فقط یک بار این کار انجام بشه.
    """
    # فقط اگه پرداخت موفق بوده و نهایی شده
    if instance.isFinaly:  # statusCode 100 یعنی موفق
        order = instance.order

        # اگه قبلاً موجودی این سفارش کم شده بود، دوباره کم نکن
        if hasattr(order, 'stock_decreased') and order.stock_decreased:
            return

        # کم کردن موجودی از هر آیتم سفارش
        for detail in order.details.all():
            product = detail.product
            if product.stock >= detail.qty:
                product.stock -= detail.qty
                product.save()
            else:
                # اگه موجودی کافی نبود، می‌تونی لاگ بزنی یا خطا بدی
                print(f"⚠️ موجودی کافی نیست برای محصول {product.title} - سفارش {order.orderCode}")

        # علامت بزن که موجودی کم شده (با یه attr موقت یا فیلد جدید)
        order.stock_decreased = True


@receiver(post_save, sender=Order)
def prevent_double_stock_decrease(sender, instance, created, **kwargs):
    """
    هر سفارشی که ساخته می‌شه، یه attr موقت می‌گیره تا توی سیگنال پرداخت
    بدونیم قبلاً کم شده یا نه.
    """
    if created:
        instance.stock_decreased = False