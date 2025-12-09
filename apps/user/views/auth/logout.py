from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib import messages

def user_logout(request):
    logout(request)
    messages.success(request, "✅ شما با موفقیت خارج شدید.")
    return redirect("main:index")
