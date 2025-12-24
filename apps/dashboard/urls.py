from django.urls import path
from . import views

app_name = 'dashboard'
urlpatterns = [
    path('', views.loadDashboard, name='home'),
    path('orders/', views.orders_page, name='orders'),
    path('favorite/toggle/<int:product_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('favorite/check-batch/<int:product_id>/', views.check_favorite, name='check_favorite'),

]
