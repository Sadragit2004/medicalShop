from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.order.models import Order
from apps.dashboard.models import Notification

@receiver(post_save, sender=Order)
def create_order_notifications(sender, instance, created, **kwargs):
    """
    ایجاد اعلان‌های خودکار برای تغییرات سفارش
    """
    if created:
        # اعلان ایجاد سفارش جدید - بدون ایموجی
        Notification.objects.create(
            user=instance.customer,
            order=instance,
            title="سفارش جدید ثبت شد",
            message=f"سفارش شما با کد پیگیری #{instance.id} با موفقیت ثبت شد.",
            notification_type='order',
            icon='shopping-cart'
        )
    else:
        # اعلان تغییر وضعیت سفارش
        try:
            original_order = Order.objects.get(pk=instance.pk)
            original_status = original_order.status
        except Order.DoesNotExist:
            original_status = None

        if original_status != instance.status:
            status_messages = {
                'pending': 'در حال بررسی',
                'processing': 'در حال پردازش',
                'shipped': 'ارسال شده',
                'delivered': 'تحویل داده شده',
                'canceled': 'لغو شده',
            }

            status_icons = {
                'pending': 'clock',
                'processing': 'settings',
                'shipped': 'truck',
                'delivered': 'check-circle',
                'canceled': 'x-circle',
            }

            # بدون ایموجی در عنوان
            Notification.objects.create(
                user=instance.customer,
                order=instance,
                title=f"وضعیت سفارش #{instance.id}",
                message=f"وضعیت سفارش شما به '{status_messages.get(instance.status, instance.status)}' تغییر کرد.",
                notification_type='order',
                icon=status_icons.get(instance.status, 'bell')
            )