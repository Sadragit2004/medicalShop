from django.db import models

from django.utils.text import slugify
from apps.product.models import Product
from apps.user.models.user import CustomUser
from ckeditor_uploader.fields import RichTextUploadingField


# ========================
# دسته‌بندی بلاگ (BlogCategory)
# ========================
class BlogCategory(models.Model):
    title = models.CharField(max_length=200, verbose_name="عنوان دسته‌بندی")
    slug = models.SlugField(max_length=200, unique=True, verbose_name="اسلاگ", allow_unicode=True)
    description = models.TextField(blank=True, verbose_name="توضیحات")
    createdAt = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updatedAt = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    isActive = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "دسته‌بندی بلاگ"
        verbose_name_plural = "دسته‌بندی‌های بلاگ"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


# ========================
# پست بلاگ (BlogPost)
# ========================
class BlogPost(models.Model):
    title = models.CharField(max_length=200, verbose_name="عنوان پست")
    slug = models.SlugField(max_length=200, unique=True, verbose_name="اسلاگ", allow_unicode=True)
    content = models.TextField(verbose_name="محتوای پست")
    description = RichTextUploadingField(
        verbose_name="توضیحات محصول", config_name="special", blank=True, null=True
    )
    mainImage = models.ImageField(upload_to='blog/posts/', blank=True, null=True, verbose_name="تصویر اصلی")
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="نویسنده", related_name="blog_posts")

    # رابطه یک به چند با محصول
    products = models.ManyToManyField(Product, blank=True, verbose_name="محصولات مرتبط", related_name="blog_posts")

    category = models.ForeignKey(BlogCategory, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="دسته‌بندی", related_name="posts")

    # فیلدهای SEO
    meta_title = models.CharField(max_length=200, blank=True, verbose_name="عنوان متا")
    meta_description = models.TextField(blank=True, verbose_name="توضیحات متا")

    # آمار
    view_count = models.PositiveIntegerField(default=0, verbose_name="تعداد بازدید")
    like_count = models.PositiveIntegerField(default=0, verbose_name="تعداد لایک")

    createdAt = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updatedAt = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    publishedAt = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ انتشار")
    isActive = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "پست بلاگ"
        verbose_name_plural = "پست‌های بلاگ"
        ordering = ['-createdAt']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def comment_count(self):
        """تعداد کامنت‌های پست"""
        return self.comments.count()

    @property
    def is_published(self):
        """بررسی اینکه پست منتشر شده یا نه"""
        return self.isActive and self.publishedAt is not None


# ========================
# کامنت بلاگ (BlogComment)
# ========================
class BlogComment(models.Model):
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, verbose_name="پست", related_name="comments")
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="نویسنده کامنت", related_name="blog_comments")
    content = models.TextField(verbose_name="محتوای کامنت")

    # پاسخ به کامنت دیگر (اختیاری برای کامنت‌های تو در تو)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, verbose_name="پاسخ به", related_name="replies")

    createdAt = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updatedAt = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    isActive = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "کامنت بلاگ"
        verbose_name_plural = "کامنت‌های بلاگ"
        ordering = ['createdAt']

    def __str__(self):
        return f"کامنت {self.author.username} روی {self.post.title}"

    @property
    def is_reply(self):
        """بررسی اینکه این کامنت پاسخ است یا نه"""
        return self.parent is not None
