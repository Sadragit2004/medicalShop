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

        # محاسبه مبلغ به ریال
        amount_in_rial = order.get_order_total_price()  # این تابع باید مبلغ را به ریال برگرداند

        # ایجاد رکورد پرداخت
        peyment = Peyment.objects.create(
            order=order,
            customer=request.user,
            amount=amount_in_rial,
            description="پرداخت سفارش",
            statusCode=0,
            isFinaly=False
        )

        # ذخیره اطلاعات در session با کلید منحصر به فرد
        session_key = f"peyment_{order_id}_{int(time.time())}"
        request.session[session_key] = {
            "order_id": order.id,
            "peyment_id": peyment.id,
            "amount": str(amount_in_rial),  # ذخیره به ریال
            "timestamp": str(time.time())
        }
        # ذخیره کلید session اصلی برای استفاده بعدی
        request.session["current_peyment_key"] = session_key
        request.session.set_expiry(3600)  # 1 ساعت

        # آماده‌سازی داده‌ها برای ارسال به زرین‌پال
        req_data = {
            "merchant_id": MERCHANT_ID,
            "amount": amount_in_rial,  # ارسال به ریال
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

            if 'data' in data and data['data'] and 'authority' in data['data']:
                authority = data['data']['authority']

                # ذخیره authority در session و مدل
                request.session[session_key]["authority"] = authority
                request.session.modified = True

                # ذخیره authority در یک session جداگانه برای بازیابی آسان
                request.session["last_authority"] = authority

                # ریدایرکت به درگاه پرداخت
                return redirect(ZP_API_STARTPAY.format(authority=authority))
            else:
                error_message = "خطا از سمت درگاه پرداخت"
                peyment.statusCode = -2
                peyment.isFinaly = False
                peyment.save()
                messages.error(request, f"خطا: {error_message}")
                return redirect("order:cart_page")
        else:
            messages.error(request, "خطا در ارتباط با درگاه پرداخت")
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

        # پیدا کردن session مربوط به این authority
        session_data = None
        session_key = None

        # روش 1: جستجو در session‌ها
        for key in list(request.session.keys()):
            if key.startswith("peyment_"):
                data = request.session.get(key)
                if data and data.get("authority") == t_authority:
                    session_data = data
                    session_key = key
                    break

        # روش 2: اگر session پیدا نشد، از دیتابیس پرداخت را پیدا کن
        if not session_data:
            try:
                # پیدا کردن پرداخت با این authority (اگر در session ذخیره شده بود)
                payments = Peyment.objects.filter(
                    customer=request.user,
                    isFinaly=False
                ).order_by('-createAt')

                # سعی کن آخرین پرداخت کاربر را پیدا کنی
                if payments.exists():
                    payment = payments.first()
                    order = payment.order
                    session_data = {
                        "order_id": order.id,
                        "peyment_id": payment.id,
                        "amount": str(payment.amount if payment.amount else order.get_order_total_price())
                    }
                    print(f"پرداخت از دیتابیس پیدا شد: {payment.id}")
            except Exception as e:
                print(f"Error finding payment from DB: {e}")

        # اگر باز هم session_data نداریم، خطا بده
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

        # حتماً قبل از هر کاری session را پاک کن
        if session_key and session_key in request.session:
            del request.session[session_key]
        if "current_peyment_key" in request.session:
            del request.session["current_peyment_key"]
        if "last_authority" in request.session:
            del request.session["last_authority"]
        request.session.modified = True

        # بررسی وضعیت پرداخت
        if t_status == "OK":
            result = self.verify_payment(request, payment, order, t_authority, session_data)
            return result
        else:
            # پرداخت ناموفق یا لغو شده
            result = self.handle_payment_cancellation(request, order, payment, "پرداخت لغو شد")
            return result

    def verify_payment(self, request, payment, order, authority, session_data):
        """تایید پرداخت با زرین‌پال"""
        amount = session_data.get("amount")
        if not amount:
            amount = order.get_order_total_price()

        req_data = {
            "merchant_id": MERCHANT_ID,
            "amount": int(float(amount)),  # اطمینان از int بودن
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

                if 'data' in data and data['data']:
                    code = data['data'].get('code')

                    if code == 100:
                        return self.handle_successful_payment(request, order, payment, data)
                    elif code == 101:
                        return self.handle_already_verified_payment(request, order, payment, data)
                    else:
                        error_message = data['data'].get('message', 'خطای نامشخص')
                        return self.handle_payment_error(request, order, payment, code, error_message)
                else:
                    error_message = "خطای نامشخص از زرین‌پال"
                    return self.handle_payment_error(request, order, payment, "UNKNOWN_ERROR", error_message)
            else:
                return self.handle_payment_error(request, order, payment,
                                               "CONNECTION_ERROR",
                                               "خطا در ارتباط با زرین‌پال")

        except Exception as e:
            return self.handle_payment_error(request, order, payment,
                                           "REQUEST_EXCEPTION",
                                           f"خطا در درخواست: {str(e)}")

    def handle_successful_payment(self, request, order, payment, data):
        """مدیریت پرداخت موفق"""
        try:
            order.isFinally = True
            order.status = "paid"
            order.save()

            payment.isFinaly = True
            payment.statusCode = 100

            if 'data' in data and data['data'] and 'ref_id' in data['data']:
                payment.refId = str(data['data']['ref_id'])
            payment.save()

            # پاک کردن session بعد از پرداخت موفق
            self.cleanup_session(request)

            return redirect("peyment:show_sucess",
                          message=f"پرداخت با موفقیت انجام شد. کد رهگیری: {payment.refId or ''}")

        except Exception as e:
            print(f"Error in handle_successful_payment: {e}")
            return redirect("peyment:show_verfiy_unmessage",
                          message="خطا در بروزرسانی اطلاعات پرداخت")

    def handle_already_verified_payment(self, request, order, payment, data):
        """مدیریت پرداخت قبلا تایید شده"""
        try:
            if not payment.isFinaly:
                payment.isFinaly = True
                payment.statusCode = 101
                if 'data' in data and data['data'] and 'ref_id' in data['data']:
                    payment.refId = str(data['data']['ref_id'])
                payment.save()

            if not order.isFinally:
                order.isFinally = True
                order.status = "paid"
                order.save()

            # پاک کردن session
            self.cleanup_session(request)

            return redirect("peyment:show_sucess",
                          message=f"این تراکنش قبلا تایید شده است. کد رهگیری: {payment.refId or ''}")
        except Exception as e:
            return redirect("peyment:show_verfiy_unmessage",
                          message="خطا در بروزرسانی اطلاعات")

    def handle_payment_cancellation(self, request, order, payment, message):
        """مدیریت لغو پرداخت توسط کاربر"""
        try:
            # فقط وضعیت پرداخت را تغییر بده، وضعیت سفارش را تغییر نده
            payment.statusCode = -10  # کد خاص برای لغو توسط کاربر
            payment.isFinaly = False
            payment.save()

            # وضعیت سفارش را تغییر نده، بگذار همان pending باشد
            # order.status = "pending"  # این خط حذف شد
            # order.save()  # این خط حذف شد

            # پاک کردن session
            self.cleanup_session(request)

            return redirect("peyment:show_verfiy_unmessage", message=message)

        except Exception as e:
            return redirect("peyment:show_verfiy_unmessage",
                          message="خطا در بروزرسانی وضعیت پرداخت")

    def handle_payment_error(self, request, order, payment, error_code, error_message):
        """مدیریت خطای پرداخت"""
        try:
            payment.statusCode = error_code
            payment.isFinaly = False
            payment.save()

            # فقط در صورت خطای واقعی وضعیت را تغییر بده
            if error_code not in [-10, "UNKNOWN_ERROR"]:
                order.status = "pending"  # برگشت به حالت انتظار
                order.save()

            # پاک کردن session
            self.cleanup_session(request)

            return redirect("peyment:show_verfiy_unmessage",
                          message=f"خطا در پرداخت: {error_message} (کد: {error_code})")

        except Exception as e:
            return redirect("peyment:show_verfiy_unmessage",
                          message=f"خطا در پرداخت: {error_message}")

    def cleanup_session(self, request):
        """پاک کردن session‌های مرتبط با پرداخت"""
        keys_to_remove = []
        for key in list(request.session.keys()):
            if key.startswith("peyment_") or key in ["current_peyment_key", "last_authority"]:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del request.session[key]

        request.session.modified = True


def show_verfiy_message(request, message):
    """نمایش صفحه موفقیت پرداخت"""
    try:
        # استخراج کد رهگیری از پیام
        ref_id = ""
        if message:
            if "کد رهگیری:" in message:
                ref_id = message.split("کد رهگیری:")[1].strip()
            elif "کد رهگیری" in message:
                # اگر کلمه "کد رهگیری" هست اما دونقطه نداره
                parts = message.split("کد رهگیری")
                if len(parts) > 1:
                    ref_id = parts[1].strip()
                    # حذف کاراکترهای غیر عددی از ابتدا
                    ref_id = ref_id.lstrip(": ").strip()

        # پیدا کردن آخرین سفارش پرداخت شده
        last_order = Order.objects.filter(
            customer=request.user,
            isFinally=True
        ).order_by('-registerDate').first()

        # اگر پیام کامل نیست، یک پیام استاندارد بساز
        if not message or "پرداخت" not in message:
            if ref_id:
                message = f"پرداخت با موفقیت انجام شد. کد رهگیری: {ref_id}"
            else:
                message = "پرداخت با موفقیت انجام شد."

        return render(request, "peyment_app/peyment.html", {
            "message": message,
            "order": last_order,
            "ref_id": ref_id
        })
    except Exception as e:
        print(f"Error in show_verfiy_message: {e}")
        return render(request, "peyment_app/peyment.html", {
            "message": "پرداخت با موفقیت انجام شد.",
            "ref_id": ""
        })


def show_verfiy_unmessage(request, message):
    """نمایش صفحه خطای پرداخت"""
    return render(request, "peyment_app/unpeyment.html", {"message": message})