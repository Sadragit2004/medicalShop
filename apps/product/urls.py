from django.urls import path
from . import views


app_name = 'product'

urlpatterns = [

    path('lasted-product/',views.latest_products,name='lastedProduct'),
    path('popularBrand/',views.popular_brands,name='brand'),
    path('popularCategories/',views.rich_categories,name='rich_categories'),
    path('<slug:slug>/', views.product_detail, name='product_detail'),

    # اضافه کردن کامنت
    path('<slug:product_slug>/comment/add/', views.add_comment, name='add_comment'),
    path('<slug:product_slug>/comments/load-more/', views.load_more_comments, name='load_more_comments'),
    # ============================ shop

    path('category/<slug:slug>/', views.show_by_filter, name='show_by_filter'),
    path('category/<slug:slug>/features/', views.get_feature_filter, name='get_feature_filter'),
    path('s/top-selling/',views.top_selling_products,name='top_selling')
]

