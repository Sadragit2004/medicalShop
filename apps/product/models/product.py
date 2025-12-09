from django.db import models
from django.db.models import Q, Count, Avg, Min, Max, When, Case, Value, IntegerField
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
import os
from decimal import Decimal
from .base import BaseModel, BaseManager


def product_image_path(instance, filename):
    """مسیر ذخیره عکس اصلی محصول"""
    ext = filename.split('.')[-1]
    filename = f"{instance.slug}-main.{ext}"
    return os.path.join('products', 'main', filename)


class ProductManager(BaseManager):
    """
    Manager مخصوص محصولات
    - تمام متدهای CRUD عمومی و اختصاصی
    """

    def create_product(self, title, price, description="", **extra_fields):
        """
        ایجاد محصول جدید با اعتبارسنجی
        - بررسی قیمت مثبت
        - تولید خودکار اسلاگ
        """
        if price <= 0:
            raise ValidationError("قیمت باید بزرگتر از صفر باشد")

        return self.create_record(
            title=title,
            price=price,
            description=description,
            **extra_fields
        )

    def get_by_category(self, category_slug, include_subcategories=True, **filters):
        """
        دریافت محصولات بر اساس دسته‌بندی
        - category_slug: اسلاگ دسته‌بندی
        - include_subcategories: آیا زیردسته‌ها هم شامل شوند؟
        - filters: فیلترهای اضافی
        """
        from .category import ProductCategory

        try:
            category = ProductCategory.objects.get(slug=category_slug)

            if include_subcategories:
                # تمام IDهای دسته‌بندی و زیردسته‌ها
                category_ids = [category.id] + category.get_all_children_ids()
            else:
                category_ids = [category.id]

            # ایجاد کوئری پایه
            queryset = self.filter(
                categories__id__in=category_ids,
                is_active=True
            ).distinct()

            # اعمال فیلترهای اضافی
            if filters:
                queryset = queryset.filter(**filters)

            return queryset

        except ProductCategory.DoesNotExist:
            return self.none()

    def get_by_brand(self, brand_slug, **filters):
        """
        دریافت محصولات بر اساس برند
        - brand_slug: اسلاگ برند
        - filters: فیلترهای اضافی
        """
        from .brand import Brand

        try:
            brand = Brand.objects.get(slug=brand_slug)

            queryset = self.filter(
                brand=brand,
                is_active=True
            ).distinct()

            if filters:
                queryset = queryset.filter(**filters)

            return queryset

        except Brand.DoesNotExist:
            return self.none()

    def search_products(self, search_term, search_fields=None):
        """
        جستجوی پیشرفته در محصولات
        - search_term: متن جستجو
        - search_fields: فیلدهایی که باید جستجو شوند (پیش‌فرض: title, description)
        """
        if not search_fields:
            search_fields = ['title', 'description', 'brand__title']

        query = Q()
        for field in search_fields:
            if '__' in field:  # برای جستجو در فیلدهای مرتبط
                query |= Q(**{f"{field}__icontains": search_term})
            else:
                query |= Q(**{f"{field}__icontains": search_term})

        return self.filter(is_active=True).filter(query).distinct()

    def get_price_range(self, category_slug=None, brand_slug=None):
        """
        دریافت محدوده قیمت محصولات
        - می‌تواند بر اساس دسته‌بندی یا برند فیلتر شود
        """
        queryset = self.filter(is_active=True).distinct()

        if category_slug:
            queryset = self.get_by_category(category_slug)

        if brand_slug:
            queryset = queryset.filter(brand__slug=brand_slug)

        price_stats = queryset.aggregate(
            min_price=Min('price'),
            max_price=Max('price'),
            avg_price=Avg('price')
        )

        return price_stats

    def get_products_with_filters(self, filters=None, order_by='-created_at', limit=None):
        """
        دریافت محصولات با فیلترهای پیشرفته
        - filters: دیکشنری فیلترها
          - category: اسلاگ دسته‌بندی
          - brand: اسلاگ برند
          - price_min: حداقل قیمت
          - price_max: حداکثر قیمت
          - is_wholesale: فروش عمده
          - search: جستجو
          - attributes: ویژگی‌ها (دیکشنری)
        - order_by: فیلد مرتب‌سازی
        - limit: محدودیت تعداد
        """
        queryset = self.filter(is_active=True).distinct()

        if filters:
            # فیلتر دسته‌بندی
            if 'category' in filters and filters['category']:
                queryset = self.get_by_category(filters['category'])

            # فیلتر برند
            if 'brand' in filters and filters['brand']:
                queryset = queryset.filter(brand__slug=filters['brand'])

            # فیلتر قیمت
            if 'price_min' in filters and filters['price_min']:
                queryset = queryset.filter(price__gte=filters['price_min'])

            if 'price_max' in filters and filters['price_max']:
                queryset = queryset.filter(price__lte=filters['price_max'])

            # فیلتر فروش عمده
            if 'is_wholesale' in filters:
                queryset = queryset.filter(is_wholesale_enabled=filters['is_wholesale'])

            # جستجو
            if 'search' in filters and filters['search']:
                queryset = self.search_products(filters['search'])

            # فیلتر ویژگی‌ها
            if 'attributes' in filters and isinstance(filters['attributes'], dict):
                from .attribute import ProductAttributeValue

                for attr_slug, attr_value in filters['attributes'].items():
                    if attr_value:  # اگر مقدار وجود دارد
                        # دریافت IDهای محصولات با این ویژگی
                        product_ids = ProductAttributeValue.objects.filter(
                            attribute__slug=attr_slug,
                            attribute__is_filterable=True
                        ).values_list('product_id', flat=True)

                        queryset = queryset.filter(id__in=product_ids)

        # مرتب‌سازی
        if order_by:
            queryset = queryset.order_by(order_by)

        # محدودیت تعداد
        if limit:
            queryset = queryset[:limit]

        return queryset

    def get_related_products(self, product, limit=4):
        """
        دریافت محصولات مرتبط
        - بر اساس دسته‌بندی‌های مشترک
        - بر اساس برند مشترک
        """
        # دریافت IDهای دسته‌بندی‌های محصول
        category_ids = list(product.categories.values_list('id', flat=True))

        # اگر هیچ دسته‌بندی و برندی ندارد
        if not category_ids and not product.brand:
            return self.get_new_arrivals(limit=limit)

        # ایجاد Q object برای شرایط مختلف
        q_objects = Q()

        # افزودن شرط دسته‌بندی
        if category_ids:
            q_objects |= Q(categories__id__in=category_ids)

        # افزودن شرط برند
        if product.brand:
            q_objects |= Q(brand=product.brand)

        # اعمال شرایط اصلی
        base_queryset = self.filter(
            q_objects,
            is_active=True
        ).exclude(id=product.id).distinct()

        # اگر تعداد کافی محصول مرتبط نداریم
        if base_queryset.count() < limit:
            # محصولات مرتبط
            related_list = list(base_queryset)

            # محصولات جدید برای تکمیل لیست
            needed = limit - len(related_list)
            if needed > 0:
                # محصولات جدید را جداگانه بگیریم
                existing_ids = [p.id for p in related_list]
                existing_ids.append(product.id)

                new_products = self.filter(
                    is_active=True,
                    created_at__gte=timezone.now() - timedelta(days=30)
                ).exclude(id__in=existing_ids).order_by('-created_at')[:needed]

                related_list.extend(list(new_products))

            return related_list

        # برای مرتب کردن بر اساس اولویت
        # ابتدا باید annotate کنیم
        annotated_queryset = base_queryset.annotate(
            category_score=Count(
                'categories',
                filter=Q(categories__id__in=category_ids) if category_ids else Q()
            )
        )

        # اگر برند دارد
        if product.brand:
            annotated_queryset = annotated_queryset.annotate(
                brand_score=Case(
                    When(brand=product.brand, then=Value(2)),
                    default=Value(0),
                    output_field=IntegerField()
                ),
                total_score=models.F('category_score') + models.F('brand_score')
            ).order_by('-total_score', '-created_at')
        else:
            annotated_queryset = annotated_queryset.order_by('-category_score', '-created_at')

        return annotated_queryset[:limit]

    def get_best_sellers(self, limit=10, category_slug=None):
        """
        دریافت پرفروش‌ترین محصولات
        - در آینده می‌توان با مدل سفارشات ادغام شود
        """
        queryset = self.filter(is_active=True).distinct()

        if category_slug:
            queryset = self.get_by_category(category_slug)

        # فعلاً بر اساس تاریخ ایجاد مرتب می‌کنیم
        # بعداً با سفارشات ادغام می‌شود
        return queryset.order_by('-created_at')[:limit]

    def get_new_arrivals(self, days=30, limit=10):
        """دریافت محصولات جدید (آخرین ۳۰ روز)"""
        date_threshold = timezone.now() - timedelta(days=days)

        return self.filter(
            created_at__gte=date_threshold,
            is_active=True
        ).order_by('-created_at')[:limit]

    def get_product_by_slug(self, slug):
        """
        دریافت محصول با اسلاگ
        - همراه با prefetch برای بهینه‌سازی
        """
        try:
            return self.select_related('brand').prefetch_related(
                'categories',
                'gallery_images'
            ).get(
                slug=slug,
                is_active=True
            )
        except self.model.DoesNotExist:
            return None


class Product(BaseModel):
    """
    مدل اصلی محصول
    - تمام قابلیت‌های فروش خرده و عمده
    - سیستم قیمت‌گذاری پیشرفته
    """

    description = models.TextField(
        verbose_name="توضیحات",
        help_text="توضیحات کامل محصول، ویژگی‌ها و مشخصات فنی"
    )

    categories = models.ManyToManyField(
        'ProductCategory',
        related_name='products',
        verbose_name="دسته‌بندی‌ها",
        help_text="دسته‌بندی‌های مربوط به این محصول"
    )

    brand = models.ForeignKey(
        'Brand',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name="برند",
        help_text="برند محصول (اختیاری)"
    )

    # قیمت‌گذاری
    price = models.DecimalField(
        max_digits=12,  # افزایش برای قیمت‌های بالا
        decimal_places=0,
        verbose_name="قیمت واحد (تومان)",
        help_text="قیمت پایه هر واحد محصول"
    )

    # قیمت ویژه (اختیاری)
    sale_price = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name="قیمت ویژه",
        help_text="قیمت تخفیف‌خورده (اختیاری)"
    )

    # موجودی
    stock_quantity = models.PositiveIntegerField(
        default=0,
        verbose_name="موجودی",
        help_text="تعداد موجود در انبار"
    )

    # تنظیمات فروش خرده
    min_quantity = models.PositiveIntegerField(
        default=1,
        verbose_name="حداقل تعداد خرید",
        help_text="کمترین تعداد قابل خرید در فروش خرده"
    )

    max_quantity = models.PositiveIntegerField(
        default=100,
        verbose_name="حداکثر تعداد خرید",
        help_text="بیشترین تعداد قابل خرید در فروش خرده"
    )

    # تنظیمات فروش عمده
    is_wholesale_enabled = models.BooleanField(
        default=False,
        verbose_name="فروش عمده فعال",
        help_text="اگر فعال باشد، امکان خرید عمده وجود دارد"
    )

    wholesale_min_quantity = models.PositiveIntegerField(
        default=10,
        verbose_name="حداقل تعداد برای عمده",
        help_text="کمترین تعداد برای خرید عمده"
    )

    # درصد تخفیف عمده (اختیاری)
    wholesale_discount_percent = models.PositiveIntegerField(
        default=0,
        verbose_name="درصد تخفیف عمده",
        help_text="درصد تخفیف برای خرید عمده (اختیاری)"
    )

    # تنظیمات بسته‌بندی
    is_packaged = models.BooleanField(
        default=False,
        verbose_name="محصول بسته‌بندی شده",
        help_text="اگر فعال باشد، محصول به صورت بسته‌ای فروخته می‌شود"
    )

    items_per_package = models.PositiveIntegerField(
        default=1,
        verbose_name="تعداد در هر بسته",
        help_text="تعداد آیتم در هر بسته (اگر بسته‌بندی شده باشد)"
    )

    # وزن و ابعاد
    weight_grams = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="وزن (گرم)",
        help_text="وزن محصول به گرم"
    )

    dimensions = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="ابعاد",
        help_text="ابعاد محصول (طول × عرض × ارتفاع) سانتیمتر"
    )

    # عکس شاخص
    main_image = models.ImageField(
        upload_to=product_image_path,
        verbose_name="عکس شاخص",
        help_text="تصویر اصلی محصول"
    )

    # SEO Fields
    meta_title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="متا تایتل",
        help_text="عنوان صفحه برای SEO (اگر خالی باشد، از title استفاده می‌شود)"
    )

    meta_description = models.TextField(
        blank=True,
        verbose_name="متا دسکریپشن",
        help_text="توضیحات صفحه برای SEO"
    )

    # استفاده از Manager مخصوص
    objects = ProductManager()

    class Meta:
        verbose_name = "محصول"
        verbose_name_plural = "محصولات"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug', 'is_active']),
            models.Index(fields=['price', 'is_active']),
            models.Index(fields=['created_at', 'is_active']),
        ]

    def clean(self):
        """اعتبارسنجی سفارشی"""
        super().clean()

        # قیمت باید مثبت باشد
        if self.price <= 0:
            raise ValidationError({'price': "قیمت باید بزرگتر از صفر باشد"})

        # اگر قیمت ویژه دارد، باید کمتر از قیمت اصلی باشد
        if self.sale_price and self.sale_price >= self.price:
            raise ValidationError({
                'sale_price': "قیمت ویژه باید کمتر از قیمت اصلی باشد"
            })

        # تنظیمات عمده
        if self.is_wholesale_enabled:
            if self.wholesale_min_quantity <= self.min_quantity:
                raise ValidationError({
                    'wholesale_min_quantity':
                    "حداقل تعداد عمده باید بیشتر از حداقل تعداد خرده باشد"
                })

            if self.wholesale_discount_percent > 100:
                raise ValidationError({
                    'wholesale_discount_percent':
                    "درصد تخفیف نمی‌تواند بیشتر از ۱۰۰ باشد"
                })

        # تنظیمات بسته‌بندی
        if self.is_packaged and self.items_per_package <= 0:
            raise ValidationError({
                'items_per_package':
                "تعداد در هر بسته باید بزرگتر از صفر باشد"
            })

    # ========== CRUD OPERATIONS (اضافه بر BaseModel) ==========

    def calculate_final_price(self, quantity=1, is_wholesale=False):
        """
        محاسبه قیمت نهایی بر اساس تعداد و نوع خرید
        - quantity: تعداد مورد نظر
        - is_wholesale: آیا خرید عمده است؟
        - return: قیمت نهایی به صورت Decimal
        """
        # ابتدا قیمت پایه را تعیین کن (قیمت ویژه یا عادی)
        base_price = self.sale_price if self.sale_price else self.price

        if is_wholesale and self.is_wholesale_enabled:
            # اعتبارسنجی تعداد برای عمده
            if quantity < self.wholesale_min_quantity:
                raise ValueError(
                    f"حداقل تعداد برای خرید عمده {self.wholesale_min_quantity} عدد است"
                )

            # اگر بسته‌بندی شده است
            if self.is_packaged:
                packages = (quantity + self.items_per_package - 1) // self.items_per_package
                total = packages * base_price
            else:
                total = quantity * base_price

            # اعمال تخفیف عمده
            if self.wholesale_discount_percent > 0:
                discount_amount = total * Decimal(self.wholesale_discount_percent / 100)
                total -= discount_amount

            return total

        else:
            # اعتبارسنجی تعداد برای خرده
            if quantity < self.min_quantity:
                raise ValueError(f"حداقل تعداد خرید {self.min_quantity} عدد است")

            if quantity > self.max_quantity:
                raise ValueError(f"حداکثر تعداد خرید {self.max_quantity} عدد است")

            # اگر بسته‌بندی شده است
            if self.is_packaged:
                packages = (quantity + self.items_per_package - 1) // self.items_per_package
                return packages * base_price

            return quantity * base_price

    def get_current_price(self):
        """دریافت قیمت فعلی (ویژه یا عادی)"""
        return self.sale_price if self.sale_price else self.price

    def get_discount_percent(self):
        """دریافت درصد تخفیف (اگر قیمت ویژه دارد)"""
        if self.sale_price and self.price > 0:
            discount = ((self.price - self.sale_price) / self.price) * 100
            return round(float(discount), 1)
        return 0

    def check_stock(self, quantity=1):
        """بررسی موجودی کافی"""
        if self.stock_quantity <= 0:
            return False, "ناموجود"

        if quantity > self.stock_quantity:
            return False, f"فقط {self.stock_quantity} عدد موجود است"

        return True, "موجود"

    def reduce_stock(self, quantity):
        """کاهش موجودی"""
        if quantity <= self.stock_quantity:
            self.stock_quantity -= quantity
            self.save()
            return True
        return False

    def increase_stock(self, quantity):
        """افزایش موجودی"""
        self.stock_quantity += quantity
        self.save()
        return True

    def get_gallery_images(self):
        """دریافت تصاویر گالری"""
        return self.gallery_images.filter(is_active=True).order_by('sort_order')

    def get_main_gallery_image(self):
        """دریافت تصویر اصلی گالری (یا عکس شاخص)"""
        main_gallery = self.gallery_images.filter(is_active=True, is_main=True).first()
        if main_gallery:
            return main_gallery.image
        return self.main_image

    def get_attributes(self, group_by_category=True):
        """
        دریافت ویژگی‌های محصول
        - group_by_category: گروه‌بندی بر اساس گروه ویژگی
        """
        from .attribute import ProductAttributeValue

        attribute_values = ProductAttributeValue.objects.filter(
            product=self,
            attribute__is_active=True,
            attribute__is_visible=True
        ).select_related('attribute', 'attribute__group')

        if not group_by_category:
            return [
                {
                    'title': av.attribute.title,
                    'value': av.get_value(),
                    'unit': av.attribute.unit,
                    'data_type': av.attribute.data_type,
                }
                for av in attribute_values
            ]

        # گروه‌بندی بر اساس گروه ویژگی
        grouped_attributes = {}
        for av in attribute_values:
            group_name = av.attribute.group.title if av.attribute.group else "سایر"

            if group_name not in grouped_attributes:
                grouped_attributes[group_name] = []

            grouped_attributes[group_name].append({
                'title': av.attribute.title,
                'value': av.get_value(),
                'unit': av.attribute.unit,
                'data_type': av.attribute.data_type,
            })

        return grouped_attributes

    def get_related_products(self, limit=4):
        """دریافت محصولات مرتبط"""
        return Product.objects.get_related_products(self, limit)

    def get_breadcrumbs(self):
        """دریافت مسیر ناوبری محصول - نسخه اصلاح شده"""
        from django.urls import reverse

        breadcrumbs = []

        # صفحه اصلی
        breadcrumbs.append({
            'title': 'خانه',
            'url': '/',
            'is_last': False
        })

        # اولین دسته‌بندی محصول
        first_category = self.categories.filter(is_active=True).first()

        if first_category:
            # لینک دسته‌بندی (با فرض اینکه URL محصولات دسته‌بندی دارید)
            # اگر ندارید، فعلاً از # استفاده کنید
            try:
                category_url = reverse('product:category_products', kwargs={'slug': first_category.slug})
            except:
                category_url = f"/product/category/{first_category.slug}/"

            breadcrumbs.append({
                'title': first_category.title,
                'url': category_url,
                'is_last': False
            })

        # خود محصول
        breadcrumbs.append({
            'title': self.title,
            'url': self.get_absolute_url(),
            'is_last': True
        })

        return breadcrumbs

    def get_seo_title(self):
        """دریافت عنوان SEO"""
        return self.meta_title if self.meta_title else self.title

    def get_seo_description(self):
        """دریافت توضیحات SEO"""
        if self.meta_description:
            return self.meta_description

        # ایجاد توضیحات از description
        if self.description:
            return self.description[:160]  # محدودیت متا دسکریپشن

        return f"خرید {self.title} با بهترین قیمت"

    def to_dict(self, fields=None, exclude=None, include_related=True):
        """
        تبدیل به دیکشنری (override از BaseModel)
        - include_related: آیا اطلاعات مرتبط شامل شود؟
        """
        data = super().to_dict(fields, exclude)

        # قیمت‌ها
        data['current_price'] = float(self.get_current_price())
        data['original_price'] = float(self.price) if self.sale_price else None
        data['discount_percent'] = self.get_discount_percent()

        # موجودی
        stock_available, stock_message = self.check_stock()
        data['stock_available'] = stock_available
        data['stock_message'] = stock_message
        data['stock_quantity'] = self.stock_quantity

        # فروش عمده
        data['wholesale_info'] = {
            'enabled': self.is_wholesale_enabled,
            'min_quantity': self.wholesale_min_quantity if self.is_wholesale_enabled else None,
            'discount_percent': self.wholesale_discount_percent if self.is_wholesale_enabled else None,
        } if self.is_wholesale_enabled else None

        # بسته‌بندی
        data['packaging_info'] = {
            'is_packaged': self.is_packaged,
            'items_per_package': self.items_per_package if self.is_packaged else None,
        }

        # اطلاعات مرتبط
        if include_related:
            # برند
            if self.brand:
                data['brand_info'] = {
                    'id': self.brand.id,
                    'title': self.brand.title,
                    'slug': self.brand.slug,
                    'image': self.brand.image.url if self.brand.image else None,
                }

            # دسته‌بندی‌ها
            data['categories'] = [
                {
                    'id': cat.id,
                    'title': cat.title,
                    'slug': cat.slug,
                }
                for cat in self.categories.filter(is_active=True)
            ]

            # تصاویر گالری
            gallery_images = self.get_gallery_images()
            data['gallery_images'] = [
                {
                    'id': img.id,
                    'title': img.title,
                    'image_url': img.image.url if img.image else None,
                    'is_main': img.is_main,
                }
                for img in gallery_images
            ]

        # SEO
        data['seo_title'] = self.get_seo_title()
        data['seo_description'] = self.get_seo_description()

        return data

    def get_absolute_url(self):
        """دریافت URL محصول"""
        from django.urls import reverse
        return reverse('product:detail', kwargs={'slug': self.slug})

    def __str__(self):
        price_info = f" - {self.get_current_price():,} تومان"
        stock_info = f" ({self.stock_quantity} عدد)" if self.stock_quantity > 0 else " (ناموجود)"
        return f"{self.title}{price_info}{stock_info}"