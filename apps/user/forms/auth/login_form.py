from django import forms
import re

class MobileForm(forms.Form):
    mobileNumber = forms.CharField(
        max_length=11,
        min_length=11,
        label="شماره موبایل",
        widget=forms.TextInput(attrs={
            "placeholder": "شماره موبایل خود را وارد کنید",
            "class": """block w-full p-3 text-base outline dark:outline-none outline-1 -outline-offset-1 placeholder:text-gray-400  sm:text-sm/6 transition-all
                text-gray-800 dark:text-gray-100 dark:bg-gray-900 bg-slate-100 border border-transparent hover:border-slate-200 appearance-none rounded-md outline-none focus:bg-white focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 dark:focus:ring-blue-400"""
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
