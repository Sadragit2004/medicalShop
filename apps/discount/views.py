from django.shortcuts import render
from django.utils import timezone
from datetime import datetime
from .models import DiscountBasket, DiscountDetail
from apps.product.models import Product

def get_amazing_product(request):
    # Get current time
    now = timezone.now()

    # Get all amazing discount baskets where isamzing is True and isActive is True
    amazing_discounts = DiscountBasket.objects.filter(isamzing=True, isActive=True, startDate__lte=now, endDate__gte=now)

    # Get all products from amazing discount baskets
    amazing_products = []
    for discount in amazing_discounts:
        discount_details = DiscountDetail.objects.filter(discountBasket=discount)
        for detail in discount_details:
            # Get the base price from the first sale type
            base_price = 0
            if detail.product.saleTypes.exists():
                sale_type = detail.product.saleTypes.first()
                base_price = sale_type.finalPrice

            # Calculate discounted price
            discount_percentage = discount.discount
            discount_amount = (base_price * discount_percentage) // 100
            discounted_price = base_price - discount_amount

            # Calculate remaining time
            remaining_seconds = int((discount.endDate - now).total_seconds())

            # Calculate days, hours, minutes, seconds
            days = remaining_seconds // 86400
            hours = (remaining_seconds % 86400) // 3600
            minutes = (remaining_seconds % 3600) // 60
            seconds = remaining_seconds % 60

            amazing_products.append({
                'product': detail.product,
                'discount': discount.discount,
                'discount_title': discount.discountTitle,
                'end_date': discount.endDate,
                'original_price': base_price,
                'discounted_price': discounted_price,
                'remaining_time': {
                    'days': days,
                    'hours': hours,
                    'minutes': minutes,
                    'seconds': seconds,
                    'total_seconds': remaining_seconds,
                    'timestamp': int(discount.endDate.timestamp())
                }
            })

    context = {
        'amazing_products': amazing_products,
        'amazing_discounts': amazing_discounts,
        'now_timestamp': int(now.timestamp()),
    }

    return render(request, 'discount_app/amazing.html', context)


# views.py
from django.shortcuts import render
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Avg, Q
from apps.product.models import Product,ProductSaleType, Rating
from apps.discount.models import  DiscountBasket, DiscountDetail



def amazing_products_view(request):
    """
    نمایش محصولات شگفت‌انگیز با تخفیف
    """
    now = timezone.now()

    # پیدا کردن سبدهای تخفیف شگفت‌انگیز فعال
    amazing_baskets = DiscountBasket.objects.filter(
        isActive=True,
        isamzing=True,
        startDate__lte=now,
        endDate__gte=now
    )

    # دریافت محصولات مرتبط
    if amazing_baskets.exists():
        products = Product.objects.filter(
            isActive=True,
            productOfDiscount__discountBasket__in=amazing_baskets,
        ).distinct()
    else:
        products = Product.objects.none()

    # آماده سازی اطلاعات کامل برای هر محصول
    products_list = []
    for product in products:
        # گرفتن درصد تخفیف از سبد تخفیف
        discount_basket = DiscountBasket.objects.filter(
            isActive=True,
            isamzing=True,
            startDate__lte=now,
            endDate__gte=now,
            discountOfBasket__product=product
        ).first()

        discount_percent = discount_basket.discount if discount_basket else 0

        # گرفتن قیمت از ProductSaleType - مهمترین بخش
        sale_type = product.saleTypes.filter(isActive=True).first()

        if sale_type:
            original_price = sale_type.price
            final_price = original_price * (100 - discount_percent) // 100

            # ذخیره در attributes محصول
            product.discount_percent = discount_percent
            product.original_price = original_price  # اسم جدید برای قیمت اصلی
            product.final_price = final_price
            product.has_discount = discount_percent > 0

            print(f"✅ {product.title}: قیمت اصلی={original_price}, تخفیف={discount_percent}%, قیمت نهایی={final_price}")
        else:
            # اگر نوع فروش نداشت، مقادیر پیش‌فرض
            product.discount_percent = discount_percent
            product.original_price = 0
            product.final_price = 0
            product.has_discount = False
            print(f"❌ {product.title}: نوع فروش ندارد!")

        # میانگین امتیاز
        avg_rating = Rating.objects.filter(product=product).aggregate(avg=Avg('rating'))['avg']
       

        products_list.append(product)

    # صفحه‌بندی
    paginator = Paginator(products_list, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'amazing_products': page_obj,
        'total_products': len(products_list),
    }

    return render(request, 'discount_app/all_amazing.html', context)