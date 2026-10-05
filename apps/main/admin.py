from django.contrib import admin
from django.utils.html import format_html
from .models import *


# ============================================================
# اسلایدرها
# ============================================================

@admin.register(SliderSite)
class SliderSiteAdmin(admin.ModelAdmin):
    list_display = ['textSlider', 'isActive', 'registerData', 'endData', 'image_preview']
    list_filter = ['isActive', 'registerData', 'endData']
    search_fields = ['textSlider', 'altSlide']
    readonly_fields = ['registerData']

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('textSlider', 'link', 'altSlide')
        }),
        ('تصاویر', {
            'fields': ('imageName', 'imageMobile')
        }),
        ('محتوا', {
            'fields': ('description',)
        }),
        ('زمان‌بندی و وضعیت', {
            'fields': ('isActive', 'registerData', 'endData')
        }),
    )

    def image_preview(self, obj):
        if obj.imageName:
            return format_html('<img src="{}" style="width: 100px; height: auto;" />', obj.imageName.url)
        return "بدون تصویر"

    image_preview.short_description = 'پیش‌نمایش تصویر'


@admin.register(SliderMain)
class SliderMainAdmin(admin.ModelAdmin):
    list_display = ['textSlider', 'isActive', 'registerData', 'endData', 'image_preview']
    list_filter = ['isActive', 'registerData', 'endData']
    search_fields = ['textSlider', 'altSlide']
    readonly_fields = ['registerData']

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('textSlider', 'link', 'altSlide')
        }),
        ('تصویر', {
            'fields': ('imageName',)
        }),
        ('زمان‌بندی و وضعیت', {
            'fields': ('isActive', 'registerData', 'endData')
        }),
    )

    def image_preview(self, obj):
        if obj.imageName:
            return format_html('<img src="{}" style="width: 100px; height: auto;" />', obj.imageName.url)
        return "بدون تصویر"

    image_preview.short_description = 'پیش‌نمایش تصویر'


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ['nameBanner', 'isActive', 'registerData', 'endData', 'image_preview']
    list_filter = ['isActive', 'registerData', 'endData']
    search_fields = ['nameBanner', 'textBanner', 'altSlide']
    readonly_fields = ['registerData']

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('nameBanner', 'textBanner', 'altSlide')
        }),
        ('تصویر', {
            'fields': ('imageName',)
        }),
        ('زمان‌بندی و وضعیت', {
            'fields': ('isActive', 'registerData', 'endData')
        }),
    )

    def image_preview(self, obj):
        if obj.imageName:
            return format_html('<img src="{}" style="width: 100px; height: auto;" />', obj.imageName.url)
        return "بدون تصویر"

    image_preview.short_description = 'پیش‌نمایش تصویر'


# ============================================================
# شماره‌های تماس
# ============================================================

@admin.register(ContactPhone)
class ContactPhoneAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'phone_number',
        'phone_type',
        'is_active',
        'created_at',
    )

    list_filter = (
        'phone_type',
        'is_active',
    )

    search_fields = (
        'title',
        'phone_number',
    )

    list_editable = (
        'is_active',
    )

    ordering = ('-created_at',)

    fieldsets = (
        ('اطلاعات شماره تماس', {
            'fields': ('title', 'phone_number', 'phone_type')
        }),
        ('وضعیت', {
            'fields': ('is_active',)
        }),
        ('اطلاعات سیستمی', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('created_at',)


# ============================================================
# تنظیمات فروشگاه
# ============================================================

@admin.register(SettingShop)
class SettingShopAdmin(admin.ModelAdmin):
    list_display = (
        'name_shop',
        'establishment_year',
        'is_call',
        'emergency_phone',
        'updated_at',
    )

    list_filter = (
        'is_call',
    )

    search_fields = (
        'name_shop',
        'about_shop',
    )

    ordering = ('-updated_at',)

    fieldsets = (
        ('اطلاعات اصلی فروشگاه', {
            'fields': (
                'name_shop',
                'establishment_year',
                'about_shop',
                'logo',
            )
        }),
        ('توضیحات تکمیلی (سئو)', {
            'fields': ('description',),
            'description': 'این متن در صفحه فروشگاه نمایش داده می‌شود و برای سئو استفاده می‌شود.'
        }),
        ('تنظیمات تماس', {
            'fields': (
                'is_call',
                'emergency_phone',
            )
        }),
        ('اطلاعات سیستمی', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )


# ============================================================
# آمار بازدید
# ============================================================

@admin.register(UniqueVisit)
class UniqueVisitAdmin(admin.ModelAdmin):
    list_display = (
        'session_key_short',
        'user_display',
        'ip_address',
        'visit_count',
        'first_visit',
        'last_visit',
    )

    list_filter = (
        'first_visit',
        'last_visit',
        'country',
        'city',
    )

    search_fields = (
        'session_key',
        'ip_address',
        'user_agent',
        'referer',
        'user__mobileNumber',
        'user__name',
        'user__family',
    )

    readonly_fields = (
        'session_key',
        'ip_address',
        'user',
        'first_visit',
        'last_visit',
        'visit_count',
        'user_agent',
        'referer',
        'country',
        'city',
    )

    ordering = ('-first_visit',)

    date_hierarchy = 'first_visit'

    def session_key_short(self, obj):
        return obj.session_key[:12] + '...' if obj.session_key else '-'
    session_key_short.short_description = 'کلید جلسه'

    def user_display(self, obj):
        if obj.user:
            name = f"{obj.user.name or ''} {obj.user.family or ''}".strip()
            return name or str(obj.user.mobileNumber)
        return 'ناشناس'
    user_display.short_description = 'کاربر'


@admin.register(DailyStat)
class DailyStatAdmin(admin.ModelAdmin):
    list_display = (
        'date',
        'unique_visitors',
        'total_visits',
        'page_views',
    )

    list_filter = (
        'date',
    )

    search_fields = (
        'date',
    )

    ordering = ('-date',)

    date_hierarchy = 'date'


@admin.register(PageVisit)
class PageVisitAdmin(admin.ModelAdmin):
    list_display = (
        'visit_display',
        'path',
        'method',
        'status_code',
        'response_time_display',
        'created_at',
    )

    list_filter = (
        'method',
        'status_code',
        'created_at',
    )

    search_fields = (
        'url',
        'path',
        'visit__session_key',
        'visit__ip_address',
    )

    readonly_fields = (
        'visit',
        'url',
        'path',
        'method',
        'status_code',
        'response_time',
        'created_at',
    )

    ordering = ('-created_at',)

    date_hierarchy = 'created_at'

    def visit_display(self, obj):
        return str(obj.visit)
    visit_display.short_description = 'بازدید'

    def response_time_display(self, obj):
        if obj.response_time is not None:
            return f"{obj.response_time:.0f} ms"
        return '-'
    response_time_display.short_description = 'زمان پاسخ'