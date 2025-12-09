# views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from ...forms.auth.verify_form import VerificationCodeForm
from ...models.user import CustomUser
from ...service.auth_service import AuthService

def verify_code(request):
    mobile = request.session.get("mobileNumber")
    next_url = request.session.get("next_url")

    if not mobile:
        messages.error(request, "شماره موبایل یافت نشد.")
        return redirect("account:send_mobile")

    user = CustomUser.objects.get(mobileNumber=mobile)
    security = AuthService.get_or_create_security(user)

    if request.method == "POST":
        # بررسی اگر درخواست ارسال مجدد است
        if 'resend' in request.POST and request.POST['resend'] == 'true':
            try:
                result = AuthService.resend_activation_code(security)
                messages.success(request, result['message'])
                if 'remaining_seconds' in result:
                    request.session['remaining_seconds'] = result['remaining_seconds']
                return redirect("account:verify_code")
            except Exception as e:
                messages.error(request, str(e))
                return redirect("account:verify_code")

        # اگر درخواست تأیید کد است
        form = VerificationCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['activeCode']
            try:
                AuthService.verify_code(security, code)
                AuthService.activate_user(user)
                login(request, user)
                messages.success(request, "✅ ورود با موفقیت انجام شد.")

                # پاکسازی session
                if 'mobileNumber' in request.session:
                    del request.session['mobileNumber']
                if 'next_url' in request.session:
                    del request.session['next_url']
                if 'remaining_seconds' in request.session:
                    del request.session['remaining_seconds']

                return redirect(next_url or "main:index")
            except Exception as e:
                messages.error(request, str(e))
                return redirect("account:verify_code")
    else:
        form = VerificationCodeForm()

    # دریافت وضعیت از service
    status = AuthService.get_code_status(security)

    # ارسال داده‌ها به تمپلیت
    context = {
        "form": form,
        "mobile": mobile,
        "remaining_seconds": status['remaining_seconds'],
        "remaining_time": status['remaining_time_display'],
        "can_resend": status['can_resend']
    }

    return render(request, "user_app/code.html", context)