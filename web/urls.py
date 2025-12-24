
from django.contrib import admin
from django.urls import path,include
import web.settings as sett
from django.conf.urls.static import static


urlpatterns = [

    path('admin/', admin.site.urls),
    path('',include('apps.main.urls'),name='main'),
    path('ckeditor',include('ckeditor_uploader.urls')),
    path('accounts/',include('apps.user.urls',namespace='user')),
    path('product/',include('apps.product.urls',namespace='product')),
    path('discount/',include('apps.discount.urls',namespace='discount')),
    path('order/',include('apps.order.urls',namespace='order')),
    path('peyment/',include('apps.peyment.urls',namespace='peyment')),
    path('search/',include('apps.search.urls',namespace='search')),
    path('blog/',include('apps.blog.urls',namespace='blog')),
    path('dashboard/',include('apps.dashboard.urls',namespace='paneluser'))


]+static(sett.MEDIA_URL,document_root = sett.MEDIA_ROOT)
