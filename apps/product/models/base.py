# base.py - همین کد شما درست است
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.core.exceptions import ValidationError

class BaseManager(models.Manager):
    """
    Manager پایه برای تمام مدل‌ها
    - همه‌ی متدهای CRUD عمومی اینجا تعریف می‌شوند
    """

    def get_active(self):
        """دریافت رکوردهای فعال"""
        return self.filter(is_active=True)

    def get_by_slug(self, slug):
        """دریافت رکورد بر اساس اسلاگ"""
        try:
            return self.get(slug=slug, is_active=True)
        except self.model.DoesNotExist:
            return None

    def create_record(self, **kwargs):
        """ایجاد رکورد جدید با اعتبارسنجی"""
        instance = self.model(**kwargs)
        instance.full_clean()  # اعتبارسنجی کامل
        instance.save()
        return instance

    def update_record(self, instance, **kwargs):
        """بروزرسانی رکورد با اعتبارسنجی"""
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        instance.full_clean()  # اعتبارسنجی کامل
        instance.save()
        return instance

    def soft_delete(self, instance):
        """حذف نرم (غیرفعال کردن)"""
        instance.is_active = False
        instance.save()
        return True

    def hard_delete(self, instance):
        """حذف کامل از دیتابیس"""
        instance.delete()
        return True

    def filter_by_params(self, **params):
        """
        فیلتر کردن بر اساس پارامترهای ورودی
        - انعطاف‌پذیر برای هر نوع فیلتری
        - پشتیبانی از exclude, order_by, limit
        """
        queryset = self.filter(is_active=True)

        for key, value in params.items():
            if key == 'exclude':
                for ex_key, ex_value in value.items():
                    queryset = queryset.exclude(**{ex_key: ex_value})
            elif key == 'order_by':
                queryset = queryset.order_by(value)
            elif key == 'limit':
                queryset = queryset[:value]
            elif '__' in key:  # برای فیلترهای پیشرفته (مثل price__gte)
                queryset = queryset.filter(**{key: value})
            elif value is not None:
                queryset = queryset.filter(**{key: value})

        return queryset

    def search(self, search_term, fields=None):
        """
        جستجو در فیلدهای مشخص شده
        - اگر fields مشخص نشود، در title و description جستجو می‌کند
        """
        from django.db.models import Q

        if not fields:
            fields = ['title', 'description']

        query = Q()
        for field in fields:
            query |= Q(**{f"{field}__icontains": search_term})

        return self.filter(is_active=True).filter(query)


class BaseModel(models.Model):
    """
    مدل پایه برای تمام مدل‌های سیستم
    - تمام فیلدهای مشترک
    - تمام متدهای CRUD پایه
    """
    title = models.CharField(max_length=255, verbose_name="عنوان")
    slug = models.SlugField(max_length=255, unique=True, verbose_name="اسلاگ")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ به‌روزرسانی")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    objects = BaseManager()

    class Meta:
        abstract = True
        ordering = ['-created_at']  # پیش‌فرض: جدیدترین اول

    def save(self, *args, **kwargs):
        """ذخیره با تولید خودکار اسلاگ"""
        if not self.slug:
            self.slug = self.generate_unique_slug()
        super().save(*args, **kwargs)

    def generate_unique_slug(self):
        """تولید اسلاگ یکتا از عنوان"""
        base_slug = slugify(self.title, allow_unicode=True)
        slug = base_slug
        counter = 1

        while self.__class__.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    # ========== CRUD OPERATIONS ==========

    def update(self, **kwargs):
        """
        بروزرسانی فیلدهای مدل
        - انعطاف‌پذیر: هر فیلدی می‌تواند بروزرسانی شود
        - خودکار اعتبارسنجی می‌کند
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        self.full_clean()  # اعتبارسنجی Django
        self.save()
        return self

    def delete(self, soft=True):
        """
        حذف رکورد
        - پیش‌فرض: حذف نرم (soft delete)
        - برای حذف کامل: delete(soft=False)
        """
        if soft:
            self.is_active = False
            self.save()
            return True
        else:
            return super().delete()

    def activate(self):
        """فعال کردن رکورد"""
        self.is_active = True
        self.save()
        return self

    def deactivate(self):
        """غیرفعال کردن رکورد"""
        self.is_active = False
        self.save()
        return self

    def get_absolute_url(self):
        """
        دریافت URL مطلق رکورد
        - باید در مدل فرزند override شود
        """
        raise NotImplementedError("این متد باید در مدل فرزند پیاده‌سازی شود")

    def to_dict(self, fields=None, exclude=None):
        """
        تبدیل مدل به دیکشنری
        - fields: فیلدهای خاصی که می‌خواهیم (اگر None، همه فیلدها)
        - exclude: فیلدهایی که نمی‌خواهیم
        """
        data = {}

        if fields is None:
            fields = [field.name for field in self._meta.fields]

        for field_name in fields:
            if exclude and field_name in exclude:
                continue

            if hasattr(self, field_name):
                value = getattr(self, field_name)

                # تبدیل مقادیر خاص
                if hasattr(value, 'url'):  # برای فیلدهای ImageField/FileField
                    value = value.url if value else None
                elif hasattr(value, 'all'):  # برای رابطه‌های ManyToMany
                    value = [item.to_dict() for item in value.all()]
                elif hasattr(value, 'to_dict'):  # برای مدل‌های دیگر
                    value = value.to_dict()

                data[field_name] = value

        return data

    def __str__(self):
        return self.title