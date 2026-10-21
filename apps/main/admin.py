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




import os
from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.http import FileResponse, Http404
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import DatabaseBackup


@admin.register(DatabaseBackup)
class DatabaseBackupAdmin(admin.ModelAdmin):
    list_display = (
        "filename",
        "status_badge",
        "file_size_display",
        "file_exists_display",
        "download_link",
        "created_at",
        "completed_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "filename",
        "file_path",
        "error_message",
    )

    readonly_fields = (
        "filename",
        "file_path",
        "file_size",
        "status",
        "error_message",
        "created_at",
        "completed_at",
        "file_exists_display",
        "file_size_display",
    )

    ordering = ("-created_at",)
    list_per_page = 25

    def get_urls(self):
        custom_urls = [
            path(
                "<int:backup_id>/download/",
                self.admin_site.admin_view(self.download_backup),
                name="main_databasebackup_download",
            ),
        ]
        return custom_urls + super().get_urls()

    def download_backup(self, request, backup_id):
        backup = self.get_object(request, backup_id)

        if backup is None:
            raise Http404("Backup not found.")

        if backup.status != DatabaseBackup.Status.SUCCESS.value:
            raise Http404("This backup is not available for download.")

        backup_root = (Path(settings.BASE_DIR) / "backups").resolve()
        file_path = Path(backup.file_path).resolve()

        try:
            file_path.relative_to(backup_root)
        except ValueError:
            raise Http404("Invalid backup path.")

        if not file_path.is_file():
            raise Http404("Backup file not found.")

        response = FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename=os.path.basename(backup.filename),
            content_type="application/gzip",
        )
        response["X-Content-Type-Options"] = "nosniff"
        return response

    @admin.display(description="وضعیت")
    def status_badge(self, obj):
        colors = {
            DatabaseBackup.Status.SUCCESS.value: "#198754",
            DatabaseBackup.Status.FAILED.value: "#dc3545",
            DatabaseBackup.Status.RUNNING.value: "#fd7e14",
        }

        color = colors.get(obj.status, "#6c757d")

        return format_html(
            '<span style="background:{};color:white;'
            'padding:4px 10px;border-radius:6px;">{}</span>',
            color,
            obj.get_status_display(),
        )

    @admin.display(description="حجم فایل")
    def file_size_display(self, obj):
        return f"{obj.file_size_mb} MB"

    @admin.display(description="وضعیت فایل")
    def file_exists_display(self, obj):
        if obj.file_exists:
            return format_html(
                '<span style="color:#198754;font-weight:bold;">موجود</span>'
            )

        return format_html(
            '<span style="color:#dc3545;font-weight:bold;">یافت نشد</span>'
        )

    @admin.display(description="دانلود بکاپ")
    def download_link(self, obj):
        if (
            obj.status != DatabaseBackup.Status.SUCCESS.value
            or not obj.file_exists
        ):
            return format_html(
                '<span style="color:#dc3545;">غیرقابل دانلود</span>'
            )

        url = reverse(
            "admin:main_databasebackup_download",
            args=[obj.pk],
        )

        return format_html(
            '<a href="{}" style="display:inline-block;'
            'padding:5px 12px;background:#198754;color:white;'
            'border-radius:5px;text-decoration:none;">دانلود فایل</a>',
            url,
        )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
