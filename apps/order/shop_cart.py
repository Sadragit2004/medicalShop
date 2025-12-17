# shop_cart.py
from apps.product.models import Product
from apps.discount.models import DiscountBasket
from django.utils import timezone

class ShopCart:
    def __init__(self, request):
        self.session = request.session
        temp = self.session.get('shop_cart')
        if not temp:
            temp = self.session['shop_cart'] = {}
        self.shop_cart = temp
        self.count = len(self.shop_cart.keys())

    def _get_key(self, product_id, detail, sale_type=1):
        """Generate a consistent key that always includes sale_type"""
        return f"{product_id}:{sale_type}:{detail}"

    def add_to_shop_cart(self, product, qty, list_detail='', sale_type_id=None):
        # Use consistent key generation
        actual_sale_type = sale_type_id or 1
        key = self._get_key(product.id, list_detail, actual_sale_type)

        # Get the specific sale type or default to first active
        if sale_type_id:
            sale_type = product.saleTypes.filter(isActive=True, typeSale=sale_type_id).first()
        else:
            sale_type = product.saleTypes.filter(isActive=True).first()

        # Calculate base price based on sale type
        if sale_type:
            if sale_type.typeSale == 2 and sale_type.memberCarton:  # Carton sale
                base_price = sale_type.price * sale_type.memberCarton  # Per carton price
            else:
                base_price = sale_type.price  # Per item price
        else:
            base_price = 0

        # Calculate discounted price
        now = timezone.now()
        discount_percent = DiscountBasket.objects.filter(
            isActive=True,
            startDate__lte=now,
            endDate__gte=now,
            discountOfBasket__product=product
        ).order_by('-discount').values_list('discount', flat=True).first() or 0

        final_price = base_price
        if discount_percent > 0:
            final_price = int(base_price * (100 - discount_percent) / 100)

        if key not in self.shop_cart:
            self.shop_cart[key] = {
                'qty': 0,
                'price': str(base_price),  # قیمت پایه
                'brand': product.brand.id if product.brand else None,
                'detail': list_detail,
                'final_price': str(final_price),  # قیمت نهایی با تخفیف
                'discount_percent': discount_percent,  # درصد تخفیف
                'sale_type': actual_sale_type,  # نوع فروش
                'member_carton': sale_type.memberCarton if sale_type else 1,  # تعداد در کارتن
                'product_id': product.id,
                'product_name': product.title,
                'product_image': product.mainImage.url if product.mainImage else '',
                'sale_type_title': sale_type.get_typeSale_display() if sale_type else 'تک فروشی'
            }

        self.shop_cart[key]['qty'] += int(qty)
        self.session.modified = True
        self.count = len(self.shop_cart.keys())

    def delete_from_shop_cart(self, product, list_detail='', sale_type_id=None):
        # Use the same key logic as add_to_shop_cart
        actual_sale_type = sale_type_id or 1
        key = self._get_key(product.id, list_detail, actual_sale_type)

        # Try to delete with the new key format
        if key in self.shop_cart:
            del self.shop_cart[key]
            self.count = len(self.shop_cart.keys())
            self.session.modified = True
            return

        # Fallback: try old key format (without sale_type) for backward compatibility
        old_key = f"{product.id}:{list_detail}" if list_detail else str(product.id)
        if old_key in self.shop_cart:
            del self.shop_cart[old_key]
            self.count = len(self.shop_cart.keys())
            self.session.modified = True
            return

        # If neither key works, try all keys that match the product_id
        keys_to_remove = []
        for cart_key in self.shop_cart.keys():
            if cart_key.startswith(f"{product.id}:"):
                cart_item = self.shop_cart[cart_key]
                if cart_item.get('product_id') == product.id:
                    keys_to_remove.append(cart_key)

        for cart_key in keys_to_remove:
            del self.shop_cart[cart_key]

        if keys_to_remove:
            self.count = len(self.shop_cart.keys())
            self.session.modified = True

    def delete_all_list(self):
        self.shop_cart.clear()
        self.count = 0
        self.session.modified = True

    def get_cart_items(self):
        """دریافت آیتم‌های سبد خرید به صورت قابل سریالایز"""
        items = []
        for key, item in self.shop_cart.items():
            try:
                # همیشه محصول را از دیتابیس بگیر
                product = Product.objects.get(id=item.get('product_id', key.split(':')[0]))

                # اگر اطلاعات محصول کامل نیست، بروزرسانی کن
                if 'product_name' not in item:
                    sale_type = product.saleTypes.filter(isActive=True).first()
                    base_price = sale_type.finalPrice if sale_type else 0

                    # Only update if final_price is not already set (preserve discounted prices)
                    if 'final_price' not in item or not item.get('final_price'):
                        item['final_price'] = str(base_price)

                    item.update({
                        'product_name': product.title,
                        'product_image': product.mainImage.url if product.mainImage else '',
                        'price': item.get('price', str(base_price)),  # Don't overwrite existing price
                        'sale_type': item.get('sale_type', sale_type.typeSale if sale_type else 1),
                        'member_carton': item.get('member_carton', sale_type.memberCarton if sale_type else 1),
                        'sale_type_title': item.get('sale_type_title', sale_type.get_typeSale_display() if sale_type else 'تک فروشی')
                    })

                # Use the stored discounted price from cart, fallback to ProductSaleType if not available
                current_price = float(item.get('final_price', item.get('price', 0)))

                items.append({
                    'id': item.get('product_id', key.split(':')[0]),
                    'name': item.get('product_name', ''),
                    'image': product.mainImage.url if product.mainImage else '',
                    'price': current_price,
                    'final_price': current_price,
                    'quantity': item['qty'],
                    'total_price': current_price * item['qty'],
                    'detail': item.get('detail', ''),
                    'sale_type': item.get('sale_type', 1),
                    'member_carton': item.get('member_carton', 1),
                    'sale_type_title': item.get('sale_type_title', 'تک فروشی'),
                    'key': key  # کلید یکتا برای مدیریت
                })
            except Product.DoesNotExist:
                # اگر محصول وجود ندارد، این آیتم را رد کن
                continue

        return items

    def calc_total_price(self):
        total = 0
        for item in self.get_cart_items():
            total += item['total_price']
        return total

    def __iter__(self):
        """برای backward compatibility"""
        for item in self.get_cart_items():
            yield item