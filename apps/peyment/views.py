from django.shortcuts import render, redirect, HttpResponse
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
import json
import requests

from apps.order.models import Order
from apps.peyment.models import Peyment
from apps.user.models.user import CustomUser
import utils
from .zarinpal import ZarinPal

ZP_API_REQUEST = "https://api.zarinpal.com/pg/v4/payment/request.json"
ZP_API_VERIFY = "https://api.zarinpal.com/pg/v4/payment/verify.json"
ZP_API_STARTPAY = "https://www.zarinpal.com/pg/StartPay/{authority}"

# Current merchant / callback
pay = ZarinPal(
    merchant="6fe93958-6832-4fbc-be2f-aa85e63233bd",
    call_back_url="https://sayamedical.com/peyment/verify/",
)
merchant = "6fe93958-6832-4fbc-be2f-aa85e63233bd"


def send_request(request, order_id):
    """Create payment and redirect user to ZarinPal gateway."""

    if not utils.has_internet_connection():
        messages.error(request, "اتصال اینرنت شما قابل تایید نیست", "danger")
        return redirect("main:index")

    user = request.user
    order = Order.objects.get(id=order_id)

    peyment = Peyment.objects.create(
        order=order,
        customer=user,
        amount=order.get_order_total_price(),
        description="پرداخت شما با زرین پال انجام شد",
    )

    request.session["peyment_session"] = {
        "order_id": order.id,
        "peyment_id": peyment.id,
    }

    response = pay.send_request(
        amount=order.get_order_total_price(),
        description="توضیحات مربوط به پرداخت",
        email="Example@test.com",
        mobile=getattr(user, "mobileNumber", None),
    )

    # Successful request returns a redirect to ZarinPal
    if hasattr(response, "status_code") and response.status_code in (301, 302):
        return response

    # Error response comes as dict
    if isinstance(response, dict):
        return HttpResponse(
            f"Error code: {response.get('error_code')}, Error Message: {response.get('message')}"
        )

    # Fallback
    return HttpResponse("خطا در اتصال به درگاه پرداخت")


def verify(request):
    response = pay.verify(request=request, amount="1000")

    if response.get("transaction"):
        if response.get("pay"):
            return HttpResponse("تراکنش با موفقت انجام شد")
        else:
            return HttpResponse("این تراکنش با موفقیت انجام شده است و الان دوباره verify شده است")
    else:
        if response.get("status") == "ok":
            return HttpResponse(
                f"Error code: {response.get('error_code')}, Error Message: {response.get('message')}"
            )
        elif response.get("status") == "cancel":
            return HttpResponse(
                "تراکنش ناموفق بوده است یا توسط کاربر لغو شده است"
                f"Error Message: {response.get('message')}"
            )


class Zarin_pal_view_verfiy(LoginRequiredMixin, View):
    def get(self, request):
        t_status = request.GET.get("Status")
        t_authority = request.GET.get("Authority")
        order_id = request.session["peyment_session"]["order_id"]
        peyment_id = request.session["peyment_session"]["peyment_id"]
        order = Order.objects.get(id=order_id)
        peyment = Peyment.objects.get(id=peyment_id)

        if t_status == "OK":
            req_header = {
                "accept": "application/json",
                "content-type": "application/json",
            }
            req_data = {
                "merchant_id": merchant,
                "amount": order.get_order_total_price(),
                "authority": t_authority,
            }
            req = requests.post(url=ZP_API_VERIFY, data=json.dumps(req_data), headers=req_header)
            if len(req.json()["errors"]) == 0:
                t_status = req.json()["data"]["code"]
                if t_status == 100:
                    order.isFinally = True
                    order.status = "delivered"
                    order.save()

                    peyment.isFinaly = True
                    peyment.statusCode = t_status
                    peyment.refId = str(req.json()["data"]["refId"])
                    peyment.save()

                    return redirect(
                        "peyment:show_sucess",
                        f"کد رهگیری شما : {str(req.json()['data']['refId'])}",
                    )

                elif t_status == 101:
                    order.isFinally = True
                    order.save()

                    peyment.isFinaly = True
                    peyment.statusCode = t_status
                    peyment.refId = str(req.json()["data"]["refId"])
                    peyment.save()
                    return redirect(
                        "peyment:show_sucess",
                        f"کد رهگیری شما : {str(req.json()['data']['refId'])}",
                    )
                else:
                    peyment.statusCode = t_status
                    peyment.save()
                    return redirect(
                        "peyment:show_verfiy_unmessage",
                        f"کد رهگیری شما : {str(req.json()['data']['refId'])}",
                    )
            else:
                e_code = req.json()["errors"]["code"]
                e_message = req.json()["errors"]["message"]
                return JsonResponse({"status": "ok", "message": e_message, "error_code": e_code})
        else:
            order.status = "canceled"
            order.save()
            return redirect("peyment:show_verfiy_unmessage", "پرداخت توسط کاربر لغو شد")

    def update_enrollment_status(self, order):
        """
        بروزرسانی وضعیت isPay در Enrollment مربوط به این سفارش
        """
        try:
            order_details = order.details.filter(enrollment__isnull=False)
            for order_detail in order_details:
                if order_detail.enrollment:
                    order_detail.enrollment.isPay = True
                    order_detail.enrollment.save()
                    print(f"Enrollment {order_detail.enrollment.id} updated to isPay=True")
        except Exception as e:
            print(f"Error updating enrollment status: {e}")


def show_verfiy_message(request, message):
    order = Order.objects.all()
    return render(request, "peyment_app/peyment.html", {"message": message, "orders": order})


def show_verfiy_unmessage(request, message):
    return render(request, "peyment_app/unpeyment.html", {"message": message})