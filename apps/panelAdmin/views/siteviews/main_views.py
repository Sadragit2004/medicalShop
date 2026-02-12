# views/site_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q
from datetime import datetime
from PIL import Image
import os
from apps.main.models import (
    SliderSite, SliderMain, Banner,
    ContactPhone, SettingShop
)
import utils


# ========================
# SLIDER SITE CRUD
# ========================

def slider_site_list(request):
    """لیست اسلایدرهای سایت"""
    sliders = SliderSite.objects.all()

    # فیلتر بر اساس وضعیت
    status = request.GET.get('status')
    if status == 'active':
        sliders = sliders.filter(isActive=True)
    elif status == 'inactive':
        sliders = sliders.filter(isActive=False)

    # فیلتر بر اساس تاریخ
    date_filter = request.GET.get('date_filter')
    now = timezone.now()
    if date_filter == 'expired':
        sliders = sliders.filter(endData__lt=now)
    elif date_filter == 'upcoming':
        sliders = sliders.filter(registerData__gt=now)
    elif date_filter == 'current':
        sliders = sliders.filter(registerData__lte=now, endData__gte=now)

    # فیلتر بر اساس جستجو
    search_query = request.GET.get('search', '')
    if search_query:
        sliders = sliders.filter(
            Q(textSlider__icontains=search_query) |
            Q(altSlide__icontains=search_query) |
            Q(link__icontains=search_query)
        )

    # بررسی تاریخ انقضا برای هر اسلایدر
    for slider in sliders:
        slider.is_expired = slider.endData < now if slider.endData else False
        slider.is_upcoming = slider.registerData > now if slider.registerData else False

    paginator = Paginator(sliders, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'panelAdmin/site/slider_site/list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'selected_status': status,
        'selected_date_filter': date_filter,
        'now': now
    })

def slider_site_create(request):
    if request.method == 'POST':
        try:
            register_date = datetime.strptime(
                request.POST.get('registerData'),
                '%Y-%m-%dT%H:%M'
            )
            end_date = datetime.strptime(
                request.POST.get('endData'),
                '%Y-%m-%dT%H:%M'
            )

            SliderSite.objects.create(
                textSlider=request.POST.get('textSlider'),
                imageName=request.FILES.get('imageName'),
                imageMobile=request.FILES.get('imageMobile'),
                altSlide=request.POST.get('altSlide'),
                isActive=request.POST.get('isActive') == 'on',
                registerData=register_date,
                endData=end_date,
                link=request.POST.get('link')
            )

            messages.success(request, 'اسلایدر با موفقیت ایجاد شد')
            return redirect('panelAdmin:admin_slider_site_list')

        except Exception as e:
            messages.error(request, f'خطا: {e}')

    return render(request, 'panelAdmin/site/slider_site/create.html')


def slider_site_update(request, slider_id):
    """ویرایش اسلایدر سایت"""
    slider = get_object_or_404(SliderSite, id=slider_id)

    if request.method == 'POST':
        try:
            # آپدیت اطلاعات متنی و وضعیت
            slider.textSlider = request.POST.get('textSlider', slider.textSlider)
            slider.altSlide = request.POST.get('altSlide', slider.altSlide)
            slider.isActive = request.POST.get('isActive') == 'on'
            slider.link = request.POST.get('link', slider.link)

            # --- بخش تغییر تصاویر (دسکتاپ و موبایل) ---
            if 'imageName' in request.FILES:
                slider.imageName = request.FILES['imageName']

            if 'imageMobile' in request.FILES:
                slider.imageMobile = request.FILES['imageMobile']
            # -------------------------------------------

            # آپدیت تاریخ‌ها
            start_date_str = request.POST.get('registerData')
            end_date_str = request.POST.get('endData')

            if start_date_str:
                register_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
                slider.registerData = register_date

            if end_date_str:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')
                slider.endData = end_date

            slider.save()

            messages.success(request, 'اسلایدر سایت با موفقیت ویرایش شد')
            return redirect('panelAdmin:admin_slider_site_list')

        except Exception as e:
            messages.error(request, f'خطا در ویرایش اسلایدر: {str(e)}')

    # فرمت تاریخ برای ورودی datetime-local
    register_date_formatted = slider.registerData.strftime('%Y-%m-%dT%H:%M') if slider.registerData else ''
    end_date_formatted = slider.endData.strftime('%Y-%m-%dT%H:%M') if slider.endData else ''

    return render(request, 'panelAdmin/site/slider_site/update.html', {
        'slider': slider,
        'register_date_formatted': register_date_formatted,
        'end_date_formatted': end_date_formatted
    })


def slider_site_delete(request, slider_id):
    """حذف اسلایدر سایت"""
    slider = get_object_or_404(SliderSite, id=slider_id)

    if request.method == 'POST':
        try:
            slider_title = slider.textSlider
            slider.delete()
            messages.success(request, f'اسلایدر "{slider_title}" با موفقیت حذف شد')
            return redirect('panelAdmin:admin_slider_site_list')
        except Exception as e:
            messages.error(request, f'خطا در حذف اسلایدر: {str(e)}')

    return render(request, 'panelAdmin/site/slider_site/delete_confirm.html', {'slider': slider})

def slider_site_toggle(request, slider_id):
    """تغییر وضعیت فعال/غیرفعال اسلایدر سایت"""
    slider = get_object_or_404(SliderSite, id=slider_id)

    if request.method == 'POST':
        try:
            slider.isActive = not slider.isActive
            slider.save()

            status = 'فعال' if slider.isActive else 'غیرفعال'
            messages.success(request, f'اسلایدر با موفقیت {status} شد')
        except Exception as e:
            messages.error(request, f'خطا در تغییر وضعیت اسلایدر: {str(e)}')

    return redirect('panelAdmin:admin_slider_site_list')


# ========================
# SLIDER MAIN CRUD
# ========================

def slider_main_list(request):
    """لیست اسلایدرهای اصلی"""
    sliders = SliderMain.objects.all()

    # فیلتر بر اساس وضعیت
    status = request.GET.get('status')
    if status == 'active':
        sliders = sliders.filter(isActive=True)
    elif status == 'inactive':
        sliders = sliders.filter(isActive=False)

    # فیلتر بر اساس تاریخ
    date_filter = request.GET.get('date_filter')
    now = timezone.now()
    if date_filter == 'expired':
        sliders = sliders.filter(endData__lt=now)
    elif date_filter == 'upcoming':
        sliders = sliders.filter(registerData__gt=now)
    elif date_filter == 'current':
        sliders = sliders.filter(registerData__lte=now, endData__gte=now)

    # فیلتر بر اساس جستجو
    search_query = request.GET.get('search', '')
    if search_query:
        sliders = sliders.filter(
            Q(textSlider__icontains=search_query) |
            Q(altSlide__icontains=search_query) |
            Q(link__icontains=search_query)
        )

    # بررسی تاریخ انقضا
    for slider in sliders:
        slider.is_expired = slider.endData < now if slider.endData else False
        slider.is_upcoming = slider.registerData > now if slider.registerData else False

    paginator = Paginator(sliders, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'panelAdmin/site/slider_main/list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'selected_status': status,
        'selected_date_filter': date_filter,
        'now': now
    })

def slider_main_create(request):
    """ایجاد اسلایدر اصلی جدید"""
    if request.method == 'POST':
        try:
            # تبدیل تاریخ‌ها به datetime
            start_date_str = request.POST.get('registerData')
            end_date_str = request.POST.get('endData')

            register_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')

            slider = SliderMain.objects.create(
                textSlider=request.POST.get('textSlider'),
                imageName=request.FILES['imageName'],  # تصویر اجباری است
                altSlide=request.POST.get('altSlide'),
                isActive=request.POST.get('isActive') == 'on',
                registerData=register_date,
                endData=end_date,
                link=request.POST.get('link')
            )

            messages.success(request, 'اسلایدر اصلی با موفقیت ایجاد شد')
            return redirect('panelAdmin:admin_slider_main_list')

        except Exception as e:
            messages.error(request, f'خطا در ایجاد اسلایدر: {str(e)}')

    return render(request, 'panelAdmin/site/slider_main/create.html')

def slider_main_update(request, slider_id):
    """ویرایش اسلایدر اصلی"""
    slider = get_object_or_404(SliderMain, id=slider_id)

    if request.method == 'POST':
        try:
            # آپدیت اطلاعات
            slider.textSlider = request.POST.get('textSlider', slider.textSlider)
            slider.altSlide = request.POST.get('altSlide', slider.altSlide)
            slider.isActive = request.POST.get('isActive') == 'on'
            slider.link = request.POST.get('link', slider.link)

            # آپدیت تصویر
            if 'imageName' in request.FILES:
                slider.imageName = request.FILES['imageName']

            # آپدیت تاریخ‌ها
            start_date_str = request.POST.get('registerData')
            end_date_str = request.POST.get('endData')

            if start_date_str:
                register_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
                slider.registerData = register_date

            if end_date_str:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')
                slider.endData = end_date

            slider.save()

            messages.success(request, 'اسلایدر اصلی با موفقیت ویرایش شد')
            return redirect('panelAdmin:admin_slider_main_list')

        except Exception as e:
            messages.error(request, f'خطا در ویرایش اسلایدر: {str(e)}')

    # فرمت تاریخ برای ورودی datetime-local
    register_date_formatted = slider.registerData.strftime('%Y-%m-%dT%H:%M') if slider.registerData else ''
    end_date_formatted = slider.endData.strftime('%Y-%m-%dT%H:%M') if slider.endData else ''

    return render(request, 'panelAdmin/site/slider_main/update.html', {
        'slider': slider,
        'register_date_formatted': register_date_formatted,
        'end_date_formatted': end_date_formatted
    })

def slider_main_delete(request, slider_id):
    """حذف اسلایدر اصلی"""
    slider = get_object_or_404(SliderMain, id=slider_id)

    if request.method == 'POST':
        try:
            slider_title = slider.textSlider
            slider.delete()
            messages.success(request, f'اسلایدر اصلی "{slider_title}" با موفقیت حذف شد')
            return redirect('panelAdmin:admin_slider_main_list')
        except Exception as e:
            messages.error(request, f'خطا در حذف اسلایدر: {str(e)}')

    return render(request, 'panelAdmin/site/slider_main/delete_confirm.html', {'slider': slider})

def slider_main_toggle(request, slider_id):
    """تغییر وضعیت فعال/غیرفعال اسلایدر اصلی"""
    slider = get_object_or_404(SliderMain, id=slider_id)

    if request.method == 'POST':
        try:
            slider.isActive = not slider.isActive
            slider.save()

            status = 'فعال' if slider.isActive else 'غیرفعال'
            messages.success(request, f'اسلایدر اصلی با موفقیت {status} شد')
        except Exception as e:
            messages.error(request, f'خطا در تغییر وضعیت اسلایدر: {str(e)}')

    return redirect('panelAdmin:admin_slider_main_list')


# ========================
# BANNER CRUD
# ========================

def banner_list(request):
    """لیست بنرها"""
    banners = Banner.objects.all()

    # فیلتر بر اساس وضعیت
    status = request.GET.get('status')
    if status == 'active':
        banners = banners.filter(isActive=True)
    elif status == 'inactive':
        banners = banners.filter(isActive=False)

    # فیلتر بر اساس تاریخ
    date_filter = request.GET.get('date_filter')
    now = timezone.now()
    if date_filter == 'expired':
        banners = banners.filter(endData__lt=now)
    elif date_filter == 'upcoming':
        banners = banners.filter(registerData__gt=now)
    elif date_filter == 'current':
        banners = banners.filter(registerData__lte=now, endData__gte=now)

    # فیلتر بر اساس جستجو
    search_query = request.GET.get('search', '')
    if search_query:
        banners = banners.filter(
            Q(nameBanner__icontains=search_query) |
            Q(textBanner__icontains=search_query) |
            Q(altSlide__icontains=search_query)
        )

    # بررسی تاریخ انقضا
    for banner in banners:
        banner.is_expired = banner.endData < now if banner.endData else False
        banner.is_upcoming = banner.registerData > now if banner.registerData else False

    paginator = Paginator(banners, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'panelAdmin/site/banner/list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'selected_status': status,
        'selected_date_filter': date_filter,
        'now': now
    })

def banner_create(request):
    """ایجاد بنر جدید"""
    if request.method == 'POST':
        try:
            # تبدیل تاریخ‌ها به datetime
            start_date_str = request.POST.get('registerData')
            end_date_str = request.POST.get('endData')

            register_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')

            banner = Banner.objects.create(
                nameBanner=request.POST.get('nameBanner'),
                textBanner=request.POST.get('textBanner'),
                altSlide=request.POST.get('altSlide'),
                imageName=request.FILES.get('imageName'),
                isActive=request.POST.get('isActive') == 'on',
                registerData=register_date,
                endData=end_date
            )

            messages.success(request, 'بنر با موفقیت ایجاد شد')
            return redirect('admin_banner_list')

        except Exception as e:
            messages.error(request, f'خطا در ایجاد بنر: {str(e)}')

    return render(request, 'panelAdmin/site/banner/create.html')

def banner_update(request, banner_id):
    """ویرایش بنر"""
    banner = get_object_or_404(Banner, id=banner_id)

    if request.method == 'POST':
        try:
            # آپدیت اطلاعات
            banner.nameBanner = request.POST.get('nameBanner', banner.nameBanner)
            banner.textBanner = request.POST.get('textBanner', banner.textBanner)
            banner.altSlide = request.POST.get('altSlide', banner.altSlide)
            banner.isActive = request.POST.get('isActive') == 'on'

            # آپدیت تصویر
            if 'imageName' in request.FILES:
                banner.imageName = request.FILES['imageName']

            # آپدیت تاریخ‌ها
            start_date_str = request.POST.get('registerData')
            end_date_str = request.POST.get('endData')

            if start_date_str:
                register_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
                banner.registerData = register_date

            if end_date_str:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')
                banner.endData = end_date

            banner.save()

            messages.success(request, 'بنر با موفقیت ویرایش شد')
            return redirect('admin_banner_list')

        except Exception as e:
            messages.error(request, f'خطا در ویرایش بنر: {str(e)}')

    # فرمت تاریخ برای ورودی datetime-local
    register_date_formatted = banner.registerData.strftime('%Y-%m-%dT%H:%M') if banner.registerData else ''
    end_date_formatted = banner.endData.strftime('%Y-%m-%dT%H:%M') if banner.endData else ''

    return render(request, 'panelAdmin/site/banner/update.html', {
        'banner': banner,
        'register_date_formatted': register_date_formatted,
        'end_date_formatted': end_date_formatted
    })

def banner_delete(request, banner_id):
    """حذف بنر"""
    banner = get_object_or_404(Banner, id=banner_id)

    if request.method == 'POST':
        try:
            banner_name = banner.nameBanner
            banner.delete()
            messages.success(request, f'بنر "{banner_name}" با موفقیت حذف شد')
            return redirect('admin_banner_list')
        except Exception as e:
            messages.error(request, f'خطا در حذف بنر: {str(e)}')

    return render(request, 'panelAdmin/site/banner/delete_confirm.html', {'banner': banner})

def banner_toggle(request, banner_id):
    """تغییر وضعیت فعال/غیرفعال بنر"""
    banner = get_object_or_404(Banner, id=banner_id)

    if request.method == 'POST':
        try:
            banner.isActive = not banner.isActive
            banner.save()

            status = 'فعال' if banner.isActive else 'غیرفعال'
            messages.success(request, f'بنر با موفقیت {status} شد')
        except Exception as e:
            messages.error(request, f'خطا در تغییر وضعیت بنر: {str(e)}')

    return redirect('admin_banner_list')


# ========================
# CONTACT PHONE CRUD
# ========================

def contact_phone_list(request):
    """لیست شماره‌های تماس"""
    phones = ContactPhone.objects.all()

    # فیلتر بر اساس نوع
    phone_type = request.GET.get('phone_type')
    if phone_type:
        phones = phones.filter(phone_type=phone_type)

    # فیلتر بر اساس وضعیت
    status = request.GET.get('status')
    if status == 'active':
        phones = phones.filter(is_active=True)
    elif status == 'inactive':
        phones = phones.filter(is_active=False)

    # فیلتر بر اساس جستجو
    search_query = request.GET.get('search', '')
    if search_query:
        phones = phones.filter(
            Q(title__icontains=search_query) |
            Q(phone_number__icontains=search_query)
        )

    return render(request, 'panelAdmin/site/contact_phone/list.html', {
        'phones': phones,
        'search_query': search_query,
        'selected_phone_type': phone_type,
        'selected_status': status,
        'phone_types': ContactPhone.PHONE_TYPE_CHOICES
    })

def contact_phone_create(request):
    """ایجاد شماره تماس جدید"""
    if request.method == 'POST':
        try:
            phone = ContactPhone.objects.create(
                title=request.POST.get('title'),
                phone_number=request.POST.get('phone_number'),
                phone_type=request.POST.get('phone_type'),
                is_active=request.POST.get('is_active') == 'on'
            )

            messages.success(request, f'شماره تماس "{phone.title}" با موفقیت ایجاد شد')
            return redirect('admin_contact_phone_list')

        except Exception as e:
            messages.error(request, f'خطا در ایجاد شماره تماس: {str(e)}')

    return render(request, 'panelAdmin/site/contact_phone/create.html', {
        'phone_types': ContactPhone.PHONE_TYPE_CHOICES
    })

def contact_phone_update(request, phone_id):
    """ویرایش شماره تماس"""
    phone = get_object_or_404(ContactPhone, id=phone_id)

    if request.method == 'POST':
        try:
            phone.title = request.POST.get('title', phone.title)
            phone.phone_number = request.POST.get('phone_number', phone.phone_number)
            phone.phone_type = request.POST.get('phone_type', phone.phone_type)
            phone.is_active = request.POST.get('is_active') == 'on'
            phone.save()

            messages.success(request, 'شماره تماس با موفقیت ویرایش شد')
            return redirect('admin_contact_phone_list')

        except Exception as e:
            messages.error(request, f'خطا در ویرایش شماره تماس: {str(e)}')

    return render(request, 'panelAdmin/site/contact_phone/update.html', {
        'phone': phone,
        'phone_types': ContactPhone.PHONE_TYPE_CHOICES
    })

def contact_phone_delete(request, phone_id):
    """حذف شماره تماس"""
    phone = get_object_or_404(ContactPhone, id=phone_id)

    if request.method == 'POST':
        try:
            phone_title = phone.title
            phone.delete()
            messages.success(request, f'شماره تماس "{phone_title}" با موفقیت حذف شد')
            return redirect('admin_contact_phone_list')
        except Exception as e:
            messages.error(request, f'خطا در حذف شماره تماس: {str(e)}')

    return render(request, 'panelAdmin/site/contact_phone/delete_confirm.html', {'phone': phone})

def contact_phone_toggle(request, phone_id):
    """تغییر وضعیت فعال/غیرفعال شماره تماس"""
    phone = get_object_or_404(ContactPhone, id=phone_id)

    if request.method == 'POST':
        try:
            phone.is_active = not phone.is_active
            phone.save()

            status = 'فعال' if phone.is_active else 'غیرفعال'
            messages.success(request, f'شماره تماس با موفقیت {status} شد')
        except Exception as e:
            messages.error(request, f'خطا در تغییر وضعیت شماره تماس: {str(e)}')

    return redirect('admin_contact_phone_list')


# ========================
# SHOP SETTINGS
# ========================

def shop_settings(request):
    """تنظیمات فروشگاه"""
    try:
        settings = SettingShop.objects.first()
        if not settings:
            settings = SettingShop.objects.create(
                name_shop="فروشگاه من",
                establishment_year=1400,
                is_call=True
            )
    except:
        settings = None

    phones = ContactPhone.objects.filter(is_active=True)

    if request.method == 'POST':
        try:
            if settings:
                # آپدیت تنظیمات موجود
                settings.name_shop = request.POST.get('name_shop', settings.name_shop)
                settings.establishment_year = request.POST.get('establishment_year', settings.establishment_year)
                settings.about_shop = request.POST.get('about_shop', settings.about_shop)
                settings.is_call = request.POST.get('is_call') == 'on'
                settings.emergency_phone_id = request.POST.get('emergency_phone') if request.POST.get('emergency_phone') else None

                if 'logo' in request.FILES:
                    settings.logo = request.FILES['logo']

                settings.save()
            else:
                # ایجاد تنظیمات جدید
                settings = SettingShop.objects.create(
                    name_shop=request.POST.get('name_shop'),
                    establishment_year=request.POST.get('establishment_year'),
                    about_shop=request.POST.get('about_shop'),
                    is_call=request.POST.get('is_call') == 'on',
                    emergency_phone_id=request.POST.get('emergency_phone') if request.POST.get('emergency_phone') else None,
                    logo=request.FILES.get('logo')
                )

            messages.success(request, 'تنظیمات فروشگاه با موفقیت ذخیره شد')
            return redirect('panelAdmin:admin_shop_settings')

        except Exception as e:
            messages.error(request, f'خطا در ذخیره تنظیمات: {str(e)}')

    return render(request, 'panelAdmin/site/shop_settings.html', {
        'settings': settings,
        'phones': phones
    })

def delete_shop_logo(request):
    """حذف لوگوی فروشگاه"""
    try:
        settings = SettingShop.objects.first()
        if settings and settings.logo:
            settings.logo.delete(save=False)
            settings.logo = None
            settings.save()
            messages.success(request, 'لوگوی فروشگاه با موفقیت حذف شد')
        else:
            messages.warning(request, 'لوگویی برای حذف وجود ندارد')
    except Exception as e:
        messages.error(request, f'خطا در حذف لوگو: {str(e)}')

    return redirect('panelAdmin:admin_shop_settings')


# ========================
# DASHBOARD
# ========================

def site_dashboard(request):
    """داشبورد مدیریت سایت"""
    now = timezone.now()

    # آمار اسلایدرهای سایت
    site_sliders = SliderSite.objects.all()
    active_site_sliders = site_sliders.filter(isActive=True).count()
    expired_site_sliders = site_sliders.filter(endData__lt=now).count()
    current_site_sliders = site_sliders.filter(
        registerData__lte=now, endData__gte=now, isActive=True
    ).count()

    # آمار اسلایدرهای اصلی
    main_sliders = SliderMain.objects.all()
    active_main_sliders = main_sliders.filter(isActive=True).count()
    expired_main_sliders = main_sliders.filter(endData__lt=now).count()
    current_main_sliders = main_sliders.filter(
        registerData__lte=now, endData__gte=now, isActive=True
    ).count()

    # آمار بنرها
    banners = Banner.objects.all()
    active_banners = banners.filter(isActive=True).count()
    expired_banners = banners.filter(endData__lt=now).count()
    current_banners = banners.filter(
        registerData__lte=now, endData__gte=now, isActive=True
    ).count()

    # آمار شماره‌های تماس
    phones = ContactPhone.objects.all()
    active_phones = phones.filter(is_active=True).count()
    phone_by_type = {}
    for phone_type, type_name in ContactPhone.PHONE_TYPE_CHOICES:
        count = phones.filter(phone_type=phone_type, is_active=True).count()
        if count > 0:
            phone_by_type[type_name] = count

    # تنظیمات فروشگاه
    shop_settings_obj = SettingShop.objects.first()

    # اسلایدرهای منقضی شده
    expired_items = {
        'site_sliders': site_sliders.filter(endData__lt=now, isActive=True)[:5],
        'main_sliders': main_sliders.filter(endData__lt=now, isActive=True)[:5],
        'banners': banners.filter(endData__lt=now, isActive=True)[:5],
    }

    # اسلایدرهای در حال اجرا
    current_items = {
        'site_sliders': site_sliders.filter(
            registerData__lte=now, endData__gte=now, isActive=True
        )[:5],
        'main_sliders': main_sliders.filter(
            registerData__lte=now, endData__gte=now, isActive=True
        )[:5],
        'banners': banners.filter(
            registerData__lte=now, endData__gte=now, isActive=True
        )[:5],
    }

    context = {
        # آمار کلی
        'total_site_sliders': site_sliders.count(),
        'total_main_sliders': main_sliders.count(),
        'total_banners': banners.count(),
        'total_phones': phones.count(),

        # آمار فعال
        'active_site_sliders': active_site_sliders,
        'active_main_sliders': active_main_sliders,
        'active_banners': active_banners,
        'active_phones': active_phones,

        # آمار جاری
        'current_site_sliders': current_site_sliders,
        'current_main_sliders': current_main_sliders,
        'current_banners': current_banners,

        # آمار منقضی شده
        'expired_site_sliders': expired_site_sliders,
        'expired_main_sliders': expired_main_sliders,
        'expired_banners': expired_banners,

        # جزئیات
        'phone_by_type': phone_by_type,
        'shop_settings': shop_settings_obj,
        'expired_items': expired_items,
        'current_items': current_items,
        'now': now,
    }

    return render(request, 'panelAdmin/site/dashboard.html', context)


# ========================
# UTILITY VIEWS
# ========================

def deactivate_expired_items(request):
    """غیرفعال کردن آیتم‌های منقضی شده"""
    now = timezone.now()

    try:
        # غیرفعال کردن اسلایدرهای سایت منقضی شده
        expired_site_sliders = SliderSite.objects.filter(
            endData__lt=now, isActive=True
        )
        site_sliders_count = expired_site_sliders.count()
        expired_site_sliders.update(isActive=False)

        # غیرفعال کردن اسلایدرهای اصلی منقضی شده
        expired_main_sliders = SliderMain.objects.filter(
            endData__lt=now, isActive=True
        )
        main_sliders_count = expired_main_sliders.count()
        expired_main_sliders.update(isActive=False)

        # غیرفعال کردن بنرهای منقضی شده
        expired_banners = Banner.objects.filter(
            endData__lt=now, isActive=True
        )
        banners_count = expired_banners.count()
        expired_banners.update(isActive=False)

        total = site_sliders_count + main_sliders_count + banners_count
        messages.success(request, f'{total} آیتم منقضی شده غیرفعال شدند')

    except Exception as e:
        messages.error(request, f'خطا در غیرفعال کردن آیتم‌ها: {str(e)}')

    return redirect('admin_site_dashboard')



def slider_main_delete(request, slider_id):
    """حذف اسلایدر اصلی"""
    slider = get_object_or_404(SliderMain, id=slider_id)

    # محاسبه آمار
    now = timezone.now()
    total_active_sliders = SliderMain.objects.filter(isActive=True).count()
    current_sliders = SliderMain.objects.filter(
        registerData__lte=now,
        endData__gte=now,
        isActive=True
    ).count()

    if request.method == 'POST':
        try:
            slider_title = slider.textSlider
            slider.delete()
            messages.success(request, f'اسلایدر اصلی "{slider_title}" با موفقیت حذف شد')
            return redirect('panelAdmin:admin_slider_main_list')
        except Exception as e:
            messages.error(request, f'خطا در حذف اسلایدر: {str(e)}')

    return render(request, 'panelAdmin/site/slider_main/delete_confirm.html', {
        'slider': slider,
        'total_active_sliders': total_active_sliders,
        'current_sliders': current_sliders
    })