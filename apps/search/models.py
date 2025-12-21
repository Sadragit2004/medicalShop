from django.db import models

# در فایل models.py (پایین فایل)
class PopularSearch(models.Model):
    """مدل برای جستجوهای پرطرفدار"""
    keyword = models.CharField(max_length=100, verbose_name="کلیدواژه", unique=True)
    search_count = models.PositiveIntegerField(default=1, verbose_name="تعداد جستجو")
    click_count = models.PositiveIntegerField(default=0, verbose_name="تعداد کلیک")
    last_searched = models.DateTimeField(auto_now=True, verbose_name="آخرین جستجو")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")

    class Meta:
        verbose_name = "جستجوی پرطرفدار"
        verbose_name_plural = "جستجوهای پرطرفدار"
        ordering = ['-search_count', '-last_searched']

    def __str__(self):
        return f"{self.keyword} ({self.search_count} جستجو)"

    def increment_search(self):
        """افزایش تعداد جستجو"""
        self.search_count += 1
        self.save()

    def increment_click(self):
        """افزایش تعداد کلیک"""
        self.click_count += 1
        self.save()