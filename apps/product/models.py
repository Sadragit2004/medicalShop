from django.db import models
from django.utils.text import slugify
from django.urls import reverse
from apps.user.models.user import CustomUser
from django.db.models import Avg, Count, Q
from django.utils import timezone
from ckeditor_uploader.fields import RichTextUploadingField

# ========================
# مدل پایه (Base Model)
# ========================
class BaseModel(models.Model):
    title = models.CharField(max_length=200, verbose_name="عنوان")
    slug = models.SlugField(max_length=200, unique=True, verbose_name="اسلاگ", allow_unicode=True)
    createdAt = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updatedAt = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    isActive = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


# ========================
# دسته‌بندی (Category)
# ========================
class Category(BaseModel):
    image = models.ImageField(upload_to='category/', verbose_name="تصویر", null=True, blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, verbose_name="دسته‌بندی والد",
                              null=True, blank=True, related_name='children')
    description = RichTextUploadingField(
        verbose_name="توضیحات محصول", config_name="special", blank=True, null=True
    )

    class Meta:
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی‌ها"

    def __str__(self):
        return self.title


# ========================
# ویژگی (Feature)
# ========================
class Feature(BaseModel):
    categories = models.ManyToManyField(Category, verbose_name="دسته‌بندی‌ها",
                                       related_name='features')

    class Meta:
        verbose_name = "ویژگی"
        verbose_name_plural = "ویژگی‌ها"


# ========================
# برند (Brand)
# ========================
class Brand(BaseModel):
    logo = models.ImageField(upload_to='brand/', verbose_name="لوگو", null=True, blank=True)
    description = models.TextField(verbose_name="توضیحات", null=True, blank=True)

    class Meta:
        verbose_name = "برند"
        verbose_name_plural = "برندها"


# ========================
# محصول (Product)
# ========================

class Product(BaseModel):
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, verbose_name="برند",
                             null=True, blank=True, related_name='products')
    category = models.ManyToManyField(Category, verbose_name="دسته‌بندی‌ها",
                                     related_name='products')
    mainImage = models.ImageField(upload_to='products/main/', verbose_name="تصویر اصلی")
    description = RichTextUploadingField(
        verbose_name="توضیحات محصول", config_name="special", blank=True, null=True
    )
    shortDescription = models.TextField(verbose_name="توضیح کوتاه", max_length=500)

    class Meta:
        verbose_name = "محصول"
        verbose_name_plural = "محصولات"
        ordering = ['-createdAt']

    def get_absolute_url(self):
        return reverse("product:product_detail", kwargs={"slug": self.slug})


    @property
    def average_rating(self):
        """میانگین امتیاز محصول"""
        result = Rating.objects.filter(product=self).aggregate(avg=Avg('rating'))
        return round(result['avg'] or 0, 1)

    @property
    def total_comments(self):
        """تعداد کل کامنت‌های محصول"""
        return Comment.objects.filter(product=self, isActive=True).count()

    @property
    def recommendation_stats(self):
        """درصد پیشنهاد کنندگان"""
        comments = Comment.objects.filter(product=self, isActive=True)
        total = comments.count()

        if total == 0:
            return {'recommend': 0, 'not_recommend': 0}

        recommend = comments.filter(typeComment='recommend').count()
        not_recommend = comments.filter(typeComment='not_recommend').count()

        return {
            'recommend': round((recommend / total) * 100, 1),
            'not_recommend': round((not_recommend / total) * 100, 1)
        }

    @property
    def rating_distribution(self):
        """توزیع امتیازها"""
        distribution = {}
        for i in range(1, 6):
            count = Rating.objects.filter(product=self, rating=i).count()
            distribution[f'star_{i}'] = count
        return distribution

    @property
    def total_ratings(self):
        """تعداد کل ریتینگ‌ها"""
        return Rating.objects.filter(product=self).count()

    @property
    def comment_stats(self):
        """تمام آمار کامنت و ریتینگ"""
        return {
            'average_rating': self.average_rating,
            'total_comments': self.total_comments,
            'recommendation': self.recommendation_stats,
            'rating_distribution': self.rating_distribution,
            'total_ratings': self.total_ratings
        }



# ========================
# گالری محصول (ProductGallery)
# ========================
class ProductGallery(models.Model):

    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="محصول",
                               related_name='galleries')
    createdAt = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updatedAt = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    isActive = models.BooleanField(default=True, verbose_name="فعال")
    image = models.ImageField(upload_to='products/gallery/', verbose_name="تصویر")
    altText = models.CharField(max_length=200, verbose_name="متن جایگزین", null=True, blank=True)

    class Meta:
        verbose_name = "گالری محصول"
        verbose_name_plural = "گالری محصولات"
        ordering = ['createdAt']





# ========================
# مقادیر ویژگی (FeatureValue)
# ========================


class FeatureValue(models.Model):
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE, verbose_name="ویژگی",
                               null=True, blank=True, related_name="featureValues")
    value = models.CharField(max_length=100, verbose_name="مقدار")

    class Meta:
        verbose_name = "مقدار ویژگی"
        verbose_name_plural = "مقادیر ویژگی‌ها"

    def __str__(self):
        return f"{self.feature} → {self.value}"


# ========================
# ویژگی محصول (ProductFeature)
# ========================
class ProductFeature(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="محصول",
                               related_name="featuresValue")
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE, verbose_name="ویژگی")
    value = models.CharField(max_length=40, verbose_name="مقدار")
    filterValue = models.ForeignKey(FeatureValue, null=True, blank=True,
                                   on_delete=models.CASCADE, verbose_name="مقدار برای فیلترینگ")

    class Meta:
        verbose_name = "ویژگی محصول"
        verbose_name_plural = "ویژگی‌های محصول"

    def __str__(self):
        return f"{self.product} | {self.feature} = {self.value}"


# ========================
# انواع روش فروش
# ========================
class SaleType:
    SINGLE = 1  # تک فروشی
    CARTON = 2  # کارتن فروشی
    LIMITED = 3  # تک فروشی با محدودیت خرید

    CHOICES = (
        (SINGLE, 'تک فروشی'),
        (CARTON, 'کارتن فروشی'),
        (LIMITED, 'تک فروشی با محدودیت خرید'),
    )


# ========================
# نوع فروش محصول (ProductSaleType)
# ========================
class ProductSaleType(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="محصول",
                               related_name="saleTypes")
    typeSale = models.IntegerField(choices=SaleType.CHOICES, verbose_name="نوع فروش",
                                  default=SaleType.SINGLE)
    price = models.PositiveIntegerField(verbose_name="قیمت")
    memberCarton = models.PositiveIntegerField(verbose_name="تعداد در کارتن", null=True, blank=True)
    limitedSale = models.PositiveIntegerField(verbose_name="محدودیت خرید", null=True, blank=True)
    finalPrice = models.PositiveIntegerField(verbose_name="قیمت نهایی",
                                    null=True, blank=True)
    title = models.CharField(max_length=200, verbose_name="عنوان",blank=True,null=True)
    createdAt = models.DateTimeField(default=timezone.now, verbose_name="تاریخ ایجاد")
    updatedAt = models.DateTimeField(default=timezone.now, verbose_name="تاریخ بروزرسانی")
    isActive = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "نوع فروش محصول"
        verbose_name_plural = "انواع فروش محصولات"

    def save(self, *args, **kwargs):
        """
        محاسبه خودکار finalPrice بر اساس typeSale:
        1. finalPrice همیشه برابر price است (قیمت پایه فروش)
        2. برای فروش کارتن، price قیمت هر کارتن است
        3. برای فروش تک، price قیمت هر عدد است
        """
        self.finalPrice = self.price

        super().save(*args, **kwargs)

    def __str__(self):
        type_name = dict(SaleType.CHOICES).get(self.typeSale, 'نامشخص')
        return f"{self.product} - {type_name}"




class Rating(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="کاربر")
    product = models.ForeignKey('Product', on_delete=models.CASCADE, verbose_name="محصول")
    rating = models.PositiveSmallIntegerField(
        verbose_name="امتیاز",
        choices=[(1, '۱ ستاره'), (2, '۲ ستاره'), (3, '۳ ستاره'), (4, '۴ ستاره'), (5, '۵ ستاره')]
    )
    createdAt = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")

    class Meta:
        verbose_name = "امتیاز"
        verbose_name_plural = "امتیازها"
        unique_together = ['user', 'product']

    def __str__(self):
        return f"{self.user} - {self.product}: {self.rating} ستاره"


# ========================
# کامنت (Comment)
# ========================
class Comment(models.Model):
    COMMENT_TYPES = [
        ('recommend', 'پیشنهاد می‌کنم'),
        ('not_recommend', 'پیشنهاد نمی‌کنم'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="کاربر")
    product = models.ForeignKey('Product', on_delete=models.CASCADE, verbose_name="محصول")
    text = models.TextField(verbose_name="متن کامنت")
    isActive = models.BooleanField(default=True, verbose_name="فعال")
    createdAt = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    typeComment = models.CharField(
        max_length=20,
        choices=COMMENT_TYPES,
        verbose_name="نوع کامنت"
    )

    class Meta:
        verbose_name = "کامنت"
        verbose_name_plural = "کامنت‌ها"
        ordering = ['-createdAt']

    def __str__(self):
        return f"{self.user} - {self.product}"
