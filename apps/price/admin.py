from django.contrib import admin
from .models import ProductPriceHistory, ProductStockHistory


@admin.register(ProductPriceHistory)
class ProductPriceHistoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'price_old', 'price_new', 'percent_change', 'change_type', 'created_at')
    list_filter = ('change_type', 'source')
    search_fields = ('product__title',)
    readonly_fields = ('price_old', 'price_new', 'percent_change', 'change_type', 'created_at')


@admin.register(ProductStockHistory)
class ProductStockHistoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'stock_old', 'stock_new', 'change_type', 'created_at')
    list_filter = ('change_type',)
    search_fields = ('product__title',)
    readonly_fields = ('stock_old', 'stock_new', 'change_type', 'created_at')