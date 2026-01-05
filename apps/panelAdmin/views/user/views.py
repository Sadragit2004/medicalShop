# views/user_views.py
# views/user_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Count, Case, When, Value, IntegerField
from django.db.models.functions import Concat
from django.utils import timezone
from datetime import datetime, timedelta
from apps.user.models.user import CustomUser
from apps.user.models.security import UserSecurity
from apps.user.models.device import UserDevice


def user_list(request):
    """لیست کاربران با فیلتر و جستجوی پیشرفته"""
    users = CustomUser.objects.select_related('security').all()

    # فیلتر بر اساس جستجو
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(
            Q(mobileNumber__icontains=search_query) |
            Q(name__icontains=search_query) |
            Q(family__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    # فیلتر بر اساس وضعیت فعال
    status = request.GET.get('status')
    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'inactive':
        users = users.filter(is_active=False)

    # فیلتر بر اساس نقش
    role = request.GET.get('role')
    if role == 'superuser':
        users = users.filter(is_superuser=True)
    elif role == 'staff':
        users = users.filter(is_staff=True, is_superuser=False)
    elif role == 'user':
        users = users.filter(is_staff=False, is_superuser=False)

    # فیلتر بر اساس وضعیت مسدودی
    ban_status = request.GET.get('ban_status')
    if ban_status == 'banned':
        users = users.filter(security__isBan=True)
    elif ban_status == 'not_banned':
        users = users.filter(security__isBan=False)

    # فیلتر بر اساس جنسیت
    gender = request.GET.get('gender')
    if gender in ['M', 'F']:
        users = users.filter(gender=gender)

    # فیلتر بر اساس تاریخ عضویت
    join_date = request.GET.get('join_date')
    if join_date:
        if join_date == 'today':
            today = timezone.now().date()
            users = users.filter(createAt__date=today)
        elif join_date == 'yesterday':
            yesterday = timezone.now().date() - timedelta(days=1)
            users = users.filter(createAt__date=yesterday)
        elif join_date == 'last_7_days':
            last_week = timezone.now() - timedelta(days=7)
            users = users.filter(createAt__gte=last_week)
        elif join_date == 'last_30_days':
            last_month = timezone.now() - timedelta(days=30)
            users = users.filter(createAt__gte=last_month)
        elif join_date == 'this_month':
            today = timezone.now().date()
            start_of_month = today.replace(day=1)
            users = users.filter(createAt__date__gte=start_of_month)

    # فیلتر بر اساس تعداد دستگاه‌ها
    devices_count = request.GET.get('devices_count')
    if devices_count:
        if devices_count == 'no_device':
            users = users.annotate(device_count=Count('devices')).filter(device_count=0)
        elif devices_count == 'one_device':
            users = users.annotate(device_count=Count('devices')).filter(device_count=1)
        elif devices_count == 'multiple_devices':
            users = users.annotate(device_count=Count('devices')).filter(device_count__gt=1)

    # مرتب‌سازی
    sort_by = request.GET.get('sort_by', '-createAt')
    if sort_by in ['createAt', '-createAt', 'mobileNumber', '-mobileNumber', 'name', '-name']:
        users = users.order_by(sort_by)
    else:
        users = users.order_by('-createAt')

    # محاسبه آمار
    total_users = users.count()
    active_users_count = users.filter(is_active=True).count()
    staff_count = users.filter(is_staff=True).count()
    banned_count = users.filter(security__isBan=True).count()

    # فیلتر بر اساس رنج سنی
    age_filter = request.GET.get('age')
    if age_filter:
        today = timezone.now().date()
        if age_filter == 'under_18':
            target_date = today.replace(year=today.year - 18)
            users = users.filter(birth_date__gte=target_date)
        elif age_filter == '18_30':
            target_date_min = today.replace(year=today.year - 30)
            target_date_max = today.replace(year=today.year - 18)
            users = users.filter(birth_date__range=(target_date_min, target_date_max))
        elif age_filter == '30_50':
            target_date_min = today.replace(year=today.year - 50)
            target_date_max = today.replace(year=today.year - 30)
            users = users.filter(birth_date__range=(target_date_min, target_date_max))
        elif age_filter == 'over_50':
            target_date = today.replace(year=today.year - 50)
            users = users.filter(birth_date__lte=target_date)

    # فیلتر بر اساس تکمیل اطلاعات
    profile_complete = request.GET.get('profile_complete')
    if profile_complete == 'complete':
        users = users.filter(
            Q(name__isnull=False) & Q(family__isnull=False) &
            Q(email__isnull=False) & Q(birth_date__isnull=False)
        )
    elif profile_complete == 'incomplete':
        users = users.filter(
            Q(name__isnull=True) | Q(family__isnull=True) |
            Q(email__isnull=True) | Q(birth_date__isnull=True)
        )

    # اعمال annotate برای نمایش بهتر
    users = users.annotate(
        full_name=Concat('name', Value(' '), 'family'),
        device_count=Count('devices'),
        profile_complete_percent=Case(
            When(
                Q(name__isnull=False) & Q(family__isnull=False) &
                Q(email__isnull=False) & Q(birth_date__isnull=False),
                then=Value(100)
            ),
            When(
                Q(name__isnull=False) & Q(family__isnull=False) &
                Q(email__isnull=False),
                then=Value(75)
            ),
            When(
                Q(name__isnull=False) & Q(family__isnull=False),
                then=Value(50)
            ),
            When(
                Q(name__isnull=False),
                then=Value(25)
            ),
            default=Value(0),
            output_field=IntegerField()
        )
    )

    context = {
        'users': users,
        'total_users': total_users,
        'active_users_count': active_users_count,
        'staff_count': staff_count,
        'banned_count': banned_count,
        'search_query': search_query,
        'selected_status': status,
        'selected_role': role,
        'selected_ban_status': ban_status,
        'selected_gender': gender,
        'selected_join_date': join_date,
        'selected_devices_count': devices_count,
        'selected_sort_by': sort_by,
        'selected_age_filter': age_filter,
        'selected_profile_complete': profile_complete,
    }

    return render(request, 'panelAdmin/users/list.html', context)



def toggle_ban(request, user_id):
    """تغییر وضعیت مسدودی کاربر"""
    user = get_object_or_404(CustomUser, id=user_id)
    security, created = UserSecurity.objects.get_or_create(user=user)

    security.isBan = not security.isBan
    security.save()

    status = 'مسدود' if security.isBan else 'رفع مسدودی'
    messages.success(request, f'کاربر با موفقیت {status} شد')

    return redirect('panelAdmin:admin_user_list')


def user_detail(request, user_id):
    user = get_object_or_404(
        CustomUser.objects.select_related('security').prefetch_related('devices'),
        id=user_id
    )

    return render(request, 'panelAdmin/users/detail.html', {'user': user})

# ایجاد کاربر جدید
def create_user(request):
    if request.method == 'POST':
        mobileNumber = request.POST.get('mobileNumber')

        try:
            # ایجاد کاربر
            user = CustomUser.objects.create_user(
                mobileNumber=mobileNumber,
                password=request.POST.get('password', '123456'),  # رمز پیش‌فرض
                name=request.POST.get('name'),
                family=request.POST.get('family'),
                email=request.POST.get('email'),
                gender=request.POST.get('gender', 'M'),
                birth_date=request.POST.get('birth_date') if request.POST.get('birth_date') else None,
                is_active=request.POST.get('is_active') == 'on',
                is_staff=request.POST.get('is_staff') == 'on',
                is_superuser=request.POST.get('is_superuser') == 'on'
            )

            messages.success(request, f'کاربر با شماره {mobileNumber} با موفقیت ایجاد شد')
            return redirect('admin_user_detail', user_id=user.id)

        except Exception as e:
            messages.error(request, f'خطا در ایجاد کاربر: {str(e)}')

    return render(request, 'panelAdmin/users/create.html')

# ویرایش کاربر
def update_user(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == 'POST':
        # آپدیت فیلدهای اصلی
        user.name = request.POST.get('name', user.name)
        user.family = request.POST.get('family', user.family)
        user.email = request.POST.get('email', user.email)
        user.gender = request.POST.get('gender', user.gender)

        # تاریخ تولد
        birth_date_str = request.POST.get('birth_date')
        if birth_date_str:
            try:
                user.birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
            except:
                pass

        # وضعیت کاربر
        user.is_active = request.POST.get('is_active') == 'on'
        user.is_staff = request.POST.get('is_staff') == 'on'
        user.is_superuser = request.POST.get('is_superuser') == 'on'

        # رمز عبور جدید
        new_password = request.POST.get('password')
        if new_password:
            user.set_password(new_password)

        user.save()

        # آپدیت UserSecurity
        security, created = UserSecurity.objects.get_or_create(user=user)
        security.isBan = request.POST.get('isBan') == 'on'
        security.isInfoFiled = request.POST.get('isInfoFiled') == 'on'
        security.save()

        messages.success(request, 'اطلاعات کاربر با موفقیت به‌روزرسانی شد')
        return redirect('admin_user_detail', user_id=user.id)

    # دریافت اطلاعات امنیتی
    security = get_object_or_404(UserSecurity, user=user)

    context = {
        'user': user,
        'security': security,
    }
    return render(request, 'panelAdmin/users/update.html', context)

# حذف کاربر
def delete_user(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == 'POST':
        mobile_number = user.mobileNumber
        user.delete()
        messages.success(request, f'کاربر با شماره {mobile_number} حذف شد')
        return redirect('panelAdmin:admin_user_list')

    return render(request, 'panelAdmin/users/delete_confirm.html', {'user': user})

# مدیریت دستگاه‌های کاربر
def user_devices(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    devices = user.devices.all()

    if request.method == 'POST':
        # افزودن دستگاه جدید
        device_info = request.POST.get('deviceInfo')
        ip_address = request.POST.get('ipAddress')

        if device_info:
            UserDevice.objects.create(
                user=user,
                deviceInfo=device_info,
                ipAddress=ip_address
            )
            messages.success(request, 'دستگاه جدید اضافه شد')
            return redirect('admin_user_devices', user_id=user.id)

    return render(request, 'panelAdmin/users/devices.html', {
        'user': user,
        'devices': devices
    })


# حذف دستگاه
def delete_device(request, device_id):
    device = get_object_or_404(UserDevice, id=device_id)
    user_id = device.user.id

    if request.method == 'POST':
        device.delete()
        messages.success(request, 'دستگاه حذف شد')

    return redirect('admin_user_devices', user_id=user_id)

