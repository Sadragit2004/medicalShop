from django.db.models.signals import post_save, post_init
from django.dispatch import receiver
from django.apps import apps
from apps.order.models import Order


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
