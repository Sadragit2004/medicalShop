from django.db import models
from apps.user.models.user import CustomUser
from apps.product.models import Product
# Create your models here.

# ========================
# علاقه‌مندی‌ها (Favorite/Wishlist)
# ========================

class Favorite(models.Model):
    """
    مدل برای ذخیره علاقه‌مندی‌های کاربران
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="کاربر",
                            related_name='favorites')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="محصول",
                               related_name='favorited_by')
    createdAt = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")

    class Meta:
        verbose_name = "علاقه‌مندی"
        verbose_name_plural = "علاقه‌مندی‌ها"
        unique_together = ['user', 'product']  # جلوگیری از ثبت تکراری
        ordering = ['-createdAt']

    def __str__(self):
        return f"{self.user} → {self.product}"