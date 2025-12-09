
from django.contrib import admin
from django.urls import path,include
import web.settings as sett
from django.conf.urls.static import static


urlpatterns = [

    path('admin/', admin.site.urls),
    path('',include('apps.main.urls'),name='main'),
    path('ckeditor',include('ckeditor_uploader.urls')),
    path('account/',include('apps.user.urls',namespace='user')),
    path('product/',include('apps.product.urls',namespace='product')),


]+static(sett.MEDIA_URL,document_root = sett.MEDIA_ROOT)
