from . import views


from django.urls import path

app_name = 'main'

urlpatterns = [


    path('',views.main,name='index'),
    path('main-slider/', views.mainSlider, name='main_slider'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('faq/', views.faq, name='faq'),
    path('terms/', views.law, name='law'),



]