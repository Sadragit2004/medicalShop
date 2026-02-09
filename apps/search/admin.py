from django.contrib import admin
from .models import PopularSearch

@admin.register(PopularSearch)
class PopularSearchAdmin(admin.ModelAdmin):
    """تنظیمات ادمین برای جستجوهای پرطرفدار"""

    # فیلدهای نمایش در لیست
    list_display = ['keyword', 'search_count', 'click_count', 'last_searched', 'created_at']

    # فیلدهای قابل جستجو
    search_fields = ['keyword']

    # فیلترهای کناری
    list_filter = ['created_at', 'last_searched']

    # فیلدهای قابل ویرایش در لیست
    list_editable = ['search_count', 'click_count']

    # ترتیب مرتب‌سازی پیش‌فرض
    ordering = ['-search_count']

    # تعداد آیتم در هر صفحه
    list_per_page = 20

    # غیرفعال کردن قابلیت حذف (اختیاری)
    def has_delete_permission(self, request, obj=None):
        # اگر می‌خواهید حذف غیرفعال باشد
        # return False
        return True

    # نمایش فیلدهای فقط خواندنی
    readonly_fields = ['created_at']

    # گروه‌بندی فیلدها در فرم ویرایش
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('keyword', 'search_count', 'click_count')
        }),
        ('تاریخ‌ها', {
            'fields': ('last_searched', 'created_at'),
            'classes': ('collapse',)  # قابل جمع شدن
        }),
    )

    # اکشن‌های سفارشی
    actions = ['reset_counts', 'mark_as_popular']

    def reset_counts(self, request, queryset):
        """بازنشانی تعداد جستجو و کلیک"""
        updated = queryset.update(search_count=1, click_count=0)
        self.message_user(request, f'{updated} مورد بازنشانی شد.')

    reset_counts.short_description = "بازنشانی آمار انتخاب شده"

    def mark_as_popular(self, request, queryset):
        """علامت‌گذاری به عنوان پرطرفدار"""
        queryset.update(search_count=models.F('search_count') + 100)
        self.message_user(request, f'{queryset.count()} مورد به عنوان پرطرفدار علامت‌گذاری شد.')

    mark_as_popular.short_description = "علامت‌گذاری به عنوان پرطرفدار"