from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.utils import timezone
from ...forms.auth.verify_form import VerificationCodeForm
from ...models.user import CustomUser
from ...service.auth_service import AuthService

def verify_code(request):
    mobile = request.session.get("mobileNumber")
    next_url = request.session.get("next_url")

    if not mobile:
        messages.error(request, "شماره موبایل یافت نشد.")
        return redirect("account:send_mobile")

    try:
        user = CustomUser.objects.get(mobileNumber=mobile)
        security = AuthService.get_or_create_security(user)
    except CustomUser.DoesNotExist:
        messages.error(request, "کاربر یافت نشد.")
        return redirect("account:send_mobile")

    # بررسی درخواست ارسال مجدد
    if request.method == "POST" and "resend" in request.POST:
        try:
            new_code = AuthService.send_activation_code(security,mobile)
            messages.success(request, "کد جدید ارسال شد.")
            # ریدایرکت برای جلوگیری از تکرار ارسال مجدد با رفرش
            return redirect("account:verify_code")
        except Exception as e:
            messages.error(request, f"خطا در ارسال مجدد کد: {str(e)}")

    # محاسبه زمان باقی‌مانده برای تایمر
    remaining_seconds = 0
    can_resend = True

    if security.expireCode:
        remaining_seconds = max(0, int((security.expireCode - timezone.now()).total_seconds()))
        can_resend = remaining_seconds <= 0

    # تبدیل ثانیه به فرمت دقیقه:ثانیه
    remaining_time = f"{remaining_seconds // 60:02d}:{remaining_seconds % 60:02d}"

    # پردازش کد تایید
    if request.method == "POST" and "resend" not in request.POST:
        form = VerificationCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['activeCode']
            try:
                AuthService.verify_code(security, code)
                AuthService.activate_user(user)
                login(request, user)
                messages.success(request, " ورود با موفقیت انجام شد.")
                return redirect(next_url or "main:index")
            except Exception as e:
                messages.error(request, str(e))
                return redirect("account:verify_code")
    else:
        form = VerificationCodeForm()

    context = {
        "form": form,
        "mobile": mobile,
        "remaining_time": remaining_time,
        "remaining_seconds": remaining_seconds,
        "can_resend": can_resend
    }

    return render(request, "user_app/code.html", context)