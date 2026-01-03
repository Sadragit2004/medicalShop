# views/auth_views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect

def admin_login(request):
    """صفحه لاگین ادمین"""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard')

    if request.method == 'POST':
        mobile_number = request.POST.get('mobileNumber')
        password = request.POST.get('password')

        user = authenticate(request, mobileNumber=mobile_number, password=password)

        if user is not None:
            if user.is_staff:
                login(request, user)
                messages.success(request, 'خوش آمدید!')
                return redirect('admin_dashboard')
            else:
                messages.error(request, 'شما دسترسی ادمین ندارید.')
        else:
            messages.error(request, 'شماره موبایل یا رمز عبور نادرست است.')

    return render(request, 'admin/auth/login.html')

def admin_logout(request):
    """خروج از پنل ادمین"""
    logout(request)
    messages.success(request, 'با موفقیت خارج شدید.')
    return redirect('admin_login')