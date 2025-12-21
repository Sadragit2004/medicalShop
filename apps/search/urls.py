from django.urls import path
from . import views

app_name = 'search'

urlpatterns = [



    path('api/search/suggestions/', views.search_suggestions, name='search_suggestions'),
    path('api/search/popular/', views.popular_searches, name='popular_searches'),
    path('search/', views.search_results, name='search_results'),

]