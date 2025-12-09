# admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse


from .models.product import Product
from .models.category import ProductCategory
from .models.attribute import Attribute,AttributeGroup,ProductAttributeValue
from .models.brand import Brand
from decimal import Decimal

# ========== INLINE MODELS ==========

class ProductAttributeValueInline(admin.TabularInline):
    """
    Inline برای مدیریت مقادیر ویژگی‌های محصول
    """
    model = ProductAttributeValue
    extra = 1
    fields = ['attribute', 'display_value']
    readonly_fields = ['display_value']
    autocomplete_fields = ['attribute']

    def display_value(self, obj):
        """نمایش مقدار ویژگی"""
        return obj.get_value() if obj.id else "تعریف نشده"
    display_value.short_description = "مقدار"


# ========== MODEL ADMINS ==========

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    """
    پنل ادمین دسته‌بندی‌های محصولات
    """
    list_display = [
        'title', 'parent_info', 'display_order',
        'product_count', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'parent', 'created_at']
    search_fields = ['title', 'slug', 'description']
    prepopulated_fields = {'slug': ['title']}
    list_editable = ['display_order', 'is_active']
    list_per_page = 25

    # فیلدهای قابل نمایش در فرم
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('title', 'slug', 'parent', 'description', 'image')
        }),
        ('تنظیمات نمایش', {
            'fields': ('display_order', 'is_active')
        }),
        ('تنظیمات SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
    )

    def parent_info(self, obj):
        """نمایش اطلاعات والد"""
        if obj.parent:
            return f"← {obj.parent.title}"
        return "ریشه"
    parent_info.short_description = "والد"
    parent_info.admin_order_field = 'parent__title'

    def product_count(self, obj):
        """تعداد محصولات این دسته‌بندی"""
        return obj.get_products_count()
    product_count.short_description = "تعداد محصولات"


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    """
    پنل ادمین برندها
    """
    list_display = [
        'title', 'logo_preview', 'product_count',
        'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'slug', 'description']
    prepopulated_fields = {'slug': ['title']}
    list_per_page = 25

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('title', 'slug', 'description', 'image', 'website')
        }),
        ('تنظیمات', {
            'fields': ('is_active',)
        }),
    )

    def logo_preview(self, obj):
        """پیش‌نمایش لوگو"""
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: contain;" />',
                obj.image.url
            )
        return "بدون تصویر"
    logo_preview.short_description = "لوگو"

    def product_count(self, obj):
        """تعداد محصولات این برند"""
        return obj.get_products_count()
    product_count.short_description = "تعداد محصولات"


@admin.register(AttributeGroup)
class AttributeGroupAdmin(admin.ModelAdmin):
    """
    پنل ادمین گروه‌های ویژگی
    """
    list_display = ['title', 'sort_order', 'attribute_count', 'is_active']
    list_filter = ['is_active']
    search_fields = ['title', 'slug']
    prepopulated_fields = {'slug': ['title']}
    list_editable = ['sort_order', 'is_active']

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('title', 'slug', 'sort_order', 'is_active')
        }),
    )

    def attribute_count(self, obj):
        """تعداد ویژگی‌های این گروه"""
        return obj.attributes.count()
    attribute_count.short_description = "تعداد ویژگی‌ها"


@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    """
    پنل ادمین ویژگی‌های محصول
    """
    list_display = [
        'title', 'group', 'data_type', 'is_filterable',
        'is_visible', 'sort_order', 'is_active'
    ]
    list_filter = [
        'is_active', 'group', 'data_type',
        'is_filterable', 'is_visible'
    ]
    search_fields = ['title', 'slug', 'description']
    prepopulated_fields = {'slug': ['title']}
    list_editable = ['sort_order', 'is_filterable', 'is_visible', 'is_active']
    list_per_page = 30

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('title', 'slug', 'group', 'description')
        }),
        ('تنظیمات داده', {
            'fields': ('data_type', 'options', 'unit')
        }),
        ('محدودیت‌ها', {
            'fields': ('min_value', 'max_value', 'max_length'),
            'classes': ('collapse',)
        }),
        ('تنظیمات نمایش', {
            'fields': (
                'is_required', 'is_filterable',
                'is_visible', 'sort_order'
            )
        }),
        ('ساختار سلسله‌مراتبی', {
            'fields': ('parent',),
            'classes': ('collapse',)
        }),
        ('وضعیت', {
            'fields': ('is_active',)
        }),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """فیلتر کردن ویژگی والد (برای جلوگیری از حلقه)"""
        if db_field.name == "parent":
            # فقط ویژگی‌های فعال را نشان بده
            kwargs["queryset"] = Attribute.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    پنل ادمین محصولات
    """
    list_display = [
        'main_image_preview', 'title', 'price_display',
        'stock_status', 'category_list', 'is_active',
        'created_at'
    ]
    list_filter = [
        'is_active', 'categories', 'brand',
        'created_at', 'is_wholesale_enabled'
    ]
    search_fields = ['title', 'slug', 'description', 'sku']
    prepopulated_fields = {'slug': ['title']}
    list_editable = ['is_active']
    list_per_page = 25

    # Inline برای ویژگی‌ها
    inlines = [ProductAttributeValueInline]

    # فیلتر کردن دسته‌بندی‌ها
    filter_horizontal = ['categories']

    # فیلدهای قابل نمایش در فرم
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': (
                'title', 'slug', 'description',
                'categories', 'brand', 'main_image'
            )
        }),
        ('قیمت‌گذاری', {
            'fields': (
                'price', 'sale_price',
                ('is_wholesale_enabled', 'wholesale_min_quantity', 'wholesale_discount_percent')
            )
        }),
        ('موجودی و فروش', {
            'fields': (
                'stock_quantity',
                ('min_quantity', 'max_quantity'),
                ('is_packaged', 'items_per_package')
            )
        }),
        ('وزن و ابعاد', {
            'fields': ('weight_grams', 'dimensions'),
            'classes': ('collapse',)
        }),
        ('تنظیمات SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('وضعیت', {
            'fields': ('is_active',)
        }),
    )

    # متدهای کمکی برای نمایش بهتر
    def main_image_preview(self, obj):
        """پیش‌نمایش عکس اصلی"""
        if obj.main_image:
            return format_html(
                '<img src="{}" width="60" height="60" style="object-fit: cover; border-radius: 4px;" />',
                obj.main_image.url
            )
        return "بدون تصویر"
    main_image_preview.short_description = "تصویر"

    def price_display(self, obj):
        """نمایش قیمت با فرمت مناسب"""
        print(f"DEBUG: obj.price = {obj.price}, type = {type(obj.price)}")
        print(f"DEBUG: obj.sale_price = {obj.sale_price}, type = {type(obj.sale_price)}")

        # دیباگ بیشتر
        if obj.price is None:
            print("DEBUG: obj.price is None")
        elif isinstance(obj.price, str):
            print(f"DEBUG: obj.price is string: '{obj.price}'")
        elif isinstance(obj.price, Decimal):
            print(f"DEBUG: obj.price is Decimal: {obj.price}")

        try:
            # تبدیل به عدد
            if obj.price is None:
                price_value = 0
            elif isinstance(obj.price, str):
                # حذف کاماها و فضاها اگر وجود دارد
                cleaned = obj.price.replace(',', '').replace(' ', '').strip()
                price_value = int(float(cleaned)) if cleaned else 0
            elif isinstance(obj.price, (Decimal, int, float)):
                price_value = int(obj.price)
            else:
                price_value = 0

            if obj.sale_price is None:
                sale_price_value = 0
            elif isinstance(obj.sale_price, str):
                cleaned = obj.sale_price.replace(',', '').replace(' ', '').strip()
                sale_price_value = int(float(cleaned)) if cleaned else 0
            elif isinstance(obj.sale_price, (Decimal, int, float)):
                sale_price_value = int(obj.sale_price)
            else:
                sale_price_value = 0

            print(f"DEBUG: price_value = {price_value}, sale_price_value = {sale_price_value}")

            if obj.sale_price and sale_price_value > 0:
                return format_html(
                    '<span style="text-decoration: line-through; color: #999;">{:,} تومان</span><br>'
                    '<span style="color: #e53935; font-weight: bold;">{:,} تومان</span>',
                    price_value, sale_price_value
                )
            return format_html('<span>{:,} تومان</span>', price_value)

        except Exception as e:
            print(f"DEBUG: Error in price_display: {e}")
            # نمایش ساده بدون فرمت
            return str(obj.price) if obj.price else "۰ تومان"

    price_display.short_description = "قیمت (تومان)"

    def stock_status(self, obj):
        """وضعیت موجودی"""
        if obj.stock_quantity == 0:
            return format_html(
                '<span style="color: #f44336; font-weight: bold;">ناموجود</span>'
            )
        elif obj.stock_quantity < 10:
            return format_html(
                '<span style="color: #ff9800; font-weight: bold;">کم موجود ({})</span>',
                obj.stock_quantity
            )
        else:
            return format_html(
                '<span style="color: #4caf50; font-weight: bold;">موجود ({})</span>',
                obj.stock_quantity
            )
    stock_status.short_description = "وضعیت موجودی"

    def category_list(self, obj):
        """لیست دسته‌بندی‌ها"""
        categories = obj.categories.filter(is_active=True)
        if categories:
            links = []
            for cat in categories[:3]:  # فقط ۳ دسته‌بندی اول
                url = reverse('admin:product_productcategory_change', args=[cat.id])
                links.append(f'<a href="{url}">{cat.title}</a>')
            result = ', '.join(links)
            if categories.count() > 3:
                result += f' و {categories.count() - 3} مورد دیگر'
            return format_html(result)
        return "بدون دسته‌بندی"
    category_list.short_description = "دسته‌بندی‌ها"

    # اکشن‌های سفارشی
    actions = ['activate_products', 'deactivate_products', 'clear_stock']

    def activate_products(self, request, queryset):
        """فعال کردن محصولات انتخاب شده"""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{updated} محصول با موفقیت فعال شد.'
        )
    activate_products.short_description = "فعال کردن محصولات انتخاب شده"

    def deactivate_products(self, request, queryset):
        """غیرفعال کردن محصولات انتخاب شده"""
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{updated} محصول با موفقیت غیرفعال شد.'
        )
    deactivate_products.short_description = "غیرفعال کردن محصولات انتخاب شده"

    def clear_stock(self, request, queryset):
        """خالی کردن موجودی محصولات انتخاب شده"""
        updated = queryset.update(stock_quantity=0)
        self.message_user(
            request,
            f'موجودی {updated} محصول صفر شد.'
        )
    clear_stock.short_description = "صفر کردن موجودی"


@admin.register(ProductAttributeValue)
class ProductAttributeValueAdmin(admin.ModelAdmin):
    """
    پنل ادمین مقادیر ویژگی‌های محصول (اختیاری)
    """
    list_display = ['product', 'attribute', 'value_display', 'created_at']
    list_filter = ['attribute', 'created_at']
    search_fields = ['product__title', 'attribute__title']
    autocomplete_fields = ['product', 'attribute']
    list_per_page = 50

    def value_display(self, obj):
        """نمایش مقدار ویژگی"""
        value = obj.get_value()
        if isinstance(value, list):
            return ', '.join(str(v) for v in value)
        return str(value) if value is not None else "تعریف نشده"
    value_display.short_description = "مقدار"


# ========== CUSTOM ADMIN SITE ==========

class CustomAdminSite(admin.AdminSite):
    """
    پنل ادمین سفارشی
    """
    site_header = "پنل مدیریت فروشگاه"
    site_title = "مدیریت فروشگاه"
    index_title = "خوش آمدید به پنل مدیریت"

    def get_app_list(self, request):
        """
        سفارشی‌سازی ترتیب اپ‌ها
        """
        app_list = super().get_app_list(request)

        # تغییر ترتیب اپ‌ها
        app_ordering = {
            'product': 1,
            'auth': 2,
        }

        # مرتب‌سازی اپ‌ها بر اساس ترتیب تعریف شده
        app_list.sort(key=lambda x: app_ordering.get(x['app_label'], 999))

        return app_list




# product_app/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models.gallery import ProductGallery

class ProductGalleryAdmin(admin.ModelAdmin):
    """
    ادمین برای گالری تصاویر محصولات
    """
    list_display = ['id', 'product', 'display_image', 'title', 'is_main', 'sort_order', 'is_active']
    list_filter = ['is_main', 'is_active', 'product__title']
    search_fields = ['product__title', 'title']
    list_editable = ['is_main', 'sort_order', 'is_active']
    list_per_page = 20
    ordering = ['product', 'sort_order']

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('product', 'title', 'image')
        }),
        ('تنظیمات نمایش', {
            'fields': ('is_main', 'sort_order')
        }),
        ('تنظیمات فعال بودن', {
            'fields': ('is_active',)
        }),
    )

    def display_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 5px;" />', obj.image.url)
        return "بدون تصویر"
    display_image.short_description = 'تصویر'

admin.site.register(ProductGallery, ProductGalleryAdmin)



# ثبت در پنل ادمین پیش‌فرض
admin.site.site_header = "پنل مدیریت فروشگاه"
admin.site.site_title = "مدیریت فروشگاه"
admin.site.index_title = "خوش آمدید به پنل مدیریت"

# یا اگر می‌خواهید از پنل سفارشی استفاده کنید:
# custom_admin_site = CustomAdminSite(name='custom_admin')
# custom_admin_site.register(Product, ProductAdmin)
# custom_admin_site.register(ProductCategory, ProductCategoryAdmin)
# custom_admin_site.register(Brand, BrandAdmin)
# custom_admin_site.register(AttributeGroup, AttributeGroupAdmin)
# custom_admin_site.register(Attribute, AttributeAdmin)
# custom_admin_site.register(ProductAttributeValue, ProductAttributeValueAdmin)