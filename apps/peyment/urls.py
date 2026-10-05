from django.urls import path
from .views import *

app_name = 'peyment'

urlpatterns = [

    path('request/<int:order_id>/', send_request, name='request'),
    path('review/<int:order_id>/', payment_review, name='review'),  # ⭐ جدید
    path('verify/', Zarin_pal_view_verfiy.as_view(), name='verify'),
    path('show_sucess/<str:message>/', show_verfiy_message, name='show_sucess'),
    path('show_verfiy_unmessage/<str:message>/', show_verfiy_unmessage, name='show_verfiy_unmessage'),
]