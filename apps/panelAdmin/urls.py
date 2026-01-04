from django.urls import path
from .views.user import views
from .views.product import product_view
from .views.discount import discount_views
from .views.order import order_views
from .views.siteviews import main_views
from .views.peyment import peyment_views
from .views import dashboard_view

app_name = 'panelAdmin'

urlpatterns = [

    path('', dashboard_view.admin_dashboard, name='admin_dashboard'),



    path('users/', views.user_list, name='admin_user_list'),
    path('users/create/', views.create_user, name='admin_create_user'),
    path('users/<uuid:user_id>/', views.user_detail, name='admin_user_detail'),
    path('users/<uuid:user_id>/update/', views.update_user, name='admin_update_user'),
    path('users/<uuid:user_id>/delete/', views.delete_user, name='admin_delete_user'),
    path('users/<uuid:user_id>/devices/', views.user_devices, name='admin_user_devices'),
    path('devices/<int:device_id>/delete/', views.delete_device, name='admin_delete_device'),
     path('categories/', product_view.category_list, name='admin_category_list'),
    path('categories/create/', product_view.category_create, name='admin_category_create'),
    path('categories/<int:category_id>/update/', product_view.category_update, name='admin_category_update'),
    path('categories/<int:category_id>/delete/', product_view.category_delete, name='admin_category_delete'),

    # Brand URLs
    path('brands/', product_view.brand_list, name='admin_brand_list'),
    path('brands/create/', product_view.brand_create, name='admin_brand_create'),
    path('brands/<int:brand_id>/update/', product_view.brand_update, name='admin_brand_update'),
    path('brands/<int:brand_id>/delete/', product_view.brand_delete, name='admin_brand_delete'),

    # Feature URLs
    path('features/', product_view.feature_list, name='admin_feature_list'),
    path('features/create/', product_view.feature_create, name='admin_feature_create'),
    path('features/<int:feature_id>/update/', product_view.feature_update, name='admin_feature_update'),
    path('features/<int:feature_id>/delete/', product_view.feature_delete, name='admin_feature_delete'),

    # Product URLs
    path('products/', product_view.product_list, name='admin_product_list'),
    path('products/create/', product_view.product_create, name='admin_product_create'),
    path('products/<int:product_id>/', product_view.product_detail, name='admin_product_detail'),
    path('products/<int:product_id>/update/', product_view.product_update, name='admin_product_update'),
    path('products/<int:product_id>/delete/', product_view.product_delete, name='admin_product_delete'),
    path('gallery/<int:image_id>/delete/', product_view.delete_gallery_image, name='admin_delete_gallery_image'),

    # Sale Type URLs
    path('products/<int:product_id>/sale-type/create/', product_view.sale_type_create, name='admin_sale_type_create'),
    path('sale-type/<int:sale_type_id>/update/', product_view.sale_type_update, name='admin_sale_type_update'),
    path('sale-type/<int:sale_type_id>/delete/', product_view.sale_type_delete, name='admin_sale_type_delete'),

    # Comment URLs
    path('comments/', product_view.comment_list, name='admin_comment_list'),
    path('comments/<int:comment_id>/toggle/', product_view.comment_toggle, name='admin_comment_toggle'),
    path('comments/<int:comment_id>/delete/', product_view.comment_delete, name='admin_comment_delete'),

    # AJAX URLs - جدید اضافه شده
    path('ajax/get-feature-values/', product_view.get_feature_values, name='admin_get_feature_values'),
    path('ajax/get-category-features/', product_view.get_category_features, name='admin_get_category_features'),
    path('ajax/get-feature-details/', product_view.get_feature_details, name='admin_get_feature_details'),
    path('ajax/upload-gallery-images/', product_view.ajax_upload_gallery_images, name='admin_ajax_upload_gallery_images'),
    path('ajax/get-product-features/', product_view.get_product_features, name='admin_get_product_features'),
    path('ajax/get-dynamic-features-html/', product_view.get_dynamic_features_html, name='admin_get_dynamic_features_html'),
    path('coupons/', discount_views.coupon_list, name='admin_coupon_list'),
    path('coupons/create/', discount_views.coupon_create, name='admin_coupon_create'),
    path('coupons/<int:coupon_id>/', discount_views.coupon_detail, name='admin_coupon_detail'),
    path('coupons/<int:coupon_id>/update/', discount_views.coupon_update, name='admin_coupon_update'),
    path('coupons/<int:coupon_id>/delete/', discount_views.coupon_delete, name='admin_coupon_delete'),
    path('coupons/<int:coupon_id>/toggle/', discount_views.coupon_toggle, name='admin_coupon_toggle'),

    # سبدهای تخفیف
    path('baskets/', discount_views.discount_basket_list, name='admin_discount_basket_list'),
    path('baskets/create/', discount_views.discount_basket_create, name='admin_discount_basket_create'),
    path('baskets/<int:basket_id>/', discount_views.discount_basket_detail, name='admin_discount_basket_detail'),
    path('baskets/<int:basket_id>/update/', discount_views.discount_basket_update, name='admin_discount_basket_update'),
    path('baskets/<int:basket_id>/delete/', discount_views.discount_basket_delete, name='admin_discount_basket_delete'),
    path('baskets/<int:basket_id>/toggle/', discount_views.discount_basket_toggle, name='admin_discount_basket_toggle'),
    path('baskets/remove-product/<int:detail_id>/', discount_views.remove_product_from_basket, name='admin_remove_product_from_basket'),

    # گزارشات
    path('reports/', discount_views.discount_report, name='admin_discount_report'),

    # AJAX Views
    path('ajax/search-products/', discount_views.search_products_ajax, name='admin_search_products_ajax'),
    path('ajax/get-product-details/', discount_views.get_product_details, name='admin_get_product_details'),
    path('ajax/get-all-categories/', discount_views.get_all_categories_ajax, name='admin_get_all_categories_ajax'),
    path('ajax/get-all-brands/', discount_views.get_all_brands_ajax, name='admin_get_all_brands_ajax'),
    path('ajax/get-products-bulk/', discount_views.get_products_bulk_ajax, name='admin_get_products_bulk_ajax'),

    path('states/', order_views.state_list, name='admin_state_list'),
    path('states/create/', order_views.state_create, name='admin_state_create'),
    path('states/<int:state_id>/update/', order_views.state_update, name='admin_state_update'),
    path('states/<int:state_id>/delete/', order_views.state_delete, name='admin_state_delete'),

    # City URLs
    path('cities/', order_views.city_list, name='admin_city_list'),
    path('states/<int:state_id>/cities/', order_views.city_list, name='admin_state_city_list'),
    path('cities/create/', order_views.city_create, name='admin_city_create'),
    path('states/<int:state_id>/cities/create/', order_views.city_create, name='admin_city_create_for_state'),
    path('cities/<int:city_id>/update/', order_views.city_update, name='admin_city_update'),
    path('cities/<int:city_id>/delete/', order_views.city_delete, name='admin_city_delete'),

    # User Address URLs
    path('user-addresses/', order_views.user_address_list, name='admin_user_address_list'),
    path('user-addresses/<int:address_id>/', order_views.user_address_detail, name='admin_user_address_detail'),
    path('user-addresses/<int:address_id>/delete/', order_views.user_address_delete, name='admin_user_address_delete'),

    # Order URLs
    path('orders/', order_views.order_list, name='admin_order_list'),
    path('order/<int:order_id>/invoice/', order_views.order_invoice, name='admin_order_invoice'),    path('orders/create/', order_views.order_create, name='admin_order_create'),
    path('orders/<int:order_id>/', order_views.order_detail, name='admin_order_detail'),
    path('orders/<int:order_id>/update/', order_views.order_update, name='admin_order_update'),
    path('orders/<int:order_id>/delete/', order_views.order_delete, name='admin_order_delete'),
    path('orders/<int:order_id>/update-status/', order_views.update_order_status, name='admin_update_order_status'),
    path('orders/<int:order_id>/toggle-final/', order_views.toggle_order_final, name='admin_toggle_order_final'),

    # Order Detail URLs
    path('orders/<int:order_id>/add-item/', order_views.add_order_item, name='admin_add_order_item'),
    path('order-items/<int:item_id>/update/', order_views.update_order_item, name='admin_update_order_item'),
    path('order-items/<int:item_id>/delete/', order_views.delete_order_item, name='admin_delete_order_item'),

    # AJAX URLs
    path('ajax/get-user-addresses/', order_views.get_user_addresses, name='admin_get_user_addresses'),
    path('ajax/get-product-price/', order_views.get_product_price, name='admin_get_product_price'),

    # Report URLs
    path('orders/report/', order_views.order_report, name='admin_order_report'),
    path('slider-site/', main_views.slider_site_list, name='admin_slider_site_list'),
    path('slider-site/create/', main_views.slider_site_create, name='admin_slider_site_create'),
    path('slider-site/<int:slider_id>/update/', main_views.slider_site_update, name='admin_slider_site_update'),
    path('slider-site/<int:slider_id>/delete/', main_views.slider_site_delete, name='admin_slider_site_delete'),
    path('slider-site/<int:slider_id>/toggle/', main_views.slider_site_toggle, name='admin_slider_site_toggle'),

    # Slider Main URLs
    path('slider-main/', main_views.slider_main_list, name='admin_slider_main_list'),
    path('slider-main/create/', main_views.slider_main_create, name='admin_slider_main_create'),
    path('slider-main/<int:slider_id>/update/', main_views.slider_main_update, name='admin_slider_main_update'),
    path('slider-main/<int:slider_id>/delete/', main_views.slider_main_delete, name='admin_slider_main_delete'),
    path('slider-main/<int:slider_id>/toggle/', main_views.slider_main_toggle, name='admin_slider_main_toggle'),

    # Banner URLs
    path('banners/', main_views.banner_list, name='admin_banner_list'),
    path('banners/create/', main_views.banner_create, name='admin_banner_create'),
    path('banners/<int:banner_id>/update/', main_views.banner_update, name='admin_banner_update'),
    path('banners/<int:banner_id>/delete/', main_views.banner_delete, name='admin_banner_delete'),
    path('banners/<int:banner_id>/toggle/', main_views.banner_toggle, name='admin_banner_toggle'),

    # Contact Phone URLs
    path('contact-phones/', main_views.contact_phone_list, name='admin_contact_phone_list'),
    path('contact-phones/create/', main_views.contact_phone_create, name='admin_contact_phone_create'),
    path('contact-phones/<int:phone_id>/update/', main_views.contact_phone_update, name='admin_contact_phone_update'),
    path('contact-phones/<int:phone_id>/delete/', main_views.contact_phone_delete, name='admin_contact_phone_delete'),
    path('contact-phones/<int:phone_id>/toggle/', main_views.contact_phone_toggle, name='admin_contact_phone_toggle'),

    # Shop Settings URLs
    path('shop-settings/', main_views.shop_settings, name='admin_shop_settings'),
    path('shop-settings/delete-logo/', main_views.delete_shop_logo, name='admin_delete_shop_logo'),

    # Dashboard & Utility URLs
    path('site-dashboard/', main_views.site_dashboard, name='admin_site_dashboard'),
    path('deactivate-expired/', main_views.deactivate_expired_items, name='admin_deactivate_expired'),
     path('payments/', peyment_views.payment_list, name='admin_payment_list'),
    path('payments/create/', peyment_views.payment_create, name='admin_payment_create'),
    path('payments/<int:payment_id>/', peyment_views.payment_detail, name='admin_payment_detail'),
    path('payments/<int:payment_id>/update/', peyment_views.payment_update, name='admin_payment_update'),
    path('payments/<int:payment_id>/delete/', peyment_views.payment_delete, name='admin_payment_delete'),

    # Payment Action URLs
    path('payments/<int:payment_id>/toggle/', peyment_views.toggle_payment_status, name='admin_toggle_payment_status'),
    path('payments/<int:payment_id>/verify/', peyment_views.verify_payment, name='admin_verify_payment'),
    path('payments/<int:payment_id>/cancel/', peyment_views.cancel_payment, name='admin_cancel_payment'),

    # Bulk Action URLs
    path('payments/bulk-verify/', peyment_views.bulk_verify_payments, name='admin_bulk_verify_payments'),
    path('payments/bulk-delete/', peyment_views.bulk_delete_payments, name='admin_bulk_delete_payments'),

    # Report URLs
    path('payments/report/', peyment_views.payment_report, name='admin_payment_report'),

    # AJAX URLs
    path('ajax/get-order-details/', peyment_views.get_order_details, name='admin_get_order_details'),
    path('ajax/search-payments/', peyment_views.search_payments_ajax, name='admin_search_payments_ajax'),
    # در urls.py اضافه کنید
    path('ajax/get-cities-by-state/', order_views.get_cities_by_state, name='admin_get_cities_by_state'),
    # Dashboard URLs
    path('payments/dashboard-widget/', peyment_views.payment_dashboard_widget, name='admin_payment_dashboard_widget'),

]