from django.db import models
from .base import BaseModel

class AttributeGroup(BaseModel):
    """
    گروه‌های ویژگی (مثلاً: مشخصات فنی، مشخصات ظاهری، ابعاد و وزن)
    """
    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name="ترتیب نمایش"
    )

    class Meta:
        verbose_name = "گروه ویژگی"
        verbose_name_plural = "گروه‌های ویژگی"
        ordering = ['sort_order', 'title']

class Attribute(BaseModel):
    """
    ویژگی‌های محصول - کاملاً داینامیک
    """
    group = models.ForeignKey(
        AttributeGroup,
        on_delete=models.CASCADE,
        related_name='attributes',
        verbose_name="گروه ویژگی",
        null=True,
        blank=True
    )

    # نوع داده‌ای ویژگی
    DATA_TYPE_CHOICES = [
        ('text', 'متن'),
        ('integer', 'عدد صحیح'),
        ('decimal', 'عدد اعشاری'),
        ('boolean', 'صحیح/غلط'),
        ('date', 'تاریخ'),
        ('datetime', 'تاریخ و زمان'),
        ('select', 'انتخاب از لیست'),
        ('multi_select', 'انتخاب چندتایی'),
        ('color', 'رنگ'),
    ]

    data_type = models.CharField(
        max_length=20,
        choices=DATA_TYPE_CHOICES,
        default='text',
        verbose_name="نوع داده"
    )

    # برای نوع select و multi_select
    options = models.TextField(
        blank=True,
        verbose_name="گزینه‌ها (هر خط یک گزینه)"
    )

    # برای نوع عددی
    min_value = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="حداقل مقدار"
    )
    max_value = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="حداکثر مقدار"
    )

    # برای نوع متن
    max_length = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="حداکثر طول متن"
    )

    # تنظیمات نمایش
    unit = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="واحد اندازه‌گیری"
    )
    is_required = models.BooleanField(
        default=False,
        verbose_name="اجباری"
    )
    is_filterable = models.BooleanField(
        default=False,
        verbose_name="قابل فیلتر در سایت"
    )
    is_visible = models.BooleanField(
        default=True,
        verbose_name="نمایش در صفحه محصول"
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name="ترتیب نمایش"
    )

    # برای ساختار سلسله‌مراتبی
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name="ویژگی والد"
    )

    class Meta:
        verbose_name = "ویژگی محصول"
        verbose_name_plural = "ویژگی‌های محصولات"
        ordering = ['group__sort_order', 'sort_order', 'title']

    def get_options_list(self):
        """
        تبدیل گزینه‌های متنی به لیست
        """
        if self.options:
            return [line.strip() for line in self.options.split('\n') if line.strip()]
        return []

    def clean(self):
        """
        اعتبارسنجی بر اساس نوع داده
        """
        from django.core.exceptions import ValidationError

        if self.data_type in ['integer', 'decimal']:
            if self.min_value and self.max_value and self.min_value > self.max_value:
                raise ValidationError("حداقل مقدار باید کوچکتر از حداکثر مقدار باشد")

    def validate_value(self, value):
        """
        اعتبارسنجی مقدار بر اساس نوع داده
        """
        if self.data_type == 'text':
            if self.max_length and len(value) > self.max_length:
                raise ValueError(f"متن نباید بیشتر از {self.max_length} کاراکتر باشد")

        elif self.data_type in ['integer', 'decimal']:
            if self.min_value and value < self.min_value:
                raise ValueError(f"مقدار نباید کمتر از {self.min_value} باشد")
            if self.max_value and value > self.max_value:
                raise ValueError(f"مقدار نباید بیشتر از {self.max_value} باشد")

        elif self.data_type == 'select':
            options = self.get_options_list()
            if value not in options:
                raise ValueError(f"مقدار باید یکی از این گزینه‌ها باشد: {', '.join(options)}")

        elif self.data_type == 'multi_select':
            if not isinstance(value, list):
                raise ValueError("مقدار باید یک لیست باشد")
            options = self.get_options_list()
            for item in value:
                if item not in options:
                    raise ValueError(f"گزینه '{item}' در لیست معتبر نیست")

class ProductAttributeValue(models.Model):
    """
    مقادیر ویژگی‌های محصول
    """
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='attribute_values',
        verbose_name="محصول"
    )
    attribute = models.ForeignKey(
        Attribute,
        on_delete=models.CASCADE,
        related_name='product_values',
        verbose_name="ویژگی"
    )

    # مقادیر بر اساس نوع داده
    value_text = models.TextField(null=True, blank=True, verbose_name="مقدار متنی")
    value_integer = models.IntegerField(null=True, blank=True, verbose_name="مقدار عددی")
    value_decimal = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="مقدار اعشاری"
    )
    value_boolean = models.BooleanField(null=True, blank=True, verbose_name="مقدار منطقی")
    value_date = models.DateField(null=True, blank=True, verbose_name="مقدار تاریخ")
    value_datetime = models.DateTimeField(null=True, blank=True, verbose_name="مقدار تاریخ و زمان")

    # برای مقادیر select
    value_select = models.CharField(max_length=255, null=True, blank=True, verbose_name="مقدار انتخابی")

    # برای مقادیر multi_select (ذخیره به صورت JSON)
    value_multi_select = models.JSONField(null=True, blank=True, verbose_name="مقادیر انتخابی چندتایی")

    # برای مقادیر color
    value_color = models.CharField(max_length=50, null=True, blank=True, verbose_name="مقدار رنگ")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "مقدار ویژگی محصول"
        verbose_name_plural = "مقادیر ویژگی‌های محصولات"
        unique_together = ['product', 'attribute']

    def get_value(self):
        """
        دریافت مقدار بر اساس نوع داده
        """
        if self.attribute.data_type == 'text':
            return self.value_text
        elif self.attribute.data_type == 'integer':
            return self.value_integer
        elif self.attribute.data_type == 'decimal':
            return self.value_decimal
        elif self.attribute.data_type == 'boolean':
            return self.value_boolean
        elif self.attribute.data_type == 'date':
            return self.value_date
        elif self.attribute.data_type == 'datetime':
            return self.value_datetime
        elif self.attribute.data_type == 'select':
            return self.value_select
        elif self.attribute.data_type == 'multi_select':
            return self.value_multi_select or []
        elif self.attribute.data_type == 'color':
            return self.value_color
        return None

    def set_value(self, value):
        """
        تنظیم مقدار بر اساس نوع داده
        """
        # پاک کردن مقادیر قبلی
        self.value_text = None
        self.value_integer = None
        self.value_decimal = None
        self.value_boolean = None
        self.value_date = None
        self.value_datetime = None
        self.value_select = None
        self.value_multi_select = None
        self.value_color = None

        # تنظیم مقدار جدید
        if self.attribute.data_type == 'text':
            self.attribute.validate_value(value)
            self.value_text = value

        elif self.attribute.data_type == 'integer':
            self.attribute.validate_value(value)
            self.value_integer = int(value)

        elif self.attribute.data_type == 'decimal':
            self.attribute.validate_value(value)
            self.value_decimal = value

        elif self.attribute.data_type == 'boolean':
            self.value_boolean = bool(value)

        elif self.attribute.data_type == 'date':
            self.value_date = value

        elif self.attribute.data_type == 'datetime':
            self.value_datetime = value

        elif self.attribute.data_type == 'select':
            self.attribute.validate_value(value)
            self.value_select = value

        elif self.attribute.data_type == 'multi_select':
            self.attribute.validate_value(value)
            self.value_multi_select = value

        elif self.attribute.data_type == 'color':
            self.value_color = value

    def __str__(self):
        return f"{self.attribute.title}: {self.get_value()}"