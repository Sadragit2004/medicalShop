# apps/order/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderDetail
import jdatetime
from django.contrib import messages
from django.utils import timezone

# ========================
# اینلاین برای جزئیات سفارش
# ========================
class OrderDetailInline(admin.TabularInline):
    model = OrderDetail
    extra = 0
    readonly_fields = ['get_total_price']
    fields = ['product', 'brand', 'qty', 'price', 'selectedOptions', 'get_total_price']

    def get_total_price(self, obj):
        return f"{obj.getTotalPrice():,} تومان"
    get_total_price.short_description = "قیمت کل"

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

# ========================
# ادمین سفارش
# ========================
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'orderCode',
        'customer',
        'get_jalali_register_date',
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
        'registerDate',
        'updateDate',
        'get_total_price',
        'get_final_price',
        'get_address_details'
    ]

    fieldsets = (
        ('اطلاعات اصلی سفارش', {
            'fields': (
                'orderCode',
                'customer',
                ('registerDate', 'updateDate'),
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

    def get_jalali_register_date(self, obj):
        try:
            return jdatetime.datetime.fromgregorian(datetime=obj.registerDate).strftime('%Y/%m/%d %H:%M')
        except:
            return obj.registerDate.strftime('%Y/%m/%d %H:%M')
    get_jalali_register_date.short_description = "تاریخ ثبت"
    get_jalali_register_date.admin_order_field = 'registerDate'

    def get_total_price(self, obj):
        return f"{obj.getTotalPrice():,} تومان"
    get_total_price.short_description = "جمع کل"

    def get_final_price(self, obj):
        return f"{obj.getFinalPrice():,} تومان"
    get_final_price.short_description = "مبلغ نهایی"

    def get_address_details(self, obj):
        if obj.address:
            return obj.address.fullAddress()
        return "آدرسی ثبت نشده"
    get_address_details.short_description = "جزئیات آدرس"

    def get_form(self, request, obj=None, **kwargs):
        """ذخیره وضعیت قبلی برای تشخیص تغییر"""
        form = super().get_form(request, obj, **kwargs)
        if obj:
            # ذخیره وضعیت قبلی برای استفاده در save_model
            obj._original_status = obj.status
        return form

    def save_model(self, request, obj, form, change):
        """ذخیره سفارش و مدیریت اعلان‌ها"""
        if change:
            # اگر وضعیت تغییر کرده باشد
            if hasattr(obj, '_original_status') and obj._original_status != obj.status:
                # اعلان توسط متد save مدل ارسال می‌شود
                messages.info(request, f"وضعیت سفارش از '{obj._original_status}' به '{obj.status}' تغییر کرد.")

        super().save_model(request, obj, form, change)

    def mark_as_delivered(self, request, queryset):
        """علامت‌گذاری سفارش‌ها به عنوان تحویل شده"""
        updated = queryset.update(status='delivered', updateDate=timezone.now())
        self.message_user(request, f"{updated} سفارش به وضعیت 'تحویل شده' تغییر یافت.")
    mark_as_delivered.short_description = "علامت‌گذاری به عنوان تحویل شده"

    def mark_as_canceled(self, request, queryset):
        """علامت‌گذاری سفارش‌ها به عنوان لغو شده"""
        updated = queryset.update(status='canceled', updateDate=timezone.now())
        self.message_user(request, f"{updated} سفارش به وضعیت 'لغو شده' تغییر یافت.")
    mark_as_canceled.short_description = "علامت‌گذاری به عنوان لغو شده"

    def export_orders(self, request, queryset):
        """اکسپورت سفارش‌های انتخاب شده"""
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
        return f"{obj.getTotalPrice():,} تومان"
    get_total_price_display.short_description = "قیمت کل"

    def has_options(self, obj):
        return "✓" if obj.selectedOptions else "✗"
    has_options.short_description = "ویژگی‌ها"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'order', 'product', 'brand'
        )


from django.contrib import admin
from .models import State, City, UserAddress


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


@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    list_display = ("user", "state", "city", "postalCode", "createdAt")
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
    readonly_fields = ("createdAt",)
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
            "fields": ("createdAt",),
        }),
    )

    def full_address(self, obj):
        return obj.fullAddress()
    full_address.short_description = "آدرس کامل"

    def coordinates_display(self, obj):
        lat, lng = obj.coordinates()
        return f"{lat}, {lng}" if lat and lng else "-"
    coordinates_display.short_description = "مختصات"


