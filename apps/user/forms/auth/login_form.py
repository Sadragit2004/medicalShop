from django import forms
import re

class MobileForm(forms.Form):
    mobileNumber = forms.CharField(
        max_length=11,
        min_length=11,
        label="شماره موبایل",
        widget=forms.TextInput(attrs={
            "placeholder": "شماره موبایل خود را وارد کنید",
            "class": "peer w-full rounded-lg border-none bg-transparent p-4 text-left placeholder-transparent focus:outline-none focus:ring-0"
        })
    )

    def clean_mobileNumber(self):
        mobile = self.cleaned_data.get("mobileNumber")

        # فقط اعداد باشه
        if not mobile.isdigit():
            raise forms.ValidationError("شماره موبایل فقط باید شامل اعداد باشد.")

        # دقیقا 11 رقم باشه
        if len(mobile) != 11:
            raise forms.ValidationError("شماره موبایل باید 11 رقم باشد.")

        # شماره ایرانی باشه (با 09 شروع بشه)
        if not re.match(r"^09\d{9}$", mobile):
            raise forms.ValidationError("شماره موبایل معتبر ایرانی نیست.")

        return mobile
