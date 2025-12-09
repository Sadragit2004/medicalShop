# product_app/models/comment.py
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from .base import BaseModel, BaseManager
from apps.user.models.user import CustomUser


class ProductCommentManager(BaseManager):
    """
    Manager مخصوص نظرات محصولات
    """

    def get_for_product(self, product_slug=None, product_id=None, only_approved=True):
        """
        دریافت نظرات یک محصول
        - product_slug: اسلاگ محصول
        - product_id: ID محصول
        - only_approved: فقط نظرات تأیید شده
        """
        query = self.filter(is_active=True)

        if only_approved:
            query = query.filter(is_approved=True)

        if product_slug:
            from .product import Product
            try:
                product = Product.objects.get(slug=product_slug)
                query = query.filter(product=product)
            except Product.DoesNotExist:
                return self.none()
        elif product_id:
            query = query.filter(product_id=product_id)

        return query.order_by('-created_at')

    def get_recent_comments(self, limit=10, only_approved=True):
        """دریافت آخرین نظرات"""
        query = self.filter(is_active=True)

        if only_approved:
            query = query.filter(is_approved=True)

        return query.order_by('-created_at')[:limit]

    def get_unapproved_comments(self):
        """دریافت نظرات تأیید نشده"""
        return self.filter(
            is_active=True,
            is_approved=False
        ).order_by('-created_at')

    def approve_comment(self, comment_id):
        """تأیید یک نظر"""
        try:
            comment = self.get(id=comment_id)
            comment.is_approved = True
            comment.save()
            return comment
        except self.model.DoesNotExist:
            return None

    def create_comment(self, product, user, content, rating=5, **extra_fields):
        """
        ایجاد نظر جدید
        """
        # بررسی تکراری نبودن نظر
        existing = self.filter(
            product=product,
            user=user,
            is_active=True
        ).exists()

        if existing:
            raise ValidationError("شما قبلاً برای این محصول نظر داده‌اید.")

        # بررسی امتیاز
        if rating < 1 or rating > 5:
            raise ValidationError("امتیاز باید بین 1 تا 5 باشد.")

        return self.create_record(
            product=product,
            user=user,
            content=content,
            rating=rating,
            **extra_fields
        )

    def get_average_rating(self, product):
        """دریافت میانگین امتیاز محصول"""
        result = self.filter(
            product=product,
            is_approved=True,
            is_active=True
        ).aggregate(
            avg_rating=models.Avg('rating'),
            count=models.Count('id')
        )

        return {
            'average': result['avg_rating'] or 0,
            'count': result['count'] or 0
        }


class ProductComment(BaseModel):
    """
    مدل نظر (کامنت) محصول
    - یک طرفه - بدون پاسخ
    """
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name="محصول",
        help_text="محصول مربوطه"
    )

    user = models.ForeignKey(
        CustomUser,  # تغییر دهید به مدل کاربر شما
        on_delete=models.CASCADE,
        related_name='product_comments',
        verbose_name="کاربر",
        help_text="کاربری که نظر داده است"
    )

    content = models.TextField(
        verbose_name="متن نظر",
        help_text="متن کامل نظر کاربر"
    )

    rating = models.PositiveSmallIntegerField(
        default=5,
        verbose_name="امتیاز",
        help_text="امتیاز از 1 تا 5",
        choices=[
            (1, 'خیلی بد'),
            (2, 'بد'),
            (3, 'متوسط'),
            (4, 'خوب'),
            (5, 'عالی'),
        ]
    )

    is_approved = models.BooleanField(
        default=False,
        verbose_name="تأیید شده",
        help_text="آیا نظر توسط ادمین تأیید شده است؟"
    )

    objects = ProductCommentManager()

    class Meta:
        verbose_name = "نظر محصول"
        verbose_name_plural = "نظرات محصولات"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'is_approved', 'is_active']),
            models.Index(fields=['user', 'is_active']),
        ]

    def clean(self):
        """اعتبارسنجی سفارشی"""
        super().clean()

        # بررسی امتیاز
        if self.rating < 1 or self.rating > 5:
            raise ValidationError({'rating': "امتیاز باید بین 1 تا 5 باشد."})

        # بررسی طول متن
        if len(self.content.strip()) < 10:
            raise ValidationError({'content': "متن نظر باید حداقل 10 کاراکتر باشد."})

    def approve(self):
        """تأیید این نظر"""
        self.is_approved = True
        self.save()
        return self

    def get_user_display_name(self):
        """دریافت نام نمایشی کاربر"""
        if hasattr(self.user, 'get_full_name'):
            full_name = self.user.get_full_name()
            if full_name.strip():
                return full_name

        return self.user.username if self.user.username else "کاربر ناشناس"

    def get_user_avatar(self):
        """دریافت آواتار کاربر"""
        if hasattr(self.user, 'avatar') and self.user.avatar:
            return self.user.avatar.url

        return None

    def get_rating_stars(self):
        """دریافت ستاره‌های امتیاز"""
        stars = []
        for i in range(1, 6):
            stars.append({
                'filled': i <= self.rating,
                'value': i
            })
        return stars

    def get_formatted_date(self):
        """دریافت تاریخ فرمت شده"""
        from django.utils.timesince import timesince
        time_diff = timezone.now() - self.created_at

        if time_diff.days < 1:
            return timesince(self.created_at, timezone.now()) + " پیش"
        elif time_diff.days == 1:
            return "دیروز"
        elif time_diff.days < 7:
            return f"{time_diff.days} روز پیش"
        else:
            return self.created_at.strftime("%Y/%m/%d")

    def to_dict(self, fields=None, exclude=None):
        """
        تبدیل به دیکشنری
        """
        data = super().to_dict(fields, exclude)

        # اطلاعات کاربر
        data['user_info'] = {
            'id': self.user.id,
            'username': self.user.username,
            'display_name': self.get_user_display_name(),
            'avatar': self.get_user_avatar(),
        }

        # اطلاعات محصول
        data['product_info'] = {
            'id': self.product.id,
            'title': self.product.title,
            'slug': self.product.slug,
        }

        # اطلاعات اضافی
        data['rating_stars'] = self.get_rating_stars()
        data['formatted_date'] = self.get_formatted_date()

        return data

    def __str__(self):
        return f"نظر {self.user.username} برای {self.product.title}"