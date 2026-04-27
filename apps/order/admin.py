from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderDetail, State, City, UserAddress
import jdatetime
from django.contrib import messages
from django.utils import timezone

# ========================
# تابع تبدیل تاریخ به شمسی (نسخه قوی)
# ========================
# apps/order/admin.py - تابع to_jalali رو اینطور عوض کن

import jdatetime
from django.utils import timezone

def to_jalali(dt):
    """تبدیل تاریخ میلادی به شمسی با در نظر گرفتن منطقه زمانی"""
    if not dt:
        return "-"
    try:
        # اگه datetime با timezone باشه، اول به منطقه زمانی تهران تبدیل کن
        if timezone.is_aware(dt):
            tehran_tz = timezone.get_current_timezone()
            dt = dt.astimezone(tehran_tz)

        # حالا تبدیل به شمسی
        return jdatetime.datetime.fromgregorian(datetime=dt).strftime('%Y/%m/%d %H:%M:%S')
    except:
        try:
            return jdatetime.date.fromgregorian(date=dt).strftime('%Y/%m/%d')
        except:
            return str(dt)
# ========================
# اینلاین برای جزئیات سفارش
# ========================
class OrderDetailInline(admin.TabularInline):
    model = OrderDetail
    extra = 0
    readonly_fields = ['get_total_price', 'get_jalali_created_at']
    fields = ['product', 'brand', 'qty', 'price', 'selectedOptions', 'get_total_price']
    can_delete = False

    def get_total_price(self, obj):
        try:
            return f"{obj.getTotalPrice():,} تومان"
        except:
            return "0 تومان"
    get_total_price.short_description = "قیمت کل"

    def get_jalali_created_at(self, obj):
        return to_jalali(obj.order.registerDate) if obj.order else "-"
    get_jalali_created_at.short_description = "تاریخ ثبت"


# ========================
# ادمین سفارش
# ========================
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'orderCode',
        'customer',
        'get_jalali_register_date',
        'get_jalali_update_date',
        'status',
        'isFinally',
        'get_total_price',
        'get_final_price',
        'discount'
    ]

    list_filter = [
        'status',
        'isFinally',
        'registerDate',
        'updateDate'
    ]

    search_fields = [
        'orderCode',
        'customer__username',
        'customer__email',
        'customer__first_name',
        'customer__last_name'
    ]

    readonly_fields = [
        'orderCode',
        'get_jalali_register_date_readonly',
        'get_jalali_update_date_readonly',
        'get_total_price',
        'get_final_price',
        'get_address_details'
    ]

    fieldsets = (
        ('اطلاعات اصلی سفارش', {
            'fields': (
                'orderCode',
                'customer',
                ('get_jalali_register_date_readonly', 'get_jalali_update_date_readonly'),
            )
        }),
        ('وضعیت سفارش', {
            'fields': (
                'status',
                'isFinally',
                'discount',
                'address',
                'get_address_details',
            )
        }),
        ('محاسبات مالی', {
            'fields': (
                'get_total_price',
                'get_final_price',
            )
        }),
        ('توضیحات', {
            'fields': ('description',)
        }),
    )

    inlines = [OrderDetailInline]
    actions = ['mark_as_delivered', 'mark_as_canceled', 'export_orders']

    # ========== نمایش شمسی در لیست ==========
    def get_jalali_register_date(self, obj):
        return to_jalali(obj.registerDate)
    get_jalali_register_date.short_description = "تاریخ ثبت (شمسی)"
    get_jalali_register_date.admin_order_field = 'registerDate'

    def get_jalali_update_date(self, obj):
        return to_jalali(obj.updateDate)
    get_jalali_update_date.short_description = "تاریخ ویرایش (شمسی)"
    get_jalali_update_date.admin_order_field = 'updateDate'

    # ========== نمایش شمسی در صفحه جزئیات ==========
    def get_jalali_register_date_readonly(self, obj):
        return to_jalali(obj.registerDate)
    get_jalali_register_date_readonly.short_description = "تاریخ ثبت (شمسی)"

    def get_jalali_update_date_readonly(self, obj):
        return to_jalali(obj.updateDate)
    get_jalali_update_date_readonly.short_description = "تاریخ ویرایش (شمسی)"

    # ========== محاسبات مالی ==========
    def get_total_price(self, obj):
        try:
            return f"{obj.getTotalPrice():,} تومان"
        except:
            return "0 تومان"
    get_total_price.short_description = "جمع کل"

    def get_final_price(self, obj):
        try:
            return f"{obj.getFinalPrice():,} تومان"
        except:
            return "0 تومان"
    get_final_price.short_description = "مبلغ نهایی"

    def get_address_details(self, obj):
        if obj.address:
            return obj.address.fullAddress()
        return "آدرسی ثبت نشده"
    get_address_details.short_description = "جزئیات آدرس"

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj:
            obj._original_status = obj.status
        return form

    def save_model(self, request, obj, form, change):
        if change:
            if hasattr(obj, '_original_status') and obj._original_status != obj.status:
                messages.info(request, f"وضعیت سفارش از '{obj._original_status}' به '{obj.status}' تغییر کرد.")
        super().save_model(request, obj, form, change)

    def mark_as_delivered(self, request, queryset):
        updated = queryset.update(status='delivered', updateDate=timezone.now())
        self.message_user(request, f"{updated} سفارش به وضعیت 'تحویل شده' تغییر یافت.")
    mark_as_delivered.short_description = "علامت‌گذاری به عنوان تحویل شده"

    def mark_as_canceled(self, request, queryset):
        updated = queryset.update(status='canceled', updateDate=timezone.now())
        self.message_user(request, f"{updated} سفارش به وضعیت 'لغو شده' تغییر یافت.")
    mark_as_canceled.short_description = "علامت‌گذاری به عنوان لغو شده"

    def export_orders(self, request, queryset):
        self.message_user(request, f"{queryset.count()} سفارش برای اکسپورت انتخاب شد.")
    export_orders.short_description = "اکسپورت سفارش‌ها"


# ========================
# ادمین جزئیات سفارش
# ========================
@admin.register(OrderDetail)
class OrderDetailAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'order',
        'product',
        'brand',
        'qty',
        'price',
        'get_total_price_display',
        'has_options'
    ]

    list_filter = [
        'brand',
        'order__status',
        'order__isFinally'
    ]

    search_fields = [
        'order__orderCode',
        'product__title',
        'brand__title'
    ]

    readonly_fields = [
        'get_total_price_display'
    ]

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': (
                'order',
                'product',
                'brand',
            )
        }),
        ('مشخصات خرید', {
            'fields': (
                'qty',
                'price',
                'get_total_price_display',
            )
        }),
        ('ویژگی‌های انتخابی', {
            'fields': ('selectedOptions',)
        }),
    )

    def get_total_price_display(self, obj):
        try:
            return f"{obj.getTotalPrice():,} تومان"
        except:
            return "0 تومان"
    get_total_price_display.short_description = "قیمت کل"

    def has_options(self, obj):
        return "✓" if obj.selectedOptions else "✗"
    has_options.short_description = "ویژگی‌ها"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'order', 'product', 'brand'
        )


# ========================
# ادمین استان
# ========================
@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ("name", "center", "externalId", "lat", "lng")
    search_fields = ("name", "center")
    ordering = ("name",)
    list_filter = ("center",)
    fieldsets = (
        ("اطلاعات کلی", {
            "fields": ("name", "center", "externalId")
        }),
        ("مختصات جغرافیایی", {
            "fields": ("lat", "lng"),
            "classes": ("collapse",)
        }),
    )
    readonly_fields = ("externalId",)


# ========================
# ادمین شهر
# ========================
@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "state", "externalId", "lat", "lng")
    search_fields = ("name", "state__name")
    list_filter = ("state",)
    ordering = ("state__name", "name")
    fieldsets = (
        ("اطلاعات شهر", {
            "fields": ("state", "name", "externalId")
        }),
        ("مختصات جغرافیایی", {
            "fields": ("lat", "lng"),
            "classes": ("collapse",)
        }),
    )
    readonly_fields = ("externalId",)


# ========================
# ادمین آدرس کاربر
# ========================
@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    list_display = ("user", "state", "city", "postalCode", "get_jalali_created_at")
    list_filter = ("state", "city")
    search_fields = (
        "user__username",
        "user__email",
        "state__name",
        "city__name",
        "addressDetail",
        "postalCode",
    )
    autocomplete_fields = ("user", "state", "city")
    readonly_fields = ("createdAt", "get_jalali_created_at_readonly")
    ordering = ("-createdAt",)
    fieldsets = (
        ("اطلاعات کاربر", {
            "fields": ("user",)
        }),
        ("موقعیت مکانی", {
            "fields": ("state", "city", "addressDetail", "postalCode")
        }),
        ("مختصات جغرافیایی", {
            "fields": ("lat", "lng"),
            "classes": ("collapse",)
        }),
        ("زمان ثبت", {
            "fields": ("get_jalali_created_at_readonly",),
        }),
    )

    def get_jalali_created_at(self, obj):
        return to_jalali(obj.createdAt)
    get_jalali_created_at.short_description = "تاریخ ثبت (شمسی)"
    get_jalali_created_at.admin_order_field = 'createdAt'

    def get_jalali_created_at_readonly(self, obj):
        return to_jalali(obj.createdAt)
    get_jalali_created_at_readonly.short_description = "تاریخ ثبت (شمسی)"

    def full_address(self, obj):
        return obj.fullAddress()
    full_address.short_description = "آدرس کامل"

    def coordinates_display(self, obj):
        lat, lng = obj.coordinates()
        return f"{lat}, {lng}" if lat and lng else "-"
    coordinates_display.short_description = "مختصات"