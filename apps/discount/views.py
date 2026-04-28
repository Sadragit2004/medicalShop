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