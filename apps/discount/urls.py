from django.urls import path,include
from .views import *

app_name = 'discount'
urlpatterns = [
    path('amazing/', get_amazing_product, name='amazing_products'),

]
