from django.contrib import admin
from django.shortcuts import get_object_or_404
from .models import Product, DiscountBasket, DiscountDetail, Copon

# Register your models here.

@admin.register(Copon)
class CoponAdmin(admin.ModelAdmin):
    list_display = ('copon', 'startDate', 'endDate', 'discount', 'isActive',)
    ordering = ('isActive',)


class DiscountBasketDetail(admin.TabularInline):
    model = DiscountDetail
    extra = 1


@admin.register(DiscountBasket)
class DiscountBasketAdmin(admin.ModelAdmin):
    list_display = ('discountTitle', 'startDate', 'endDate', 'discount', 'isActive',)
    ordering = ('isActive',)
    inlines = [DiscountBasketDetail]

    # اکشن برای اضافه کردن تمام محصولات به سبد تخفیف
    actions = ['add_all_products']

    def add_all_products(self, request, queryset):
        # بررسی اینکه فقط یک سبد تخفیف انتخاب شده باشد
        if queryset.count() != 1:
            self.message_user(request, "لطفا تنها یک سبد تخفیف انتخاب کنید", level='error')
            return

        discount_basket = queryset.first()

        # اضافه کردن تمام محصولات به سبد تخفیف
        products = Product.objects.all()
        for product in products:
            DiscountDetail.objects.get_or_create(discountBasket=discount_basket, product=product)

        self.message_user(request, "تمام محصولات به سبد تخفیف اضافه شدند")

    add_all_products.short_description = "اضافه کردن تمام محصولات به سبد تخفیف"