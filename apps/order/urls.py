from django.urls import path
from . import views
from . import core_view

app_name = 'order'

urlpatterns = [
    # URLهای سبد خرید
    path('cart/summary/', views.cart_summary, name='cart_summary'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/', views.update_cart_quantity, name='update_cart_quantity'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    path('cart/count/', views.get_cart_count, name='get_cart_count'),
    path('createOrder/',views.CreateOrderView.as_view(),name='createOrder'),
    path('cart/', views.cart_page, name='cart_page'),
    path('save-location/', core_view.save_user_location, name='save_location'),
    path('get-location/', core_view.get_user_location, name='get_location'),
    path('checkout/<int:order_id>/', views.checkout, name='checkout'),

    # API endpoints for addresses
    path('api/cities/<int:state_id>/', views.get_cities_by_state, name='get_cities_by_state'),
    path('api/addresses/create/', views.create_user_address, name='create_user_address'),
]