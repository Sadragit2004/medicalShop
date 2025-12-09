from django.urls import path
from .views import product_views
from .views import category_views
from .views import brand_views

app_name = 'product'

urlpatterns = [

    path('PopularCategories/',category_views.PopularCategoriesView.as_view(),name='popularGroup'),
    path('newsproduct/',product_views.NewArrivalsView.as_view(),name='newsproduct'),
    path('Popularbrand/',brand_views.PopularBrandsView.as_view(),name='PopularBrandsView'),
    path('<slug:slug>/', product_views.ProductDetailView.as_view(), name='detail'),

    # API نظرات محصول
    path('product/<int:product_id>/comment/add/', product_views.AddCommentView.as_view(), name='add_comment'),
    path('product/<int:product_id>/comments/', product_views.CommentListView.as_view(), name='comment_list'),


]
