from django.urls import path
from . import views

app_name = 'price'

urlpatterns = [
    # صفحه اصلی UI
    path('', views.showUiPrice, name='price_ui'),

    # دریافت لیست محصولات و اطلاعات
    path('api/products/', views.get_products_list, name='api_products_list'),
    path('api/product/<int:product_id>/', views.get_product_detail, name='api_product_detail'),

    # عملیات قیمت
    path('api/product/update-price/', views.update_product_price, name='api_update_price'),
    path('api/product/<int:product_id>/price-history/', views.get_price_history, name='api_price_history'),
    path('api/product/bulk-update-prices/', views.bulk_update_prices, name='api_bulk_update_prices'),

    # عملیات موجودی
    path('api/product/<int:product_id>/update-stock/', views.update_product_stock, name='api_update_stock'),
    path('api/product/<int:product_id>/set-stock-zero/', views.set_product_stock_to_zero, name='api_set_stock_zero'),
    path('api/product/<int:product_id>/restore-stock/', views.restore_product_stock, name='api_restore_stock'),
    path('api/product/<int:product_id>/stock-history/', views.get_product_stock_history, name='api_stock_history'),

    # دکمه خاموش/روشن با مدیریت موجودی (اصلی)
    path('api/product/<int:product_id>/toggle/', views.toggle_product_with_stock_management, name='api_toggle_product'),

    # آمار و دسته‌بندی
    path('api/dashboard-stats/', views.get_dashboard_stats, name='api_dashboard_stats'),
    path('api/categories/', views.get_categories_with_stats, name='api_categories_stats'),
]