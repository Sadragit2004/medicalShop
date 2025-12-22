from . import views


from django.urls import path

app_name = 'main'

urlpatterns = [


    path('',views.main,name='index'),
    path('main-slider/', views.mainSlider, name='main_slider'),



]