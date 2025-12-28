from django.urls import path
from . import views

app_name = 'dashboard'
urlpatterns = [
    path('', views.loadDashboard, name='home'),
    path('orders/', views.orders_page, name='orders'),
    path('favorite/toggle/<int:product_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('favorite/check-batch/<int:product_id>/', views.check_favorite, name='check_favorite'),
    path('list_favorit/', views.favorite_list, name='list_favorit'),
    path('remove_favorit/<int:favorite_id>/', views.remove_favorite, name='remove_favorit'),
    path('addresses/', views.address_list, name='address_list'),
    path('api/addresses/create/', views.create_user_address, name='create_user_address'),
    path('api/addresses/update/', views.update_user_address, name='update_user_address'),
    path('api/addresses/delete/', views.delete_user_address, name='delete_user_address'),
    path('api/addresses/get/', views.get_address_detail, name='get_address_detail'),
    path('api/cities/get/', views.get_cities, name='get_cities'),
     path('notifications/', views.notifications_page, name='notifications'),
    path('api/notifications/', views.get_notifications, name='get_notifications'),
    path('api/notifications/unread-count/', views.get_unread_count, name='get_unread_count'),
    path('api/notifications/mark-read/', views.mark_as_read, name='mark_as_read'),
    path('api/notifications/delete/', views.delete_notification, name='delete_notification'),
    path('complete-profile/', views.complete_profile, name='complete_profile'),

]
