from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models.user import CustomUser
from .models.security import UserSecurity
from .models.device import UserDevice


# =========================
# Custom User Admin
# =========================
@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    # ستون‌هایی که در لیست کاربران نمایش داده میشه
    list_display = ("mobileNumber", "name", "family", "email", "gender", "is_active", "is_staff", "is_superuser",)
    list_filter = ("is_active", "is_superuser", "gender",)
    search_fields = ("mobileNumber", "name", "family", "email")
    ordering = ("-id",)

    fieldsets = (
        (None, {"fields": ("mobileNumber", "password")}),
        (_("اطلاعات شخصی"), {"fields": ("name", "family", "email", "gender")}),
        (_("سطوح دسترسی"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("تاریخ‌ها"), {"fields": ("last_login",)}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("mobileNumber", "password1", "password2", "name", "family", "email", "gender", "is_active", "is_staff", "is_superuser"),
        }),
    )


# =========================
# User Security Admin
# =========================
@admin.register(UserSecurity)
class UserSecurityAdmin(admin.ModelAdmin):
    list_display = ("user", "activeCode", "expireCode", "isBan", "isInfoFiled", "createdAt")
    list_filter = ("isBan", "isInfoFiled")
    search_fields = ("user__mobileNumber", "activeCode")
    ordering = ("-createdAt",)


# =========================
# User Device Admin
# =========================
@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display = ("user", "deviceInfo", "ipAddress", "createdAt")
    search_fields = ("user__mobileNumber", "deviceInfo", "ipAddress")
    list_filter = ("createdAt",)
    ordering = ("-createdAt",)
