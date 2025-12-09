from django.urls import path
from .views.auth import login,logout,verify


app_name = 'account'

urlpatterns = [
    path("login/", login.send_mobile, name="send_mobile"),
    path("verify/", verify.verify_code, name="verify_code"),
    path("logout/", logout.user_logout, name="logout"),
]
