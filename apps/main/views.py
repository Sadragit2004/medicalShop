from django.shortcuts import render
import web.settings as sett
from apps.blog.views import get_latest_blogs
# Create your views here.




def media_admin(request):

    context = {
        'media_url':sett.MEDIA_URL
    }

    return context



def main(request):
    # دریافت پست‌های اخیر بلاگ برای صفحه اصلی
    latest_blogs = get_latest_blogs()[:6]

    context = {
        'media_url': sett.MEDIA_URL,
        'latest_blogs': latest_blogs,
    }

    return render(request,'main_app/main.html', context)

