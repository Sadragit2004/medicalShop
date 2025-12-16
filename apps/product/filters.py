import django_filters

class ProductFilter(django_filters.FilterSet):
    price = django_filters.NumberFilter(field_name='price',lookup_expr='lte')


# product_app/filters.py
import django_filters
from .models import Product, Brand

class ProductFilter(django_filters.FilterSet):
    brand = django_filters.ModelMultipleChoiceFilter(
        field_name='brand',
        queryset=Brand.objects.all(),
        widget=django_filters.widgets.CSVWidget
    )

    min_price = django_filters.NumberFilter(
        field_name='saleTypes__price',
        lookup_expr='gte'
    )

    max_price = django_filters.NumberFilter(
        field_name='saleTypes__price',
        lookup_expr='lte'
    )

    class Meta:
        model = Product
        fields = ['brand']