from django.shortcuts import render, redirect
from django.contrib import messages
from ...forms.auth.login_form import MobileForm
from ...service.auth_service import AuthService

def send_mobile(request):
    next_url = request.GET.get("next")
    if request.method == "POST":
        form = MobileForm(request.POST)
        if form.is_valid():
            mobile = form.cleaned_data['mobileNumber']
            user = AuthService.get_or_create_user(mobile)
            security = AuthService.get_or_create_security(user)
            AuthService.send_activation_code(security)
            request.session["mobileNumber"] = mobile
            if next_url:
                request.session["next_url"] = next_url
            messages.success(request, "کد فعال‌سازی ارسال شد ✅")
            return redirect("account:verify_code")
    else:
        form = MobileForm()
    return render(request, "user_app/login.html", {"form": form, "next": next_url})

