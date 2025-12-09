from django import forms
from ..models.attribute import Attribute, AttributeGroup

class AttributeForm(forms.ModelForm):
    class Meta:
        model = Attribute
        fields = [
            'title',
            'group',
            'data_type',
            'options',
            'min_value',
            'max_value',
            'max_length',
            'unit',
            'is_required',
            'is_filterable',
            'is_visible',
            'sort_order',
            'parent',
        ]

        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'group': forms.Select(attrs={'class': 'form-control'}),
            'data_type': forms.Select(attrs={'class': 'form-control'}),
            'options': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'هر گزینه در یک خط جداگانه'
            }),
            'min_value': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_value': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_length': forms.NumberInput(attrs={'class': 'form-control'}),
            'unit': forms.TextInput(attrs={'class': 'form-control'}),
            'is_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_filterable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_visible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control'}),
            'parent': forms.Select(attrs={'class': 'form-control'}),
        }

        labels = {
            'title': 'عنوان ویژگی',
            'group': 'گروه ویژگی',
            'data_type': 'نوع داده',
            'options': 'گزینه‌ها',
            'min_value': 'حداقل مقدار',
            'max_value': 'حداکثر مقدار',
            'max_length': 'حداکثر طول متن',
            'unit': 'واحد اندازه‌گیری',
            'is_required': 'اجباری',
            'is_filterable': 'قابل فیلتر',
            'is_visible': 'قابل نمایش',
            'sort_order': 'ترتیب نمایش',
            'parent': 'ویژگی والد',
        }

class AttributeGroupForm(forms.ModelForm):
    class Meta:
        model = AttributeGroup
        fields = ['title', 'sort_order']

        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control'}),
        }

        labels = {
            'title': 'عنوان گروه',
            'sort_order': 'ترتیب نمایش',
        }

class DynamicProductAttributeForm(forms.Form):
    """
    فرم داینامیک برای ویژگی‌های محصول
    """
    def __init__(self, *args, **kwargs):
        self.product = kwargs.pop('product', None)
        self.attribute_service = kwargs.pop('attribute_service', None)
        super().__init__(*args, **kwargs)

        if self.product and self.attribute_service:
            self._build_dynamic_fields()

    def _build_dynamic_fields(self):
        """
        ساخت فیلدهای داینامیک بر اساس ویژگی‌های تعریف شده
        """
        form_data = self.attribute_service.get_attribute_form_data(self.product.id)

        for field_config in form_data:
            field_name = f'attribute_{field_config["id"]}'
            field_label = field_config['title']

            if field_config['data_type'] == 'text':
                if field_config.get('field_type') == 'textarea':
                    self.fields[field_name] = forms.CharField(
                        label=field_label,
                        required=field_config['is_required'],
                        widget=forms.Textarea(attrs={
                            'class': 'form-control',
                            'rows': 3,
                            'maxlength': field_config.get('max_length')
                        }),
                        initial=field_config['current_value'],
                        help_text=field_config['help_text']
                    )
                else:
                    self.fields[field_name] = forms.CharField(
                        label=field_label,
                        required=field_config['is_required'],
                        widget=forms.TextInput(attrs={
                            'class': 'form-control',
                            'maxlength': field_config.get('max_length')
                        }),
                        initial=field_config['current_value'],
                        help_text=field_config['help_text']
                    )

            elif field_config['data_type'] in ['integer', 'decimal']:
                self.fields[field_name] = forms.DecimalField(
                    label=field_label,
                    required=field_config['is_required'],
                    widget=forms.NumberInput(attrs={
                        'class': 'form-control',
                        'min': field_config.get('min_value'),
                        'max': field_config.get('max_value'),
                        'step': field_config.get('step', '0.01')
                    }),
                    initial=field_config['current_value'],
                    help_text=field_config['help_text']
                )

            elif field_config['data_type'] == 'boolean':
                self.fields[field_name] = forms.BooleanField(
                    label=field_label,
                    required=field_config['is_required'],
                    widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
                    initial=field_config['current_value'] or False,
                    help_text=field_config['help_text']
                )

            elif field_config['data_type'] == 'date':
                self.fields[field_name] = forms.DateField(
                    label=field_label,
                    required=field_config['is_required'],
                    widget=forms.DateInput(attrs={
                        'class': 'form-control',
                        'type': 'date'
                    }),
                    initial=field_config['current_value'],
                    help_text=field_config['help_text']
                )

            elif field_config['data_type'] == 'datetime':
                self.fields[field_name] = forms.DateTimeField(
                    label=field_label,
                    required=field_config['is_required'],
                    widget=forms.DateTimeInput(attrs={
                        'class': 'form-control',
                        'type': 'datetime-local'
                    }),
                    initial=field_config['current_value'],
                    help_text=field_config['help_text']
                )

            elif field_config['data_type'] == 'select':
                choices = [(opt, opt) for opt in field_config['options']]
                self.fields[field_name] = forms.ChoiceField(
                    label=field_label,
                    required=field_config['is_required'],
                    choices=choices,
                    widget=forms.Select(attrs={'class': 'form-control'}),
                    initial=field_config['current_value'],
                    help_text=field_config['help_text']
                )

            elif field_config['data_type'] == 'multi_select':
                choices = [(opt, opt) for opt in field_config['options']]
                self.fields[field_name] = forms.MultipleChoiceField(
                    label=field_label,
                    required=field_config['is_required'],
                    choices=choices,
                    widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
                    initial=field_config['current_value'] or [],
                    help_text=field_config['help_text']
                )

            elif field_config['data_type'] == 'color':
                self.fields[field_name] = forms.CharField(
                    label=field_label,
                    required=field_config['is_required'],
                    widget=forms.TextInput(attrs={
                        'class': 'form-control',
                        'type': 'color'
                    }),
                    initial=field_config['current_value'] or '#000000',
                    help_text=field_config['help_text']
                )

    def save_attributes(self):
        """
        ذخیره مقادیر ویژگی‌ها
        """
        if not self.product or not self.attribute_service:
            return False

        attribute_values = {}
        for field_name, value in self.cleaned_data.items():
            if field_name.startswith('attribute_'):
                attribute_id = int(field_name.split('_')[1])
                attribute_values[attribute_id] = value

        return self.attribute_service.save_product_attributes(
            self.product.id,
            attribute_values
        )