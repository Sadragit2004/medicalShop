from . import views
from . import uniqvisi

from django.urls import path

app_name = 'main'

urlpatterns = [


    path('',views.main,name='index'),
    path('main-slider/', views.mainSlider, name='main_slider'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('faq/', views.faq, name='faq'),
    path('terms/', views.law, name='law'),
     path('api/stats/overview/', uniqvisi.GetOverviewStatsAPI.as_view(), name='api_stats_overview'),
    path('api/stats/top-pages/', uniqvisi.GetTopPagesAPI.as_view(), name='api_stats_top_pages'),
    path('api/stats/recent-visits/', uniqvisi.GetRecentVisitsAPI.as_view(), name='api_stats_recent_visits'),
    path('api/stats/daily/', uniqvisi.GetDailyStatsAPI.as_view(), name='api_stats_daily'),
    path('api/stats/visitor/', uniqvisi.GetVisitorDetailsAPI.as_view(), name='api_stats_visitor'),
    path('api/stats/chart/', uniqvisi.GetChartDataAPI.as_view(), name='api_stats_chart'),
    path('api/stats/export/', uniqvisi.ExportStatsAPI.as_view(), name='api_stats_export'),
    path('api/stats/reset/', uniqvisi.ResetStatsAPI.as_view(), name='api_stats_reset'),



]