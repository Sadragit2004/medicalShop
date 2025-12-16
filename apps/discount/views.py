from django.shortcuts import render
from .models import DiscountBasket, DiscountDetail
from apps.product.models import Product

def get_amazing_product(request):
    # Get all amazing discount baskets where isamzing is True
    amazing_discounts = DiscountBasket.objects.filter(isamzing=True, isActive=True)

    # Get all products from amazing discount baskets
    amazing_products = []
    for discount in amazing_discounts:
        discount_details = DiscountDetail.objects.filter(discountBasket=discount)
        for detail in discount_details:
            amazing_products.append({
                'product': detail.product,
                'discount': discount.discount,
                'discount_title': discount.discountTitle,
                'end_date': discount.endDate,
            })

    context = {
        'amazing_products': amazing_products,
        'amazing_discounts': amazing_discounts,
    }

    return render(request, 'discount_app/amazing.html', context)