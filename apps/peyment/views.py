from django.shortcuts import render, redirect, HttpResponse
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
import requests
import time

from apps.order.models import Order
from apps.peyment.models import Peyment
from apps.user.models.user import CustomUser
import utils

# تنظیمات ZarinPal
MERCHANT_ID = "6fe93958-6832-4fbc-be2f-aa85e63233bd"
ZP_API_REQUEST = "https://api.zarinpal.com/pg/v4/payment/request.json"
ZP_API_VERIFY = "https://api.zarinpal.com/pg/v4/payment/verify.json"
ZP_API_STARTPAY = "https://www.zarinpal.com/pg/StartPay/{authority}"
CALLBACK_URL = "https://sayamedical.com/peyment/verify/"


def send_request(request, order_id):
    """Create payment and redirect user to ZarinPal gateway."""

    if not utils.has_internet_connection():
        messages.error(request, "اتصال اینترنت شما قابل تایید نیست", "danger")
        return redirect("order:cart_page")

    try:
        # بررسی احراز هویت
        if not request.user.is_authenticated:
            messages.error(request, "لطفا ابتدا وارد حساب کاربری خود شوید")
            return redirect("user:login")

        # دریافت سفارش
        try:
            order = Order.objects.get(id=order_id, customer=request.user)
        except Order.DoesNotExist:
            messages.error(request, "سفارش یافت نشد")
            return redirect("order:cart_page")

        # بررسی اینکه آیا سفارش قبلا پرداخت شده
        if order.isFinally:
            messages.error(request, "این سفارش قبلا پرداخت شده است")
            return redirect("main:index")

        # ایجاد رکورد پرداخت
        peyment = Peyment.objects.create(
            order=order,
            customer=request.user,
            amount=order.get_order_total_price(),
            description="پرداخت سفارش",
            statusCode=0,
            isFinaly=False
        )

        # ذخیره اطلاعات در session
        request.session["peyment_session"] = {
            "order_id": order.id,
            "peyment_id": peyment.id,
            "amount": str(order.get_order_total_price() ),
            "timestamp": str(time.time())
        }
        request.session.set_expiry(1800)  # 30 دقیقه

        # آماده‌سازی داده‌ها برای ارسال به زرین‌پال
        req_data = {
            "merchant_id": MERCHANT_ID,
            "amount": int(order.get_order_total_price() ),  # تبدیل به ریال و int
            "callback_url": CALLBACK_URL,
            "description": f"پرداخت سفارش شماره {order.id} - سایت سایا مدیکال",
            "metadata": {
                "email": request.user.email if hasattr(request.user, 'email') and request.user.email else "",
                "mobile": getattr(request.user, "mobileNumber", "")
            }
        }

        headers = {
            "accept": "application/json",
            "content-type": "application/json"
        }

        # ارسال درخواست به زرین‌پال
        response = requests.post(
            ZP_API_REQUEST,
            data=json.dumps(req_data),
            headers=headers,
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()

            # دیباگ: چاپ پاسخ برای بررسی ساختار
            print("ZarinPal Request Response:", json.dumps(data, indent=2, ensure_ascii=False))

            # بررسی ساختار پاسخ
            if 'data' in data and data['data'] and 'authority' in data['data']:
                authority = data['data']['authority']

                # ذخیره authority در session
                request.session["peyment_session"]["authority"] = authority
                request.session.modified = True

                # ریدایرکت به درگاه پرداخت
                return redirect(ZP_API_STARTPAY.format(authority=authority))
            else:
                # خطا از سمت زرین‌پال
                error_message = "خطا از سمت درگاه پرداخت"
                if 'errors' in data and data['errors']:
                    # errors ممکن است لیست باشد
                    if isinstance(data['errors'], list) and len(data['errors']) > 0:
                        error_message = data['errors'][0].get('message', 'خطای نامشخص')
                    elif isinstance(data['errors'], dict):
                        error_message = data['errors'].get('message', 'خطای نامشخص')

                peyment.statusCode = -2
                peyment.isFinaly = False
                peyment.save()

                messages.error(request, f"خطا: {error_message}")
                return redirect("order:cart_page")
        else:
            messages.error(request, "خطا در ارتباط با درگاه پرداخت")
            return redirect("order:cart_page")

    except requests.exceptions.RequestException as e:
        messages.error(request, f"خطا در ارتباط با سرور پرداخت: {str(e)}")
        return redirect("order:cart_page")
    except Exception as e:
        messages.error(request, f"خطای غیرمنتظره: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return redirect("order:cart_page")


@method_decorator(csrf_exempt, name='dispatch')
class Zarin_pal_view_verfiy(LoginRequiredMixin, View):
    """کلاس بررسی و تایید پرداخت"""

    def get(self, request):
        t_status = request.GET.get("Status")
        t_authority = request.GET.get("Authority")

        # چک کردن وجود پارامترهای لازم
        if not t_status or not t_authority:
            messages.error(request, "پارامترهای لازم ارسال نشده است")
            return redirect("main:index")

        # استفاده از session برای پیدا کردن پرداخت
        session_data = request.session.get("peyment_session")

        if not session_data:
            messages.error(request, "اطلاعات پرداخت یافت نشد. لطفا با پشتیبانی تماس بگیرید.")
            return redirect("main:index")

        try:
            order_id = session_data.get("order_id")
            peyment_id = session_data.get("peyment_id")

            if not order_id or not peyment_id:
                messages.error(request, "اطلاعات پرداخت ناقص است")
                return redirect("main:index")

            order = Order.objects.get(id=order_id, customer=request.user)
            payment = Peyment.objects.get(id=peyment_id, customer=request.user)

        except (Order.DoesNotExist, Peyment.DoesNotExist) as e:
            messages.error(request, "اطلاعات پرداخت نامعتبر است")
            print(f"Error: {e}")
            return redirect("main:index")

        # بررسی وضعیت پرداخت
        if t_status == "OK":
            return self.verify_payment(request, payment, order, t_authority, session_data)
        else:
            # پرداخت ناموفق یا لغو شده
            return self.handle_payment_failure(request, order, payment, "لغو شده توسط کاربر")

    def verify_payment(self, request, payment, order, authority, session_data):
        """تایید پرداخت با زرین‌پال"""

        # دریافت amount از session
        amount = session_data.get("amount")
        if not amount:
            amount = order.get_order_total_price()

        req_data = {
            "merchant_id": MERCHANT_ID,
            "amount": int(float(amount)),
            "authority": authority
        }

        headers = {
            "accept": "application/json",
            "content-type": "application/json"
        }

        try:
            response = requests.post(
                ZP_API_VERIFY,
                data=json.dumps(req_data),
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()

                # دیباگ: چاپ پاسخ برای بررسی ساختار
                print("ZarinPal Verify Response:", json.dumps(data, indent=2, ensure_ascii=False))

                # بررسی ساختار پاسخ
                if 'data' in data and data['data']:
                    code = data['data'].get('code')

                    if code == 100:  # پرداخت موفق
                        return self.handle_successful_payment(request, order, payment, data)
                    elif code == 101:  # پرداخت قبلا موفق بوده
                        return self.handle_already_verified_payment(request, order, payment, data)
                    else:
                        # کدهای خطا
                        error_message = data['data'].get('message', 'خطای نامشخص')
                        return self.handle_payment_error(request, order, payment, code, error_message)
                else:
                    # خطای زرین‌پال
                    error_message = "خطای نامشخص از زرین‌پال"
                    if 'errors' in data and data['errors']:
                        if isinstance(data['errors'], list) and len(data['errors']) > 0:
                            error_item = data['errors'][0]
                            error_code = error_item.get('code', 'نامشخص')
                            error_message = error_item.get('message', 'خطای نامشخص')
                            return self.handle_payment_error(request, order, payment, error_code, error_message)
                        elif isinstance(data['errors'], dict):
                            error_code = data['errors'].get('code', 'نامشخص')
                            error_message = data['errors'].get('message', 'خطای نامشخص')
                            return self.handle_payment_error(request, order, payment, error_code, error_message)

                    return self.handle_payment_error(request, order, payment,
                                                   "UNKNOWN_ERROR", error_message)
            else:
                return self.handle_payment_error(request, order, payment,
                                               "CONNECTION_ERROR",
                                               "خطا در ارتباط با زرین‌پال")

        except requests.exceptions.RequestException as e:
            return self.handle_payment_error(request, order, payment,
                                           "REQUEST_EXCEPTION",
                                           f"خطا در درخواست: {str(e)}")
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return self.handle_payment_error(request, order, payment,
                                           "UNKNOWN_EXCEPTION",
                                           f"خطای غیرمنتظره: {str(e)}")

    def handle_successful_payment(self, request, order, payment, data):
        """مدیریت پرداخت موفق"""
        try:
            # بروزرسانی سفارش
            order.isFinally = True
            order.status = "paid"
            order.save()

            # بروزرسانی پرداخت
            payment.isFinaly = True
            payment.statusCode = 100

            # ذخیره refId از پاسخ زرین‌پال
            if 'data' in data and data['data'] and 'ref_id' in data['data']:
                payment.refId = str(data['data']['ref_id'])
            payment.save()

            # بروزرسانی وضعیت ثبت نام
            self.update_enrollment_status(order)

            # پاک کردن session
            if "peyment_session" in request.session:
                del request.session["peyment_session"]

            # ریدایرکت به صفحه موفقیت
            ref_id = payment.refId or ""
            return redirect("peyment:show_sucess",
                          message=f"پرداخت با موفقیت انجام شد. کد رهگیری: {ref_id}")

        except Exception as e:
            print(f"Error in handle_successful_payment: {e}")
            import traceback
            print(traceback.format_exc())
            return redirect("peyment:show_verfiy_unmessage",
                          message="خطا در بروزرسانی اطلاعات پرداخت")

    def handle_already_verified_payment(self, request, order, payment, data):
        """مدیریت پرداخت قبلا تایید شده"""
        if not payment.isFinaly:
            payment.isFinaly = True
            payment.statusCode = 101

            # ذخیره refId
            if 'data' in data and data['data'] and 'ref_id' in data['data']:
                payment.refId = str(data['data']['ref_id'])
            payment.save()

            if not order.isFinally:
                order.isFinally = True
                order.status = "paid"
                order.save()

        # پاک کردن session
        if "peyment_session" in request.session:
            del request.session["peyment_session"]

        ref_id = payment.refId or ""
        return redirect("peyment:show_sucess",
                      message=f"این تراکنش قبلا تایید شده است. کد رهگیری: {ref_id}")

    def handle_payment_failure(self, request, order, payment, message):
        """مدیریت پرداخت ناموفق"""
        try:
            order.status = "canceled"
            order.save()

            payment.statusCode = -1
            payment.isFinaly = False
            payment.save()

            # پاک کردن session
            if "peyment_session" in request.session:
                del request.session["peyment_session"]

            return redirect("peyment:show_verfiy_unmessage", message=message)

        except Exception as e:
            print(f"Error in handle_payment_failure: {e}")
            return redirect("peyment:show_verfiy_unmessage",
                          message="خطا در بروزرسانی وضعیت سفارش")

    def handle_payment_error(self, request, order, payment, error_code, error_message):
        """مدیریت خطای پرداخت"""
        try:
            payment.statusCode = error_code
            payment.isFinaly = False
            payment.save()

            order.status = "canceled"
            order.save()

            # پاک کردن session
            if "peyment_session" in request.session:
                del request.session["peyment_session"]

            return redirect("peyment:show_verfiy_unmessage",
                          message=f"خطا در پرداخت: {error_message} (کد: {error_code})")

        except Exception as e:
            print(f"Error in handle_payment_error: {e}")
            return redirect("peyment:show_verfiy_unmessage",
                          message=f"خطا در پرداخت: {error_message}")

    def update_enrollment_status(self, order):
        """بروزرسانی وضعیت isPay در Enrollment مربوط به این سفارش"""
        try:
            # این بخش بستگی به ساختار مدل‌های شما دارد
            # اگر Enrollment مربوطه را دارید، اینجا آن را آپدیت کنید
            pass
        except Exception as e:
            print(f"Error updating enrollment status: {e}")


def show_verfiy_message(request, message):
    """نمایش صفحه موفقیت پرداخت"""
    try:
        last_order = Order.objects.filter(
            customer=request.user,
            isFinally=True
        ).order_by('-registerDate').first()

        return render(request, "peyment_app/peyment.html", {
            "message": message,
            "order": last_order
        })
    except Exception as e:
        print(f"Error in show_verfiy_message: {e}")
        return render(request, "peyment_app/peyment.html", {"message": message})


def show_verfiy_unmessage(request, message):
    """نمایش صفحه خطای پرداخت"""
    return render(request, "peyment_app/unpeyment.html", {"message": message})