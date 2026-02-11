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

    # دریافت اسلایدرهای هدر فعال و غیر منقضی
    from .models import SliderSite
    from django.utils import timezone

    # فقط اسلایدرهایی که هم active هستن و هم تاریخ پایانشون از الان بزرگتره
    head_sliders = SliderSite.objects.filter(
        isActive=True,
        endData__gte=timezone.now()  # تاریخ پایان >= الان
    ).order_by('-registerData')

    print(f"DEBUG: Active and non-expired sliders: {head_sliders.count()}")

    context = {
        'media_url': sett.MEDIA_URL,
        'latest_blogs': latest_blogs,
        'head_sliders': head_sliders,
    }

    return render(request, 'main_app/main.html', context)


def mainSlider(request):
    # دریافت اسلایدرهای اصلی فعال که تاریخ آنها معتبر است
    from .models import SliderMain
    from django.utils import timezone

    sliders = SliderMain.objects.filter(
        isActive=True,
        registerData__lte=timezone.now(),
        endData__gte=timezone.now()
    ).order_by('-registerData')

    context = {
        'sliders': sliders,
        'media_url': sett.MEDIA_URL,
    }

    return render(request,'main_app/mainslider.html', context)


# --- Static pages ---
def about(request):
    return render(request, "main_app/about.html")


def contact(request):
    return render(request, "main_app/contact.html")


def faq(request):
    return render(request, "main_app/faq.html")



def law(request):

    return render(request,'main_app/law.html')