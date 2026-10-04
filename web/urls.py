from django.contrib import admin
from django.urls import path, include
from django.contrib.sitemaps.views import sitemap, index
from django.views.generic import TemplateView
import web.settings as sett
from django.conf.urls.static import static
from apps.main.sitemaps import (
    StaticSitemap, CategorySitemap, ProductSitemap,
    BlogPostSitemap, BlogListSitemap,
)

sitemaps = {
    'static': StaticSitemap,
    'categories': CategorySitemap,
    'products': ProductSitemap,
    'blog': BlogPostSitemap,
    'blog-list': BlogListSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.main.urls'), name='main'),
    path('ckeditor', include('ckeditor_uploader.urls')),
    path('accounts/', include('apps.user.urls', namespace='user')),
    path('product/', include('apps.product.urls', namespace='product')),
    path('discount/', include('apps.discount.urls', namespace='discount')),
    path('order/', include('apps.order.urls', namespace='order')),
    path('peyment/', include('apps.peyment.urls', namespace='peyment')),
    path('search/', include('apps.search.urls', namespace='search')),
    path('blog/', include('apps.blog.urls', namespace='blog')),
    path('dashboard/', include('apps.dashboard.urls', namespace='paneluser')),
    path('panelAdmin/', include('apps.panelAdmin.urls', namespace='panelAdmin')),
    path('price/', include('apps.price.urls', namespace='price')),

    # Sitemap & Robots
    path('sitemap.xml', index, {'sitemaps': sitemaps}, name='sitemap-index'),
    path('sitemap-<section>.xml', sitemap, {'sitemaps': sitemaps},
         name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', TemplateView.as_view(
        template_name='robots.txt',
        content_type='text/plain'
    )),
] + static(sett.MEDIA_URL, document_root=sett.MEDIA_ROOT)