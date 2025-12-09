from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Count, Q, F, Prefetch
from .base import BaseModel, BaseManager
import os

def category_image_path(instance, filename):
    """مسیر ذخیره عکس دسته‌بندی"""
    ext = filename.split('.')[-1]
    filename = f"{instance.slug}.{ext}"
    return os.path.join('categories', filename)


class ProductCategoryManager(BaseManager):
    """Manager مخصوص دسته‌بندی محصولات"""

    def get_root_categories(self):
        """دریافت دسته‌بندی‌های والد"""
        return self.filter(is_active=True, parent__isnull=True).order_by('title')

    def get_children(self, parent_slug=None, parent_id=None, include_self=False):
        """دریافت زیردسته‌های یک دسته‌بندی"""
        if parent_slug:
            try:
                parent = self.get(slug=parent_slug)
                parent_id = parent.id
            except self.model.DoesNotExist:
                return self.none()

        if parent_id:
            query = self.filter(parent_id=parent_id, is_active=True)
            if include_self:
                try:
                    parent = self.get(id=parent_id)
                    return list(query) + [parent]
                except self.model.DoesNotExist:
                    return list(query)
            return query

        return self.get_root_categories()

    def get_category_tree(self, parent_id=None, max_depth=None):
        """دریافت درخت کامل دسته‌بندی‌ها"""
        def build_tree(category, current_depth):
            if max_depth and current_depth >= max_depth:
                return []

            children = list(category.children.filter(is_active=True).order_by('title'))
            for child in children:
                child.children_list = build_tree(child, current_depth + 1)
            return children

        if parent_id:
            try:
                parent = self.get(id=parent_id, is_active=True)
                parent.children_list = build_tree(parent, 1)
                return parent
            except self.model.DoesNotExist:
                return None

        root_categories = self.get_root_categories()
        for category in root_categories:
            category.children_list = build_tree(category, 1)

        return root_categories

    def get_categories_with_most_products(self, limit=10, include_subcategories=True):
        """
        دریافت دسته‌بندی‌هایی که بیشترین تعداد محصول را دارند
        - شامل محصولات زیردسته‌ها هم می‌شود
        - مرتب‌سازی نزولی بر اساس تعداد محصولات
        """
        from .product import Product

        # گرفتن همه دسته‌بندی‌های فعال
        categories = self.get_active()

        results = []
        for category in categories:
            # محاسبه تعداد محصولات
            if include_subcategories:
                category_ids = [category.id] + category.get_all_children_ids()
            else:
                category_ids = [category.id]

            product_count = Product.objects.filter(
                categories__id__in=category_ids,
                is_active=True
            ).distinct().count()

            if product_count > 0:
                results.append({
                    'category': category,
                    'product_count': product_count,
                    'level': category.get_level()
                })

        # مرتب‌سازی بر اساس تعداد محصولات (بیشترین اول)
        results.sort(key=lambda x: x['product_count'], reverse=True)

        # محدود کردن تعداد
        return results[:limit]

    def get_categories_with_product_count(self):
        """دریافت دسته‌بندی‌ها همراه با تعداد محصولات"""
        from .product import Product
        from django.db.models import Count

        # روش بهینه: استفاده از annotate برای شمردن محصولات
        categories = self.filter(is_active=True).annotate(
            product_count=Count(
                'products',
                filter=Q(products__is_active=True),
                distinct=True
            )
        )

        return categories

    def get_popular_categories(self, limit=8, min_products=1):
        """
        دریافت دسته‌بندی‌های پرمخاطب - نسخه اصلاح شده
        - دسته‌بندی‌هایی که حداقل min_products محصول دارند
        - بر اساس تعداد محصولات مرتب می‌شوند
        """
        from django.db.models import Count, Q

        # روش 1: استفاده از annotate و filter - سریع و بهینه
        popular_categories = self.filter(
            is_active=True
        ).annotate(
            product_count=Count(
                'products',
                filter=Q(products__is_active=True),
                distinct=True
            )
        ).filter(
            product_count__gte=min_products
        ).order_by(
            '-product_count'
        )[:limit]

        return list(popular_categories)

    def get_category_stats(self):
        """دریافت آمار کلی دسته‌بندی‌ها"""
        from django.db.models import Count, Q

        stats = {
            'total_categories': self.filter(is_active=True).count(),
            'root_categories': self.filter(is_active=True, parent__isnull=True).count(),
            'categories_with_products': 0,
            'categories_without_products': 0,
        }

        # محاسبه با annotate
        categories_with_counts = self.filter(is_active=True).annotate(
            product_count=Count('products', filter=Q(products__is_active=True))
        )

        for category in categories_with_counts:
            if category.product_count > 0:
                stats['categories_with_products'] += 1
            else:
                stats['categories_without_products'] += 1

        return stats

    def get_breadcrumbs(self, category):
        """دریافت مسیر ناوبری (breadcrumb)"""
        breadcrumbs = []

        def add_parents(cat):
            if cat.parent:
                add_parents(cat.parent)
                breadcrumbs.append({
                    'title': cat.parent.title,
                    'slug': cat.parent.slug,
                    'url': cat.parent.get_absolute_url()
                })

        add_parents(category)
        breadcrumbs.append({
            'title': category.title,
            'slug': category.slug,
            'url': category.get_absolute_url(),
            'is_current': True
        })

        return breadcrumbs

    def create_category(self, title, parent=None, **extra_fields):
        """ایجاد دسته‌بندی جدید"""
        # بررسی والد
        if parent:
            # جلوگیری از انتخاب خود به عنوان والد
            if parent.title == title:
                raise ValidationError("دسته‌بندی نمی‌تواند والد خودش باشد")

            # بررسی حلقه در سلسله‌مراتب
            current = parent
            while current.parent:
                if current.parent.title == title:
                    raise ValidationError("حلقه در سلسله‌مراتب ایجاد شده است")
                current = current.parent

        return self.create_record(
            title=title,
            parent=parent,
            **extra_fields
        )

    def search_categories(self, search_term, search_in_subcategories=True):
        """
        جستجو در دسته‌بندی‌ها
        - در title و description جستجو می‌کند
        - اگر search_in_subcategories=True، در زیردسته‌ها هم جستجو می‌کند
        """
        # جستجو در دسته‌بندی‌های اصلی
        main_results = self.filter(
            Q(title__icontains=search_term) |
            Q(description__icontains=search_term),
            is_active=True
        ).distinct()

        if not search_in_subcategories:
            return main_results

        # پیدا کردن والدهای دسته‌بندی‌های یافت شده
        all_categories = list(main_results)
        for category in main_results:
            # اضافه کردن تمام والدها
            parent = category.parent
            while parent:
                if parent not in all_categories:
                    all_categories.append(parent)
                parent = parent.parent

        return all_categories

    def get_all_active_categories(self):
        """دریافت تمام دسته‌بندی‌های فعال"""
        return self.filter(is_active=True).order_by('display_order', 'title')


class ProductCategory(BaseModel):
    """مدل دسته‌بندی محصولات (سلسله‌مراتبی)"""

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name="دسته‌بندی والد",
        help_text="اگر این دسته‌بندی زیرمجموعه‌ی دسته‌بندی دیگری است"
    )

    description = models.TextField(
        blank=True,
        verbose_name="توضیحات",
        help_text="توضیحات کامل دسته‌بندی"
    )

    image = models.ImageField(
        upload_to=category_image_path,
        null=True,
        blank=True,
        verbose_name="عکس دسته‌بندی",
        help_text="تصویر شاخص دسته‌بندی"
    )

    # ترتیب نمایش سفارشی
    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name="ترتیب نمایش",
        help_text="برای مرتب‌سازی دسته‌بندی‌ها در منو"
    )

    # برای SEO
    meta_title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="متا تایتل",
        help_text="عنوان صفحه برای SEO"
    )

    meta_description = models.TextField(
        blank=True,
        verbose_name="متا دسکریپشن",
        help_text="توضیحات صفحه برای SEO"
    )

    # استفاده از Manager مخصوص
    objects = ProductCategoryManager()

    class Meta:
        verbose_name = "دسته‌بندی محصول"
        verbose_name_plural = "دسته‌بندی محصولات"
        ordering = ['display_order', 'title']
        indexes = [
            models.Index(fields=['slug', 'is_active']),
            models.Index(fields=['parent', 'is_active']),
            models.Index(fields=['display_order', 'is_active']),
        ]

    def clean(self):
        """اعتبارسنجی سفارشی"""
        super().clean()

        # بررسی اینکه والد، خودش نباشد
        if self.parent and self.parent.id == self.id:
            raise ValidationError({
                'parent': "یک دسته‌بندی نمی‌تواند والد خودش باشد."
            })

        # بررسی حلقه در سلسله‌مراتب
        if self.parent:
            parent = self.parent
            visited = {self.id}

            while parent:
                if parent.id in visited:
                    raise ValidationError({
                        'parent': "حلقه در سلسله‌مراتب دسته‌بندی ایجاد شده است."
                    })
                visited.add(parent.id)
                parent = parent.parent

    # ========== CRUD OPERATIONS ==========

    def get_all_children_ids(self):
        """دریافت تمام IDهای زیردسته‌ها (بازگشتی)"""
        children_ids = []

        def get_children(category):
            for child in category.children.filter(is_active=True):
                children_ids.append(child.id)
                get_children(child)

        get_children(self)
        return children_ids

    def get_all_children(self):
        """دریافت تمام زیردسته‌ها (بازگشتی)"""
        children = []

        def get_children(category):
            for child in category.children.filter(is_active=True):
                children.append(child)
                get_children(child)

        get_children(self)
        return children

    def get_descendants(self, include_self=False):
        """دریافت تمام نوادگان (زیردسته‌های زیردسته‌ها)"""
        descendants = []

        if include_self:
            descendants.append(self)

        for child in self.children.filter(is_active=True):
            descendants.append(child)
            descendants.extend(child.get_descendants())

        return descendants

    def get_ancestors(self, include_self=False):
        """دریافت تمام اجداد (والدهای والدها)"""
        ancestors = []

        if include_self:
            ancestors.append(self)

        parent = self.parent
        while parent:
            ancestors.append(parent)
            parent = parent.parent

        # معکوس کردن لیست (از ریشه به پایین)
        return list(reversed(ancestors))

    def get_level(self):
        """دریافت سطح دسته‌بندی در سلسله‌مراتب"""
        level = 0
        parent = self.parent
        while parent:
            level += 1
            parent = parent.parent
        return level

    def get_products(self, include_children=True, **filters):
        """
        دریافت محصولات این دسته‌بندی
        - include_children: آیا محصولات زیردسته‌ها هم شامل شود؟
        - filters: فیلترهای دلخواه برای محصولات
        """
        from .product import Product

        if include_children:
            category_ids = [self.id] + self.get_all_children_ids()
        else:
            category_ids = [self.id]

        queryset = Product.objects.filter(
            categories__id__in=category_ids,
            is_active=True
        ).distinct()

        if filters:
            queryset = queryset.filter(**filters)

        return queryset

    def get_products_count(self, include_children=True):
        """تعداد محصولات این دسته‌بندی"""
        if include_children:
            category_ids = [self.id] + self.get_all_children_ids()
        else:
            category_ids = [self.id]

        from .product import Product
        return Product.objects.filter(
            categories__id__in=category_ids,
            is_active=True
        ).distinct().count()

    def get_filterable_attributes(self):
        """
        دریافت ویژگی‌های قابل فیلتر برای این دسته‌بندی
        - ویژگی‌هایی که در محصولات این دسته‌بندی استفاده شده‌اند
        """
        from .attribute import Attribute

        product_ids = self.get_products().values_list('id', flat=True)

        if not product_ids:
            return Attribute.objects.none()

        return Attribute.objects.filter(
            is_active=True,
            is_filterable=True,
            product_values__product_id__in=product_ids
        ).distinct().order_by('sort_order', 'title')

    def get_brands(self):
        """دریافت برندهایی که در این دسته‌بندی محصول دارند"""
        from .brand import Brand

        return Brand.objects.filter(
            products__categories=self,
            products__is_active=True,
            is_active=True
        ).distinct().order_by('title')

    def get_price_range(self):
        """دریافت محدوده قیمت محصولات این دسته‌بندی"""
        from django.db.models import Min, Max

        products = self.get_products()

        if not products.exists():
            return {'min': 0, 'max': 0, 'avg': 0}

        price_stats = products.aggregate(
            min_price=Min('price'),
            max_price=Max('price'),
            avg_price=models.Avg('price')
        )

        return {
            'min': price_stats['min_price'] or 0,
            'max': price_stats['max_price'] or 0,
            'avg': price_stats['avg_price'] or 0
        }

    def move_to(self, new_parent):
        """انتقال دسته‌بندی به والد جدید"""
        if new_parent and new_parent.id == self.id:
            raise ValidationError("دسته‌بندی نمی‌تواند والد خودش باشد")

        # بررسی حلقه
        if new_parent:
            parent = new_parent
            while parent:
                if parent.id == self.id:
                    raise ValidationError("حلقه در سلسله‌مراتب ایجاد می‌شود")
                parent = parent.parent

        self.parent = new_parent
        self.save()
        return self

    def get_siblings(self, include_self=False):
        """دریافت خواهر و برادرهای این دسته‌بندی"""
        if self.parent:
            siblings = self.parent.children.filter(is_active=True)
        else:
            siblings = ProductCategory.objects.get_root_categories()

        if not include_self:
            siblings = siblings.exclude(id=self.id)

        return siblings

    def get_next_sibling(self):
        """دریافت دسته‌بندی بعدی در همین سطح"""
        siblings = self.get_siblings(include_self=False)
        return siblings.filter(display_order__gt=self.display_order).order_by('display_order').first()

    def get_previous_sibling(self):
        """دریافت دسته‌بندی قبلی در همین سطح"""
        siblings = self.get_siblings(include_self=False)
        return siblings.filter(display_order__lt=self.display_order).order_by('-display_order').first()

    def get_seo_title(self):
        """دریافت عنوان SEO"""
        return self.meta_title if self.meta_title else self.title

    def get_seo_description(self):
        """دریافت توضیحات SEO"""
        if self.meta_description:
            return self.meta_description

        if self.description:
            return self.description[:160]

        return f"محصولات دسته‌بندی {self.title} با بهترین قیمت"

    def to_dict(self, fields=None, exclude=None, include_related=True):
        """تبدیل به دیکشنری"""
        data = super().to_dict(fields, exclude)

        # اطلاعات والد
        if self.parent:
            data['parent'] = {
                'id': self.parent.id,
                'title': self.parent.title,
                'slug': self.parent.slug,
            }

        # تعداد فرزندان
        data['children_count'] = self.children.filter(is_active=True).count()

        # تعداد محصولات
        data['products_count'] = self.get_products_count()

        # سطح در سلسله‌مراتب
        data['level'] = self.get_level()

        # آدرس تصویر
        if self.image:
            data['image_url'] = self.image.url

        # SEO
        data['seo_title'] = self.get_seo_title()
        data['seo_description'] = self.get_seo_description()

        # اطلاعات مرتبط
        if include_related:
            # برندها
            data['brands'] = [
                {
                    'id': brand.id,
                    'title': brand.title,
                    'slug': brand.slug,
                }
                for brand in self.get_brands()[:10]  # محدود به 10 برند
            ]

            # ویژگی‌های قابل فیلتر
            data['filterable_attributes'] = [
                {
                    'id': attr.id,
                    'title': attr.title,
                    'slug': attr.slug,
                    'data_type': attr.data_type,
                }
                for attr in self.get_filterable_attributes()[:10]
            ]

        return data

    def get_absolute_url(self):
        """دریافت URL این دسته‌بندی"""
        from django.urls import reverse
        return reverse('product:category_detail', kwargs={'slug': self.slug})

    def __str__(self):
        if self.parent:
            return f"{self.parent.title} → {self.title}"
        return self.title