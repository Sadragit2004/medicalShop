from django.contrib import admin
from django.utils.html import format_html
from .models import *




@admin.register(SliderSite)
class SliderSiteAdmin(admin.ModelAdmin):
    list_display = ['textSlider', 'isActive', 'registerData', 'endData', 'image_preview']
    list_filter = ['isActive', 'registerData', 'endData']
    search_fields = ['textSlider', 'altSlide']
    readonly_fields = ['registerData']

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

    def image_preview(self, obj):
        if obj.imageName:
            return format_html('<img src="{}" style="width: 100px; height: auto;" />', obj.imageName.url)
        return "بدون تصویر"

    image_preview.short_description = 'پیش‌نمایش تصویر'




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
