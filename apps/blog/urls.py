from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    # لیست پست‌های بلاگ
    path('', views.blog_list, name='blog_list'),

    # جزئیات پست بلاگ
    path('<slug:slug>/', views.blog_detail, name='blog_detail'),

    # افزودن کامنت به پست بلاگ
    path('<slug:blog_slug>/comment/add/', views.add_blog_comment, name='add_blog_comment'),

    # بخش مقالات صفحه اصلی
    path('home-blogs/', views.main_blog_section, name='home_blogs_section'),
]
