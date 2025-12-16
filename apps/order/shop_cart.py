# shop_cart.py
from apps.product.models import Product

class ShopCart:
    def __init__(self, request):
        self.session = request.session
        temp = self.session.get('shop_cart')
        if not temp:
            temp = self.session['shop_cart'] = {}
        self.shop_cart = temp
        self.count = len(self.shop_cart.keys())

    def _get_key(self, product_id, detail):
        return f"{product_id}:{detail}" if detail else str(product_id)

    def add_to_shop_cart(self, product, qty, list_detail=''):
        key = self._get_key(product.id, list_detail)

        # Get the price from ProductSaleType
        sale_type = product.saleTypes.filter(isActive=True).first()
        price = sale_type.finalPrice if sale_type else 0

        if key not in self.shop_cart:
            self.shop_cart[key] = {
                'qty': 0,
                'price': str(price),  # استفاده از قیمت ProductSaleType
                'brand': product.brand.id if product.brand else None,
                'detail': list_detail,
                'final_price': str(price),  # استفاده از قیمت ProductSaleType
                'product_id': product.id,
                'product_name': product.title,  # استفاده از title به جای name
                'product_image': product.mainImage.url if product.mainImage else ''
            }

        self.shop_cart[key]['qty'] += int(qty)
        self.session.modified = True
        self.count = len(self.shop_cart.keys())

    def delete_from_shop_cart(self, product, list_detail=''):
        key = self._get_key(product.id, list_detail)
        if key in self.shop_cart:
            del self.shop_cart[key]
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
                    price = sale_type.finalPrice if sale_type else 0
                    item.update({
                        'product_name': product.title,
                        'product_image': product.mainImage.url if product.mainImage else '',
                        'price': str(price),
                        'final_price': str(price)
                    })

                # Get updated price from ProductSaleType
                sale_type = product.saleTypes.filter(isActive=True).first()
                current_price = sale_type.finalPrice if sale_type else float(item.get('price', 0))

                items.append({
                    'id': item.get('product_id', key.split(':')[0]),
                    'name': item.get('product_name', ''),
                    'image': product.mainImage.url if product.mainImage else '',
                    'price': current_price,
                    'final_price': current_price,
                    'quantity': item['qty'],
                    'total_price': current_price * item['qty'],
                    'detail': item.get('detail', ''),
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