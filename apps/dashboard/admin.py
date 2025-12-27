# notifications/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    پنل ادمین برای مدیریت اعلان‌ها
    """
    # فیلدهای نمایش در لیست
    list_display = [
        'id',
        'user_email',
        'title',
        'notification_type',
        'is_read',
        'created_at_formatted',
        'time_ago',
        'has_order',
        'has_copon'
    ]

    # فیلدهای قابل کلیک برای دسترسی سریع
    list_display_links = ['id', 'title']

    # فیلترهای سمت راست
    list_filter = [
        'notification_type',
        'is_read',
        'created_at',
    ]

    # جستجو در فیلدهای مشخص
    search_fields = [
        'user__email',
        'user__phone',
        'title',
        'message',
    ]

    # فیلدهای قابل ویرایش در لیست
    list_editable = ['is_read']

    # ترتیب مرتب‌سازی پیش‌فرض
    ordering = ['-created_at', '-id']

    # تعداد آیتم در هر صفحه
    list_per_page = 50

    # انتخاب دسته‌جمعی
    actions = ['mark_as_read', 'mark_as_unread']

    # فیلدهای نمایش در صفحه جزئیات
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('user', 'title', 'message', 'notification_type')
        }),
        ('مرتبط‌سازی', {
            'fields': ('order', 'copon', 'icon'),
            'classes': ('collapse',)
        }),
        ('وضعیت', {
            'fields': ('is_read', 'created_at')
        }),
    )

    # فیلدهای فقط خواندنی
    readonly_fields = ['created_at', 'get_time_ago_display']

    # پیش‌نمایش پیام در لیست (اختیاری)
    def message_preview(self, obj):
        return obj.message[:100] + '...' if len(obj.message) > 100 else obj.message
    message_preview.short_description = "پیش‌نمایش پیام"

    # نمایش ایمیل کاربر
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = "ایمیل کاربر"

    # نمایش تاریخ فرمت‌شده
    def created_at_formatted(self, obj):
        return obj.created_at.strftime("%Y/%m/%d - %H:%M")
    created_at_formatted.short_description = "تاریخ ایجاد"

    # نمایش زمان گذشته
    def time_ago(self, obj):
        return obj.get_time_ago()
    time_ago.short_description = "زمان گذشته"

    # بررسی وجود سفارش مرتبط
    def has_order(self, obj):
        if obj.order:
            return format_html(
                '<span style="color: green;">✓</span>'
            )
        return format_html('<span style="color: red;">✗</span>')
    has_order.short_description = "سفارش"
    has_order.admin_order_field = 'order'

    # بررسی وجود کوپن مرتبط
    def has_copon(self, obj):
        if obj.copon:
            return format_html(
                '<span style="color: green;">✓</span>'
            )
        return format_html('<span style="color: red;">✗</span>')
    has_copon.short_description = "کوپن"
    has_copon.admin_order_field = 'copon'

    # اکشن‌های سفارشی
    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f"{updated} اعلان به عنوان خوانده شده علامت‌گذاری شد.")
    mark_as_read.short_description = "علامت‌گذاری به عنوان خوانده شده"

    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f"{updated} اعلان به عنوان خوانده نشده علامت‌گذاری شد.")
    mark_as_unread.short_description = "علامت‌گذاری به عنوان خوانده نشده"

    # نمایش get_time_ago در صفحه جزئیات
    def get_time_ago_display(self, obj):
        return obj.get_time_ago()
    get_time_ago_display.short_description = "زمان گذشته از ایجاد"

    # سفارشی‌سازی ظاهر بر اساس وضعیت خوانده شدن
    def colored_is_read(self, obj):
        if obj.is_read:
            return format_html(
                '<span style="color: green; font-weight: bold;">خوانده شده</span>'
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">خوانده نشده</span>'
        )
    colored_is_read.short_description = "وضعیت"

    # اضافه کردن لینک به سفارش در صورت وجود
    def order_link(self, obj):
        if obj.order:
            url = f"/admin/order/order/{obj.order.id}/change/"
            return format_html(f'<a href="{url}">مشاهده سفارش #{obj.order.id}</a>')
        return "-"
    order_link.short_description = "لینک سفارش"

    # اضافه کردن لینک به کوپن در صورت وجود
    def copon_link(self, obj):
        if obj.copon:
            url = f"/admin/discount/copon/{obj.copon.id}/change/"
            return format_html(f'<a href="{url}">مشاهده کوپن</a>')
        return "-"
    copon_link.short_description = "لینک کوپن"

# اختیاری: اگر می‌خواهید نمایش ساده‌تری هم داشته باشید
class NotificationSimpleAdmin(admin.ModelAdmin):
    """
    نمایش ساده‌تر اعلان‌ها
    """
    list_display = ['id', 'user', 'title_short', 'is_read', 'created_at']
    list_filter = ['is_read', 'notification_type']
    search_fields = ['title', 'message', 'user__email']

    def title_short(self, obj):
        return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
    title_short.short_description = "عنوان"