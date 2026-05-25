from django.urls import path
from . import views

app_name = 'price'

urlpatterns = [
    # صفحه اصلی UI
    path('', views.showUiPrice, name='price'),

    # محصولات
    path('api/products/', views.get_products_list, name='api_products_list'),
    path('api/products/<int:product_id>/', views.get_product_detail, name='api_product_detail'),

    # قیمت‌ها
    path('api/price/update/', views.update_product_price, name='api_update_price'),
    path('api/price/bulk-update/', views.bulk_update_prices, name='api_bulk_update_prices'),

    # تاریخچه
    path('api/history/<int:product_id>/', views.get_price_history, name='api_price_history'),

    # تاریخچه موجودی (جدید)
    path('api/stock/history/<int:product_id>/', views.get_product_stock_history, name='api_stock_history'),

    # آمار
    path('api/dashboard/stats/', views.get_dashboard_stats, name='api_dashboard_stats'),

    # وضعیت و موجودی (بروزرسانی شده)
    path('api/product/<int:product_id>/toggle/', views.toggle_product_status, name='api_toggle_product'),
    path('api/product/<int:product_id>/stock/', views.update_product_stock, name='api_update_stock'),

    # دسته بندی
    path('api/categories/', views.get_categories_with_stats, name='api_categories'),
    
]