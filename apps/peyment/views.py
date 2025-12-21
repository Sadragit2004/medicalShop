from django.shortcuts import render,redirect
import requests
import json
import requests
from django.views import View
from django.contrib import messages
from apps.order.models import Order
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from apps.peyment.models import Peyment
from apps.user.models import CustomUser
import utils

from .zarinpal import ZarinPal
from django.http import JsonResponse

ZP_API_REQUEST = "https://api.zarinpal.com/pg/v4/payment/request.json"
ZP_API_VERIFY = "https://api.zarinpal.com/pg/v4/payment/verify.json"
ZP_API_STARTPAY = "https://www.zarinpal.com/pg/StartPay/{authority}"

pay = ZarinPal(merchant='41cb2cdd-3a44-4fb4-a0b3-db471b673078', call_back_url="https://rank0.ir/peyment/verify/")
merchant='41cb2cdd-3a44-4fb4-a0b3-db471b673078'

def send_request(request,order_id):
    # email and mobile is optimal

    if utils.has_internet_connection():

        user =  request.user
        order = Order.objects.get(id = order_id)

        peyment = Peyment.objects.create(
            order = order,
            customer = request.user,
            amount = order.get_order_total_price(),
            description = 'پرداخت شما با زرین پال انجام شد'
        )

        peyment.save()

        request.session['peyment_session'] = {
            'order_id':order.id,
            'peyment_id':peyment.id,

        }

        response = pay.send_request(amount=order.get_order_total_price(), description='توضیحات مربوط به پرداخت', email="Example@test.com",
                                mobile=user.mobileNumber)
        if response.get('error_code') is None:
            # redirect object
            return response
        else:
            return HttpResponse(f'Error code: {response.get("error_code")}, Error Message: {response.get("message")}')

    else:

        messages.error(request,'اتصال اینرنت شما قابل تایید نیست','danger')
        return redirect('main:index')


def verify(request):
    response = pay.verify(request=request, amount='1000')

    if response.get("transaction"):
        if response.get("pay"):
            return HttpResponse('تراکنش با موفقت انجام شد')
        else:
            return HttpResponse('این تراکنش با موفقیت انجام شده است و الان دوباره verify شده است')
    else:
        if response.get("status") == "ok":
            return HttpResponse(f'Error code: {response.get("error_code")}, Error Message: {response.get("message")}')
        elif response.get("status") == "cancel":
            return HttpResponse(f'تراکنش ناموفق بوده است یا توسط کاربر لغو شده است'
                                f'Error Message: {response.get("message")}')

class Zarin_pal_view_verfiy(LoginRequiredMixin, View):
    def get(self, request):
        t_status = request.GET.get('Status')
        t_authority = request.GET['Authority']
        order_id = request.session['peyment_session']['order_id']
        peyment_id = request.session['peyment_session']['peyment_id']
        order = Order.objects.get(id=order_id)
        peyment = Peyment.objects.get(id=peyment_id)


        if t_status == 'OK':
            req_header = {
                "accept": "application/json",
                "content-type": "application/json"
            }
            req_data = {
                "merchant_id": merchant,
                "amount": order.get_order_total_price(),
                "authority": t_authority
            }
            req = requests.post(url=ZP_API_VERIFY, data=json.dumps(req_data), headers=req_header)
            if len(req.json()['errors']) == 0:
                t_status = req.json()['data']['code']
                if t_status == 100:
                    # پرداخت موفق - بروزرسانی وضعیت سفارش
                    order.isFinally = True
                    order.status = "delivered"
                    order.save()

                    # بروزرسانی وضعیت enrollment مربوط به این سفارش - غیرفعال شده
                    # self.update_enrollment_status(order)

                    peyment.isFinaly = True
                    peyment.statusCode = t_status
                    peyment.refId = str(req.json()['data']['refId'])
                    peyment.save()

                    return redirect('peyment:show_sucess', 'کد رهگیری شما : {}'.format(str(req.json()['data']['refId'])))


                elif t_status == 101:
                    # پرداخت تکراری - بروزرسانی وضعیت
                    order.isFinally = True
                    order.save()

                    # بروزرسانی وضعیت enrollment مربوط به این سفارش - غیرفعال شده
                    # self.update_enrollment_status(order)

                    peyment.isFinaly = True
                    peyment.statusCode = t_status
                    peyment.refId = str(req.json()['data']['refId'])
                    peyment.save()
                    return redirect('peyment:show_sucess', 'کد رهگیری شما : {}'.format(str(req.json()['data']['refId'])))
                else:
                    peyment.statusCode = t_status
                    peyment.save()
                    return redirect('peyment:show_verfiy_unmessage', 'کد رهگیری شما : {}'.format(str(req.json()['data']['refId'])))
            else:
                e_code = req.json()['errors']['code']
                e_message = req.json()['errors']['message']
                return JsonResponse({
                    "status": 'ok',
                    "message": e_message,
                    "error_code": e_code
                })
        else:
            order.status = "canceled"
            order.save()
            return redirect('peyment:show_verfiy_unmessage','پرداخت توسط کاربر لغو شد')

    def update_enrollment_status(self, order):
        """
        بروزرسانی وضعیت isPay در Enrollment مربوط به این سفارش
        """
        try:
            # پیدا کردن OrderDetail مربوط به این سفارش که enrollment دارد
            order_details = order.details.filter(enrollment__isnull=False)

            for order_detail in order_details:
                if order_detail.enrollment:
                    # بروزرسانی وضعیت پرداخت در Enrollment
                    order_detail.enrollment.isPay = True
                    order_detail.enrollment.save()
                    print(f"Enrollment {order_detail.enrollment.id} updated to isPay=True")

        except Exception as e:
            print(f"Error updating enrollment status: {e}")

def show_verfiy_message(request,message):
    order = Order.objects.all()
    return render(request,'peyment_app/peyment.html',{'message':message,'orders':order})

def show_verfiy_unmessage(request,message):
    return render(request,'peyment_app/unpeyment.html',{'message':message})