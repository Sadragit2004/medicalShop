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

        # ========================
        # بررسی موجودی محصول
        # ========================
        if product.stock <= 0:
            raise ValueError(f"محصول '{product.title}' موجودی ندارد")

        # محاسبه مقدار فعلی در سبد خرید
        current_qty_in_cart = 0
        if key in self.shop_cart:
            current_qty_in_cart = self.shop_cart[key]['qty']

        # مقدار نهایی بعد از افزودن
        new_total_qty = current_qty_in_cart + int(qty)

        # بررسی اینکه از موجودی بیشتر نشود
        if new_total_qty > product.stock:
            remaining = product.stock - current_qty_in_cart
            if remaining <= 0:
                raise ValueError(f"محصول '{product.title}' به مقدار حداکثر {product.stock} عدد موجود است و شما قبلاً {current_qty_in_cart} عدد در سبد دارید")
            else:
                raise ValueError(f"موجودی محصول '{product.title}' کافی نیست. تنها {remaining} عدد دیگر می‌توانید اضافه کنید")

        # بررسی محدودیت‌های حداقل خرید بر اساس نوع فروش
        if sale_type:
            if sale_type.typeSale == 2 and sale_type.memberCarton:  # فروش کارتن
                # برای فروش کارتن، تعداد باید مضربی از memberCarton باشد
                if new_total_qty % sale_type.memberCarton != 0:
                    raise ValueError(f"تعداد باید مضربی از {sale_type.memberCarton} باشد (تعداد هر کارتن)")
                # بررسی حداقل تعداد کارتن
                min_cartons = sale_type.limitedSale or 1
                min_qty = min_cartons * sale_type.memberCarton
                if new_total_qty < min_qty:
                    raise ValueError(f"حداقل تعداد برای این محصول {min_cartons} کارتن ({min_qty} عدد) است")
            elif sale_type.typeSale == 3:  # فروش محدود با حداقل خرید
                min_qty = sale_type.limitedSale or 1
                if new_total_qty < min_qty:
                    raise ValueError(f"حداقل تعداد برای این محصول {min_qty} عدد است")
            elif sale_type.typeSale == 1:  # فروش تک
                if new_total_qty < 1:
                    raise ValueError(f"حداقل تعداد برای این محصول 1 عدد است")

        # محاسبه قیمت پایه بر اساس نوع فروش
        if sale_type:
            if sale_type.typeSale == 2 and sale_type.memberCarton:  # فروش کارتن
                base_price = sale_type.price  # قیمت هر کارتن
            else:
                base_price = sale_type.price  # قیمت هر عدد
        else:
            base_price = 0

        # محاسبه قیمت با تخفیف
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
                'price': str(base_price),
                'brand': product.brand.id if product.brand else None,
                'detail': list_detail,
                'final_price': str(final_price),
                'discount_percent': discount_percent,
                'sale_type': actual_sale_type,
                'member_carton': sale_type.memberCarton if sale_type else 1,
                'product_id': product.id,
                'product_name': product.title,
                'product_image': product.mainImage.url if product.mainImage else '',
                'sale_type_title': sale_type.get_typeSale_display() if sale_type else 'تک فروشی'
            }

        self.shop_cart[key]['qty'] = new_total_qty
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

                # Get sale type info for minimum purchase limits
                sale_type_obj = None
                limited_sale = 1
                if 'sale_type' in item:
                    sale_type_obj = product.saleTypes.filter(isActive=True, typeSale=item['sale_type']).first()
                    if sale_type_obj:
                        limited_sale = sale_type_obj.limitedSale or 1

                items.append({
                    'id': item.get('product_id', key.split(':')[0]),
                    'title': item.get('product_name', ''),
                    'image': product.mainImage.url if product.mainImage else '',
                    'price': current_price,
                    'quantity': item['qty'],
                    'total_price': current_price * item['qty'],
                    'detail': item.get('detail', ''),
                    'sale_type': item.get('sale_type', 1),
                    'member_carton': item.get('member_carton', 1),
                    'limited_sale': limited_sale,
                    'min_quantity': limited_sale if item.get('sale_type', 1) in [2, 3] else 1,
                    'shipping_days': 1,  # Default shipping days
                    'color': '',  # Default empty color
                    'warranty': 'گارانتی ۱۸ ماهه',  # Default warranty
                    'key': key,  # کلید یکتا برای مدیریت
                    'max_stock': product.stock  # اضافه کردن حداکثر موجودی برای استفاده در فرانت
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

    def update_quantity(self, product_id, new_quantity, detail='', sale_type=1):
        """آپدیت مستقیم تعداد یک محصول در سبد خرید"""
        key = self._get_key(product_id, detail, sale_type)

        if key not in self.shop_cart:
            raise ValueError("محصول در سبد خرید وجود ندارد")

        # دریافت محصول از دیتابیس برای بررسی موجودی
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise ValueError("محصول یافت نشد")

        # بررسی موجودی
        if new_quantity > product.stock:
            raise ValueError(f"موجودی کافی نیست. فقط {product.stock} عدد موجود است")

        if new_quantity < 1:
            raise ValueError("تعداد باید حداقل ۱ باشد")

        # بررسی محدودیت‌های نوع فروش
        sale_type_obj = product.saleTypes.filter(isActive=True, typeSale=sale_type).first()
        if sale_type_obj:
            if sale_type_obj.typeSale == 2 and sale_type_obj.memberCarton:  # فروش کارتن
                if new_quantity % sale_type_obj.memberCarton != 0:
                    raise ValueError(f"تعداد باید مضربی از {sale_type_obj.memberCarton} باشد (تعداد هر کارتن)")
                min_cartons = sale_type_obj.limitedSale or 1
                min_qty = min_cartons * sale_type_obj.memberCarton
                if new_quantity < min_qty:
                    raise ValueError(f"حداقل تعداد برای این محصول {min_cartons} کارتن ({min_qty} عدد) است")
            elif sale_type_obj.typeSale == 3:  # فروش محدود
                min_qty = sale_type_obj.limitedSale or 1
                if new_quantity < min_qty:
                    raise ValueError(f"حداقل تعداد برای این محصول {min_qty} عدد است")

        # آپدیت تعداد
        self.shop_cart[key]['qty'] = new_quantity
        self.session.modified = True

        # برگرداندن اطلاعات جدید
        return {
            'new_quantity': new_quantity,
            'item_total': float(self.shop_cart[key]['final_price']) * new_quantity,
            'cart_total': self.calc_total_price(),
            'cart_count': sum(item['qty'] for item in self.shop_cart.values())
        }