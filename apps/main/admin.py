from django.contrib import admin
from django.utils.html import format_html
from .models import TextImageBlock


@admin.register(TextImageBlock)
class TextImageBlockAdmin(admin.ModelAdmin):
    list_display = ("title", "image_position", "order")
    search_fields = ("title", "text",)





from django.contrib import admin
from .models import Content

@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'description']
    list_editable = ['is_active']
    list_per_page = 20

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('title', 'image', 'description', 'is_active')
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at']

    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-created_at')