from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from ..services.implementations.attribute_service import AttributeService
from ..forms.attribute_form import AttributeForm, AttributeGroupForm, DynamicProductAttributeForm

class AttributeListView(LoginRequiredMixin, View):
    """
    لیست ویژگی‌ها
    """
    template_name = 'product/attribute_list.html'

    def __init__(self):
        self.attribute_service = AttributeService()

    def get(self, request):
        page = request.GET.get('page', 1)

        # دریافت ویژگی‌ها گروه‌بندی شده
        attributes_by_group = self.attribute_service.get_attributes_by_group()

        context = {
            'attributes_by_group': attributes_by_group,
        }

        return render(request, self.template_name, context)

class AttributeCreateView(LoginRequiredMixin, View):
    """
    ایجاد ویژگی جدید
    """
    template_name = 'product/attribute_form.html'

    def get(self, request):
        form = AttributeForm()
        context = {
            'form': form,
            'title': 'ایجاد ویژگی جدید',
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = AttributeForm(request.POST)

        if form.is_valid():
            try:
                attribute = form.save()
                messages.success(request, "ویژگی با موفقیت ایجاد شد")
                return redirect('product:attribute_list')
            except Exception as e:
                messages.error(request, str(e))

        context = {
            'form': form,
            'title': 'ایجاد ویژگی جدید',
        }
        return render(request, self.template_name, context)

class ProductAttributesView(LoginRequiredMixin, View):
    """
    مدیریت ویژگی‌های یک محصول
    """
    template_name = 'product/product_attributes.html'

    def __init__(self):
        self.attribute_service = AttributeService()
        from ..services.implementations.product_service import ProductService
        self.product_service = ProductService()

    def get(self, request, product_id):
        product = self.product_service.get_product_by_id(product_id)

        if not product:
            messages.error(request, "محصول یافت نشد")
            return redirect('product:list')

        # ساخت فرم داینامیک
        form = DynamicProductAttributeForm(
            product=product,
            attribute_service=self.attribute_service
        )

        context = {
            'product': product,
            'form': form,
            'title': f'مدیریت ویژگی‌های {product.title}',
        }

        return render(request, self.template_name, context)

    def post(self, request, product_id):
        product = self.product_service.get_product_by_id(product_id)

        if not product:
            messages.error(request, "محصول یافت نشد")
            return redirect('product:list')

        # ساخت فرم داینامیک
        form = DynamicProductAttributeForm(
            request.POST,
            product=product,
            attribute_service=self.attribute_service
        )

        if form.is_valid():
            try:
                if form.save_attributes():
                    messages.success(request, "ویژگی‌های محصول با موفقیت ذخیره شدند")
                else:
                    messages.error(request, "خطا در ذخیره ویژگی‌ها")
            except Exception as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "لطفاً خطاهای فرم را برطرف کنید")

        context = {
            'product': product,
            'form': form,
            'title': f'مدیریت ویژگی‌های {product.title}',
        }

        return render(request, self.template_name, context)