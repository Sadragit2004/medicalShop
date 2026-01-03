# views/user_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from apps.user.models.user import CustomUser
from apps.user.models.security import UserSecurity
from apps.user.models.device import UserDevice
from datetime import datetime

# لیست کاربران
def user_list(request):
    users = CustomUser.objects.select_related('security').all()
    return render(request, 'panelAdmin/users/list.html', {'users': users})


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
        return redirect('admin_user_list')

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

