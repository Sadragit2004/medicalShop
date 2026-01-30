# admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Category, Brand, Feature, FeatureValue, Product,
    ProductGallery, ProductFeature, ProductSaleType,
    Rating, Comment
)

# ========================
# فیلترهای سفارشی
# ========================
class IsActiveFilter(admin.SimpleListFilter):
    title = 'وضعیت فعال'
    parameter_name = 'is_active'

    def lookups(self, request, model_admin):
        return (
            ('active', 'فعال'),
            ('inactive', 'غیرفعال'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(isActive=True)
        if self.value() == 'inactive':
            return queryset.filter(isActive=False)


class HasParentFilter(admin.SimpleListFilter):
    title = 'دارای والد'
    parameter_name = 'has_parent'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'دارای والد'),
            ('no', 'بدون والد'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(parent__isnull=False)
        if self.value() == 'no':
            return queryset.filter(parent__isnull=True)


# ========================
# اینلاین‌ها (Inlines)
# ========================
class ProductFeatureInline(admin.TabularInline):
    model = ProductFeature
    extra = 1
    fields = ('feature', 'value', 'filterValue')


class ProductGalleryInline(admin.TabularInline):
    model = ProductGallery
    extra = 1
    fields = ('image', 'altText', 'isActive')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="60" height="60" style="object-fit:cover;border-radius:8px;" />', obj.image.url)
        return "بدون تصویر"
    image_preview.short_description = 'پیش‌نمایش'


class ProductSaleTypeInline(admin.TabularInline):
    model = ProductSaleType
    extra = 1
    fields = ('typeSale', 'price', 'memberCarton', 'limitedSale', 'finalPrice', 'isActive')


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ('user', 'product', 'createdAt')
    fields = ('user', 'text', 'typeComment', 'isActive', 'createdAt')
    can_delete = False
    max_num = 10

    def has_add_permission(self, request, obj):
        return False


class RatingInline(admin.TabularInline):
    model = Rating
    extra = 0
    readonly_fields = ('user', 'product', 'createdAt')
    fields = ('user', 'rating', 'createdAt')
    can_delete = False
    max_num = 10

    def has_add_permission(self, request, obj):
        return False


# ========================
# ادمین کلاس‌ها
# ========================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'parent', 'image_preview', 'isActive', 'createdAt')
    list_filter = (IsActiveFilter, HasParentFilter)
    search_fields = ('title', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    list_per_page = 20
    actions = ['make_active', 'make_inactive']

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('title', 'slug', 'parent', 'isActive','description')
        }),
        ('تصویر', {
            'fields': ('image', 'image_preview'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="60" height="60" style="object-fit:cover;border-radius:8px;" />', obj.image.url)
        return "بدون تصویر"
    image_preview.short_description = 'پیش‌نمایش'

    def make_active(self, request, queryset):
        updated = queryset.update(isActive=True)
        self.message_user(request, f'{updated} دسته‌بندی فعال شدند.')
    make_active.short_description = 'فعال کردن دسته‌بندی‌های انتخاب شده'

    def make_inactive(self, request, queryset):
        updated = queryset.update(isActive=False)
        self.message_user(request, f'{updated} دسته‌بندی غیرفعال شدند.')
    make_inactive.short_description = 'غیرفعال کردن دسته‌بندی‌های انتخاب شده'


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('title', 'logo_preview', 'product_count', 'isActive', 'createdAt')
    list_filter = (IsActiveFilter,)
    search_fields = ('title', 'slug', 'description')
    prepopulated_fields = {'slug': ('title',)}
    list_per_page = 20
    actions = ['make_active', 'make_inactive']

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('title', 'slug', 'description', 'isActive')
        }),
        ('لوگو', {
            'fields': ('logo', 'logo_preview'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('logo_preview',)

    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" width="60" height="60" style="object-fit:contain;border-radius:8px;" />', obj.logo.url)
        return "بدون لوگو"
    logo_preview.short_description = 'پیش‌نمایش'

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'تعداد محصولات'

    def make_active(self, request, queryset):
        updated = queryset.update(isActive=True)
        self.message_user(request, f'{updated} برند فعال شدند.')

    def make_inactive(self, request, queryset):
        updated = queryset.update(isActive=False)
        self.message_user(request, f'{updated} برند غیرفعال شدند.')


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ('title', 'categories_count', 'isActive', 'createdAt')
    list_filter = (IsActiveFilter, 'categories')
    search_fields = ('title', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('categories',)
    list_per_page = 20

    def categories_count(self, obj):
        return obj.categories.count()
    categories_count.short_description = 'تعداد دسته‌بندی‌ها'


@admin.register(FeatureValue)
class FeatureValueAdmin(admin.ModelAdmin):
    list_display = ('feature', 'value', 'created_at')
    list_filter = ('feature',)
    search_fields = ('value', 'feature__title')
    list_per_page = 20

    def created_at(self, obj):
        return obj.feature.createdAt if obj.feature else '-'
    created_at.short_description = 'تاریخ ایجاد'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'brand', 'main_image_preview', 'price_range', 'average_rating_display', 'isActive', 'createdAt')
    list_filter = (IsActiveFilter, 'brand', 'category')
    search_fields = ('title', 'slug', 'description', 'shortDescription')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('category',)
    list_per_page = 20
    inlines = [ProductFeatureInline, ProductGalleryInline, ProductSaleTypeInline]
    actions = ['make_active', 'make_inactive']

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('title', 'slug', 'brand', 'category', 'isActive')
        }),
        ('تصاویر', {
            'fields': ('mainImage', 'main_image_preview'),
            'classes': ('collapse',)
        }),
        ('توضیحات', {
            'fields': ('shortDescription', 'description')
        }),
    )

    readonly_fields = ('main_image_preview',)

    def main_image_preview(self, obj):
        if obj.mainImage:
            return format_html('<img src="{}" width="80" height="80" style="object-fit:cover;border-radius:8px;" />', obj.mainImage.url)
        return "بدون تصویر"
    main_image_preview.short_description = 'پیش‌نمایش'

    def price_range(self, obj):
        sale_types = obj.saleTypes.filter(isActive=True)
        if sale_types.exists():
            prices = [st.price for st in sale_types]
            min_price = min(prices)
            max_price = max(prices)
            if min_price == max_price:
                return f"{min_price:,}"
            return f"{min_price:,} - {max_price:,}"
        return "بدون قیمت"
    price_range.short_description = 'محدوده قیمت'

    def average_rating_display(self, obj):
        avg = obj.average_rating
        stars = "★" * int(avg) + "☆" * (5 - int(avg))
        return f"{avg} {stars}"
    average_rating_display.short_description = 'امتیاز'

    def make_active(self, request, queryset):
        updated = queryset.update(isActive=True)
        self.message_user(request, f'{updated} محصول فعال شدند.')

    def make_inactive(self, request, queryset):
        updated = queryset.update(isActive=False)
        self.message_user(request, f'{updated} محصول غیرفعال شدند.')


@admin.register(ProductSaleType)
class ProductSaleTypeAdmin(admin.ModelAdmin):
    list_display = ('product', 'typeSale_display', 'price', 'finalPrice', 'isActive')
    list_filter = ('typeSale', IsActiveFilter, 'product__brand')
    search_fields = ('product__title', 'product__slug')
    list_per_page = 20
    actions = ['make_active', 'make_inactive']

    def typeSale_display(self, obj):
        return dict(SaleType.CHOICES).get(obj.typeSale, 'نامشخص')
    typeSale_display.short_description = 'نوع فروش'

    def make_active(self, request, queryset):
        updated = queryset.update(isActive=True)
        self.message_user(request, f'{updated} نوع فروش فعال شدند.')

    def make_inactive(self, request, queryset):
        updated = queryset.update(isActive=False)
        self.message_user(request, f'{updated} نوع فروش غیرفعال شدند.')


@admin.register(ProductFeature)
class ProductFeatureAdmin(admin.ModelAdmin):
    list_display = ('product', 'feature', 'value', 'filterValue')
    list_filter = ('feature', 'product__brand')
    search_fields = ('product__title', 'feature__title', 'value')
    list_per_page = 20


@admin.register(ProductGallery)
class ProductGalleryAdmin(admin.ModelAdmin):
    list_display = ('product', 'image_preview', 'altText', 'isActive')
    list_filter = (IsActiveFilter, 'product__brand')
    search_fields = ('product__title', 'altText')
    list_per_page = 20
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="80" height="80" style="object-fit:cover;border-radius:8px;" />', obj.image.url)
        return "بدون تصویر"
    image_preview.short_description = 'پیش‌نمایش'


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'rating_stars', 'createdAt')
    list_filter = ('rating', 'createdAt')
    search_fields = ('user__username', 'user__email', 'product__title')
    list_per_page = 20
    readonly_fields = ('user', 'product', 'createdAt')

    def rating_stars(self, obj):
        stars = "★" * obj.rating + "☆" * (5 - obj.rating)
        return stars
    rating_stars.short_description = 'امتیاز'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'typeComment_display', 'text_preview', 'isActive', 'createdAt')
    list_filter = ('typeComment', 'isActive', 'createdAt')
    search_fields = ('user__username', 'user__email', 'product__title', 'text')
    list_per_page = 20
    actions = ['make_active', 'make_inactive', 'mark_as_recommend', 'mark_as_not_recommend']
    readonly_fields = ('user', 'product', 'createdAt')

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('user', 'product', 'typeComment', 'isActive', 'createdAt')
        }),
        ('متن کامنت', {
            'fields': ('text',)
        }),
    )

    def typeComment_display(self, obj):
        return dict(Comment.COMMENT_TYPES).get(obj.typeComment, 'نامشخص')
    typeComment_display.short_description = 'نوع کامنت'

    def text_preview(self, obj):
        if len(obj.text) > 50:
            return f"{obj.text[:50]}..."
        return obj.text
    text_preview.short_description = 'متن'

    def make_active(self, request, queryset):
        updated = queryset.update(isActive=True)
        self.message_user(request, f'{updated} کامنت فعال شدند.')

    def make_inactive(self, request, queryset):
        updated = queryset.update(isActive=False)
        self.message_user(request, f'{updated} کامنت غیرفعال شدند.')

    def mark_as_recommend(self, request, queryset):
        updated = queryset.update(typeComment='recommend')
        self.message_user(request, f'{updated} کامنت به "پیشنهاد می‌کنم" تغییر یافت.')

    def mark_as_not_recommend(self, request, queryset):
        updated = queryset.update(typeComment='not_recommend')
        self.message_user(request, f'{updated} کامنت به "پیشنهاد نمی‌کنم" تغییر یافت.')