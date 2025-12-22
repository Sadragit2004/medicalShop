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