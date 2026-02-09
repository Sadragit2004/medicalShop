from django.contrib import admin
from django.utils import timezone
from jalali_date import datetime2jalali
from .models import PopularSearch

@admin.register(PopularSearch)
class PopularSearchAdmin(admin.ModelAdmin):
    """پنل ادمین برای جستجوهای پرطرفدار"""

    # فیلدهای قابل نمایش در لیست
    list_display = ['keyword', 'search_count', 'click_count', 'last_searched_jalali', 'created_at_jalali']

    # فیلدهای قابل جستجو
    search_fields = ['keyword']

    # فیلترهای سمت راست
    list_filter = ['created_at', 'last_searched']

    # مرتب‌سازی پیش‌فرض
    ordering = ['-search_count', '-last_searched']

    # فیلدهای غیر قابل ویرایش
    readonly_fields = ['search_count', 'click_count', 'last_searched', 'created_at', 'last_searched_jalali', 'created_at_jalali']

    # تنظیمات نمایشی
    list_per_page = 20

    # نمایش فیلدها به صورت گروه‌بندی شده
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('keyword',)
        }),
        ('آمارها', {
            'fields': ('search_count', 'click_count')
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at_jalali', 'last_searched_jalali')
        }),
    )

    def created_at_jalali(self, obj):
        """تبدیل تاریخ ایجاد به شمسی"""
        if obj.created_at:
            jalali_date = datetime2jalali(obj.created_at)
            return jalali_date.strftime('%Y/%m/%d - %H:%M')
        return "نامشخص"
    created_at_jalali.short_description = "تاریخ ایجاد (شمسی)"

    def last_searched_jalali(self, obj):
        """تبدیل آخرین جستجو به شمسی"""
        if obj.last_searched:
            jalali_date = datetime2jalali(obj.last_searched)
            return jalali_date.strftime('%Y/%m/%d - %H:%M')
        return "نامشخص"
    last_searched_jalali.short_description = "آخرین جستجو (شمسی)"

    # غیرفعال کردن امکان افزودن دستی (اختیاری)
    def has_add_permission(self, request):
        """غیرفعال کردن دکمه افزودن جدید"""
        return False

    # غیرفعال کردن امکان حذف (اختیاری)
    def has_delete_permission(self, request, obj=None):
        """غیرفعال کردن دکمه حذف"""
        return False

    # نمایش تعداد رکوردها در بالای لیست
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        total_count = PopularSearch.objects.count()
        extra_context['title'] = f'جستجوهای پرطرفدار (تعداد: {total_count})'
        return super().changelist_view(request, extra_context, extra_context)