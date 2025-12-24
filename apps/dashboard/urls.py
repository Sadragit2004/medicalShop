from django.urls import path
from . import views

app_name = 'dashboard'
urlpatterns = [
    path('', views.loadDashboard, name='home'),
    path('orders/', views.orders_page, name='orders'),
]
