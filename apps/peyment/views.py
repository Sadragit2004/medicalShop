import json
import requests
import time
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction
from apps.order.models import Order
from apps.peyment.models import Peyment


# تنظیمات زرین‌پال
MERCHANT_ID = "6fe93958-6832-4fbc-be2f-aa85e63233bd"
ZP_API_REQUEST = "https://api.zarinpal.com/pg/v4/payment/request.json"
ZP_API_VERIFY = "https://api.zarinpal.com/pg/v4/payment/verify.json"
ZP_API_STARTPAY = "https://www.zarinpal.com/pg/StartPay/{authority}"
CALLBACK_URL = "https://sayamedical.com/peyment/verify/"


def send_request(request, order_id):
    """ایجاد درخواست پرداخت و هدایت به درگاه زرین‌پال"""
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
            return redirect("order:cart")

        # بررسی اینکه سفارش قبلا پرداخت نشده باشد
        if order.isFinally:
            messages.warning(request, "این سفارش قبلا پرداخت شده است")
            return redirect("order:orders")

        # محاسبه مبلغ پرداخت (با استفاده از تابع شما)
        amount_tomans = order.get_order_total_price()  # تومان
        amount_rials = int(amount_tomans)  # ریال

        # بررسی مبلغ
        if amount_rials < 1000:  # حداقل مبلغ زرین‌پال
            messages.error(request, "مبلغ پرداخت کافی نیست")
            return redirect("order:cart")

        # ایجاد رکورد پرداخت (با استفاده از فیلدهای مدل شما)
        peyment = Peyment.objects.create(
            order=order,
            customer=request.user,
            amount=amount_tomans,  # تومان
            description=f"پرداخت سفارش {order.orderCode}",
            status="pending"
        )

        # ذخیره اطلاعات در session برای تایید
        request.session['payment_data'] = {
            'order_id': order.id,
            'payment_id': peyment.id,
            'amount_rials': amount_rials,
            'authority_expected': True,
            'timestamp': time.time()
        }
        request.session.modified = True

        # آماده‌سازی داده‌ها برای زرین‌پال
        req_data = {
            "merchant_id": MERCHANT_ID,
            "amount": amount_rials,
            "callback_url": CALLBACK_URL,
            "description": f"پرداخت سفارش {order.orderCode} - سایا مدیکال",
            "metadata": {
                "email": request.user.email or "",
                "mobile": request.user.phone if hasattr(request.user, 'phone') else ""
            }
        }

        headers = {
            "accept": "application/json",
            "content-type": "application/json"
        }

        # ارسال درخواست به زرین‌پال
        try:
            response = requests.post(
                ZP_API_REQUEST,
                data=json.dumps(req_data),
                headers=headers,
                timeout=30
            )
        except requests.exceptions.Timeout:
            peyment.status = "failed"
            peyment.save()
            messages.error(request, "زمان ارتباط با درگاه پرداخت به پایان رسید")
            return redirect("order:cart")
        except requests.exceptions.RequestException as e:
            peyment.status = "failed"
            peyment.save()
            messages.error(request, f"خطا در ارتباط با درگاه پرداخت: {str(e)}")
            return redirect("order:cart")

        if response.status_code == 200:
            data = response.json()

            # بررسی خطاهای زرین‌پال
            if data.get('errors'):
                error_code = data['errors'].get('code', 'نامشخص')
                error_message = data['errors'].get('message', 'خطای نامشخص')

                peyment.status = "failed"
                peyment.error_code = error_code
                peyment.save()

                messages.error(request, f"خطا از سمت زرین‌پال: {error_message}")
                return redirect("order:cart")

            # دریافت authority
            authority = data['data']['authority']

            # ذخیره authority در رکورد پرداخت
            peyment.authority = authority
            peyment.save()

            # ذخیره authority در session
            request.session['payment_data']['authority'] = authority
            request.session.modified = True

            # هدایت به درگاه پرداخت
            return redirect(ZP_API_STARTPAY.format(authority=authority))
        else:
            peyment.status = "failed"
            peyment.save()
            messages.error(request, f"خطا از زرین‌پال - کد: {response.status_code}")
            return redirect("order:cart")

    except Exception as e:
        messages.error(request, f"خطای غیرمنتظره: {str(e)}")
        return redirect("order:cart")


@method_decorator(csrf_exempt, name='dispatch')
class ZarinPalVerifyView(LoginRequiredMixin, View):
    """کلاس بررسی و تایید پرداخت"""

    def get(self, request):
        status = request.GET.get('Status')
        authority = request.GET.get('Authority')

        # لاگ برای دیباگ
        print(f"🟡 Verify called - Status: {status}, Authority: {authority}")

        # بررسی وجود پارامترهای لازم
        if not status or not authority:
            messages.error(request, "پارامترهای لازم ارسال نشده است")
            return redirect("order:orders")

        # پرداخت لغو شده
        if status != "OK":
            return self.handle_cancelled_payment(request, authority)

        # پرداخت موفق (وضعیت OK)
        return self.verify_payment(request, authority)

    def handle_cancelled_payment(self, request, authority):
        """مدیریت پرداخت لغو شده"""
        try:
            # پیدا کردن پرداخت با authority
            payment = Peyment.objects.get(authority=authority, customer=request.user)

            # به‌روزرسانی وضعیت
            payment.status = "cancelled"
            payment.save()

            # پاک کردن session
            if 'payment_data' in request.session:
                del request.session['payment_data']

            messages.warning(request, "پرداخت توسط شما لغو شد")
            return redirect("order:cart")

        except Peyment.DoesNotExist:
            messages.error(request, "اطلاعات پرداخت یافت نشد")
            return redirect("order:orders")
        except Exception as e:
            messages.error(request, f"خطا در لغو پرداخت: {str(e)}")
            return redirect("order:orders")

    def verify_payment(self, request, authority):
        """تایید پرداخت با زرین‌پال"""
        print(f"🟢 Starting verification for authority: {authority}")

        try:
            # پیدا کردن پرداخت
            payment = Peyment.objects.get(authority=authority, customer=request.user)
            order = payment.order

            print(f"📦 Found payment: {payment.id}, order: {order.id}")

            # اگر قبلا تایید شده
            if payment.isFinaly:
                print(f"ℹ️ Payment already finalized")
                messages.info(request, "این پرداخت قبلاً تایید شده است")
                return self.show_success_page(request, order, payment, "این پرداخت قبلاً تأیید شده است")

            # دریافت مبلغ از session یا payment
            session_data = request.session.get('payment_data', {})
            amount_rials = session_data.get('amount_rials', payment.amount * 10)

            # درخواست تایید به زرین‌پال
            req_data = {
                "merchant_id": MERCHANT_ID,
                "amount": int(amount_rials),
                "authority": authority
            }

            print(f"📤 Sending verification request: {req_data}")

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
                print(f"📥 Response status: {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"❌ Request exception: {str(e)}")
                return self.handle_verification_error(
                    request,
                    payment,
                    order,
                    f"خطا در ارتباط با زرین‌پال: {str(e)}"
                )

            if response.status_code != 200:
                print(f"❌ HTTP error: {response.status_code}")
                return self.handle_verification_error(
                    request,
                    payment,
                    order,
                    f"خطا در ارتباط با زرین‌پال - کد وضعیت: {response.status_code}"
                )

            data = response.json()
            print(f"📊 Response data: {data}")

            # بررسی خطاهای زرین‌پال
            if data.get('errors'):
                error_code = data['errors'].get('code', 'نامشخص')
                error_message = data['errors'].get('message', 'خطای نامشخص')
                print(f"❌ ZarinPal error: {error_code} - {error_message}")
                return self.handle_verification_error(
                    request,
                    payment,
                    order,
                    f"{error_message} (کد خطا: {error_code})"
                )

            # پردازش کد وضعیت
            code = data['data'].get('code')
            print(f"🔢 Response code: {code}")

            if code == 100:  # پرداخت موفق
                print(f"✅ Payment successful")
                return self.handle_successful_payment(request, payment, order, data)
            elif code == 101:  # قبلا تایید شده
                print(f"ℹ️ Payment already verified")
                return self.handle_already_verified(request, payment, order, data)
            else:
                print(f"❌ Unknown code: {code}")
                return self.handle_verification_error(
                    request,
                    payment,
                    order,
                    f"کد خطا از زرین‌پال: {code}"
                )

        except Peyment.DoesNotExist:
            print(f"❌ Payment not found for authority: {authority}")
            messages.error(request, "پرداخت یافت نشد")
            return redirect("order:orders")
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            return self.handle_verification_error(request, None, None, f"خطای غیرمنتظره: {str(e)}")

    @transaction.atomic
    def handle_successful_payment(self, request, payment, order, data):
        """مدیریت پرداخت موفق"""
        try:
            print(f"🔄 Processing successful payment...")

            # ذخیره ref_id (اگر وجود دارد)
            ref_id = data['data'].get('ref_id')
            print(f"📝 Ref ID: {ref_id}")

            # به‌روزرسانی پرداخت
            payment.isFinaly = True
            payment.statusCode = 100
            payment.status = "completed"
            if ref_id:
                payment.refId = str(ref_id)
            else:
                print("⚠️ No ref_id received from ZarinPal")
            payment.save()

            print(f"✅ Payment updated: {payment.id}")

            # به‌روزرسانی سفارش
            order.isFinally = True
            order.status = "paid"
            order.save()

            print(f"✅ Order updated: {order.id}")

            # پاک کردن session
            if 'payment_data' in request.session:
                del request.session['payment_data']

            print(f"✅ Session cleaned")

            # نمایش صفحه موفقیت
            return self.show_success_page(
                request,
                order,
                payment,
                "پرداخت با موفقیت انجام شد",
                ref_id
            )

        except Exception as e:
            print(f"❌ Error in handle_successful_payment: {str(e)}")
            messages.error(request, f"خطا در به‌روزرسانی اطلاعات: {str(e)}")
            return redirect("order:orders")

    @transaction.atomic
    def handle_already_verified(self, request, payment, order, data):
        """مدیریت پرداخت قبلا تایید شده"""
        try:
            print(f"🔄 Processing already verified payment...")

            # اگر هنوز تایید نشده، تاییدش کن
            if not payment.isFinaly:
                payment.isFinaly = True
                payment.statusCode = 101
                payment.status = "completed"

                ref_id = data['data'].get('ref_id')
                if ref_id:
                    payment.refId = str(ref_id)
                payment.save()

            if not order.isFinally:
                order.isFinally = True
                order.status = "paid"
                order.save()

            # پاک کردن session
            if 'payment_data' in request.session:
                del request.session['payment_data']

            return self.show_success_page(
                request,
                order,
                payment,
                "این پرداخت قبلاً تأیید شده بود"
            )

        except Exception as e:
            print(f"❌ Error in handle_already_verified: {str(e)}")
            messages.error(request, f"خطا در به‌روزرسانی: {str(e)}")
            return redirect("order:orders")

    def handle_verification_error(self, request, payment, order, error_message):
        """مدیریت خطای تایید"""
        try:
            print(f"❌ Verification error: {error_message}")

            if payment:
                payment.status = "failed"
                payment.save()

            if order:
                order.status = "failed"
                order.save()

            # پاک کردن session
            if 'payment_data' in request.session:
                del request.session['payment_data']

            messages.error(request, error_message)
            return render(request, 'peyment_app/error.html', {
                'error': error_message,
                'order': order
            })

        except Exception as e:
            print(f"❌ Error in handle_verification_error: {str(e)}")
            messages.error(request, f"خطا در مدیریت خطا: {str(e)}")
            return redirect("order:orders")

    def show_success_page(self, request, order, payment, message, ref_id=None):
        """نمایش صفحه موفقیت پرداخت"""
        print(f"🎉 Showing success page - Ref ID: {ref_id}")

        context = {
            'success': True,
            'order': order,
            'payment': payment,
            'ref_id': ref_id,
            'message': message
        }
        return render(request, 'peyment_app/peyment.html', context)


def payment_success(request):
    """صفحه موفقیت پرداخت"""
    return render(request, 'peyment_app/peyment.html')


def payment_error(request):
    """صفحه خطای پرداخت"""
    return render(request, 'peyment_app/unpeyment.html')