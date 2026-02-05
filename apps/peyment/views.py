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
            return redirect("order:cart_page")

        # بررسی اینکه سفارش قبلا پرداخت نشده باشد
        if order.isFinally:
            messages.warning(request, "این سفارش قبلا پرداخت شده است")
            return redirect("order:orders")

        # محاسبه مبلغ پرداخت
        amount_tomans = order.get_order_total_price()  # تومان
        amount_rials = int(amount_tomans)  # ریال

        # بررسی مبلغ
        if amount_rials < 1000:
            messages.error(request, "مبلغ پرداخت کافی نیست")
            return redirect("order:cart_page")

        # ایجاد رکورد پرداخت
        peyment = Peyment.objects.create(
            order=order,
            customer=request.user,
            amount=amount_tomans,
            description=f"پرداخت سفارش {order.orderCode}",
            isFinaly=False,
            statusCode=None
        )

        # ذخیره اطلاعات در session
        request.session['payment_data'] = {
            'order_id': order.id,
            'payment_id': peyment.id,
            'amount_rials': amount_rials,
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
            peyment.delete()  # حذف رکورد ناموفق
            messages.error(request, "زمان ارتباط با درگاه پرداخت به پایان رسید")
            return redirect("order:cart_page")
        except requests.exceptions.RequestException as e:
            peyment.delete()  # حذف رکورد ناموفق
            messages.error(request, f"خطا در ارتباط با درگاه پرداخت: {str(e)}")
            return redirect("order:cart_page")

        if response.status_code == 200:
            data = response.json()

            # بررسی خطاهای زرین‌پال
            if data.get('errors'):
                error_code = data['errors'].get('code', 'نامشخص')
                error_message = data['errors'].get('message', 'خطای نامشخص')

                peyment.delete()  # حذف رکورد ناموفق
                messages.error(request, f"خطا از سمت زرین‌پال: {error_message}")
                return redirect("order:cart_page")

            # دریافت authority
            authority = data['data']['authority']

            # بروزرسانی رکورد پرداخت با authority
            # **توجه: در مدل شما فیلد authority وجود ندارد!**
            # می‌توانید به صورت موقت در description ذخیره کنید یا فیلد اضافه کنید
            peyment.description = f"{peyment.description} - Authority: {authority}"
            peyment.save()

            # ذخیره authority در session
            request.session['payment_data']['authority'] = authority
            request.session.modified = True

            # هدایت به درگاه پرداخت
            return redirect(ZP_API_STARTPAY.format(authority=authority))
        else:
            peyment.delete()  # حذف رکورد ناموفق
            messages.error(request, f"خطا از زرین‌پال - کد: {response.status_code}")
            return redirect("order:cart_page")

    except Exception as e:
        messages.error(request, f"خطای غیرمنتظره: {str(e)}")
        return redirect("order:cart_page")


@method_decorator(csrf_exempt, name='dispatch')
class Zarin_pal_view_verfiy(LoginRequiredMixin, View):
    """کلاس بررسی و تایید پرداخت"""

    def get(self, request):
        status = request.GET.get('Status', '')
        authority = request.GET.get('Authority', '')

        print(f"💰 Verification started - Status: {status}, Authority: {authority}")

        # بررسی پارامترهای ورودی
        if not status or not authority:
            messages.error(request, "پارامترهای لازم ارسال نشده است")
            return redirect("order:orders")

        # بررسی وجود session
        if 'payment_data' not in request.session:
            messages.error(request, "سشن پرداخت یافت نشد")
            return redirect("order:orders")

        try:
            session_data = request.session['payment_data']
            order_id = session_data['order_id']
            payment_id = session_data['payment_id']
            amount_rials = session_data['amount_rials']

            print(f"📋 Session data - Order: {order_id}, Payment: {payment_id}")

            # پیدا کردن پرداخت و سفارش
            payment = get_object_or_404(Peyment, id=payment_id, customer=request.user)
            order = get_object_or_404(Order, id=order_id, customer=request.user)

            # پرداخت لغو شده
            if status != 'OK':
                return self.handle_cancelled_payment(request, payment, order)

            # پرداخت موفق - تایید با زرین‌پال
            return self.verify_payment(request, payment, order, authority, amount_rials)

        except Exception as e:
            print(f"❌ Error in verification: {str(e)}")
            messages.error(request, f"خطا در پردازش: {str(e)}")
            return redirect("order:orders")

    def handle_cancelled_payment(self, request, payment, order):
        """مدیریت پرداخت لغو شده"""
        try:
            # بروزرسانی سفارش
            order.status = "cancelled"
            order.save()

            # نمایش پیام
            messages.warning(request, "پرداخت توسط شما لغو شد")

            # پاک کردن session
            if 'payment_data' in request.session:
                del request.session['payment_data']

            return redirect("order:cart_page")

        except Exception as e:
            messages.error(request, f"خطا در مدیریت پرداخت لغو شده: {str(e)}")
            return redirect("order:orders")

    def verify_payment(self, request, payment, order, authority, amount_rials):
        """تایید پرداخت با زرین‌پال"""
        try:
            # درخواست تایید به زرین‌پال
            req_data = {
                "merchant_id": MERCHANT_ID,
                "amount": int(amount_rials),
                "authority": authority
            }

            headers = {
                "accept": "application/json",
                "content-type": "application/json"
            }

            print(f"📤 Sending verification request to ZarinPal: {req_data}")

            response = requests.post(
                ZP_API_VERIFY,
                data=json.dumps(req_data),
                headers=headers,
                timeout=30
            )

            print(f"📥 Response status: {response.status_code}")

            if response.status_code != 200:
                return self.handle_verification_error(
                    request, payment, order,
                    f"خطا در ارتباط با زرین‌پال - کد: {response.status_code}"
                )

            data = response.json()
            print(f"📊 Response data: {json.dumps(data, ensure_ascii=False)}")

            # بررسی خطاهای زرین‌پال
            if data.get('errors'):
                error_code = data['errors'].get('code', 'نامشخص')
                error_message = data['errors'].get('message', 'خطای نامشخص')
                return self.handle_verification_error(
                    request, payment, order,
                    f"{error_message} (کد خطا: {error_code})"
                )

            # بررسی وجود data
            if 'data' not in data:
                return self.handle_verification_error(
                    request, payment, order,
                    "پاسخ نامعتبر از زرین‌پال"
                )

            # پردازش کد وضعیت
            code = data['data'].get('code')

            if code == 100:  # پرداخت موفق
                return self.handle_successful_payment(request, payment, order, data['data'])
            elif code == 101:  # قبلا تایید شده
                return self.handle_already_verified(request, payment, order, data['data'])
            else:
                return self.handle_verification_error(
                    request, payment, order,
                    f"کد خطا از زرین‌پال: {code}"
                )

        except requests.exceptions.RequestException as e:
            return self.handle_verification_error(
                request, payment, order,
                f"خطا در ارتباط با زرین‌پال: {str(e)}"
            )
        except Exception as e:
            return self.handle_verification_error(
                request, payment, order,
                f"خطای غیرمنتظره: {str(e)}"
            )

    @transaction.atomic
    def handle_successful_payment(self, request, payment, order, data):
        """مدیریت پرداخت موفق"""
        try:
            print(f"✅ Payment successful - Processing...")

            # ذخیره refId (با استفاده از کلید صحیح از زرین‌پال)
            ref_id = data.get('ref_id')  # زرین‌پال ref_id برمی‌گرداند
            print(f"📝 Ref ID from ZarinPal: {ref_id}")

            # بروزرسانی پرداخت
            payment.isFinaly = True
            payment.statusCode = 100

            # **مهم: استفاده از ref_id دریافتی از زرین‌پال**
            if ref_id:
                payment.refId = str(ref_id)
                print(f"📋 RefId saved: {payment.refId}")
            else:
                print("⚠️ No ref_id received from ZarinPal")

            payment.save()

            # بروزرسانی سفارش
            order.isFinally = True
            order.status = "paid"
            order.save()

            # پاک کردن session
            if 'payment_data' in request.session:
                del request.session['payment_data']

            print(f"🎉 Payment and order updated successfully")

            # نمایش صفحه موفقیت
            return self.show_success_page(request, order, payment, ref_id)

        except Exception as e:
            print(f"❌ Error in successful payment: {str(e)}")
            messages.error(request, f"خطا در به‌روزرسانی اطلاعات: {str(e)}")
            return redirect("order:orders")

    def handle_already_verified(self, request, payment, order, data):
        """مدیریت پرداخت قبلا تایید شده"""
        try:
            print(f"ℹ️ Payment already verified")

            # اگر هنوز تایید نشده، تاییدش کن
            if not payment.isFinaly:
                payment.isFinaly = True
                payment.statusCode = 101

                ref_id = data.get('ref_id')
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

            messages.info(request, "این پرداخت قبلاً تأیید شده بود")
            return self.show_success_page(request, order, payment)

        except Exception as e:
            print(f"❌ Error in already verified: {str(e)}")
            messages.error(request, f"خطا در به‌روزرسانی: {str(e)}")
            return redirect("order:orders")

    def handle_verification_error(self, request, payment, order, error_message):
        """مدیریت خطای تایید"""
        try:
            print(f"❌ Verification error: {error_message}")

            # بروزرسانی وضعیت
            payment.statusCode = -1
            payment.save()

            order.status = "failed"
            order.save()

            # پاک کردن session
            if 'payment_data' in request.session:
                del request.session['payment_data']

            messages.error(request, error_message)
            return render(request, 'peyment_app/unpeyment.html', {
                'error': error_message,
                'order': order
            })

        except Exception as e:
            print(f"❌ Error in verification error handler: {str(e)}")
            messages.error(request, f"خطا در مدیریت خطا: {str(e)}")
            return redirect("order:orders")

    def show_success_page(self, request, order, payment, ref_id=None):
        """نمایش صفحه موفقیت پرداخت"""
        print(f"🎉 Showing success page - Ref ID: {ref_id}")

        context = {
            'success': True,
            'order': order,
            'payment': payment,
            'ref_id': ref_id or payment.refId,
            'message': f"پرداخت سفارش {order.orderCode} با موفقیت انجام شد"
        }
        return render(request, 'peyment_app/peyment.html', context)


# ویوهای قدیمی برای backward compatibility
def show_verfiy_message(request, message):
    """ویو قدیمی"""
    return render(request, 'peyment_app/peyment.html', {'message': message})


def show_sucess(request, message):
    """ویو قدیمی"""
    return render(request, 'peyment_app/peyment.html', {'message': message})


def show_verfiy_unmessage(request, message):
    """ویو قدیمی"""
    return render(request, 'peyment_app/unpeyment.html', {'error': message})


def payment_success(request):
    """صفحه موفقیت پرداخت"""
    return render(request, 'peyment_app/peyment.html')


def payment_error(request):
    """صفحه خطای پرداخت"""
    return render(request, 'peyment_app/unpeyment.html')