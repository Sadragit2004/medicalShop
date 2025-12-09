from django import forms

class VerificationCodeForm(forms.Form):
    code1 = forms.CharField(
        max_length=1, min_length=1, label='',
        widget=forms.TextInput(attrs={
            'inputmode': 'numeric',
            'class': 'code-input border border-zinc-300 w-10 h-11 rounded-md outline-none text-center focus:outline-0 focus:border-primary-500 focus:shadow-lg',
            'placeholder': ''
        })
    )
    code2 = forms.CharField(max_length=1, min_length=1, label='', widget=forms.TextInput(attrs={'inputmode':'numeric','class':'code-input border border-zinc-300 w-10 h-11 rounded-md outline-none text-center focus:outline-0 focus:border-primary-500 focus:shadow-lg'}))
    code3 = forms.CharField(max_length=1, min_length=1, label='', widget=forms.TextInput(attrs={'inputmode':'numeric','class':'code-input border border-zinc-300 w-10 h-11 rounded-md outline-none text-center focus:outline-0 focus:border-primary-500 focus:shadow-lg'}))
    code4 = forms.CharField(max_length=1, min_length=1, label='', widget=forms.TextInput(attrs={'inputmode':'numeric','class':'code-input border border-zinc-300 w-10 h-11 rounded-md outline-none text-center focus:outline-0 focus:border-primary-500 focus:shadow-lg'}))
    code5 = forms.CharField(max_length=1, min_length=1, label='', widget=forms.TextInput(attrs={'inputmode':'numeric','class':'code-input border border-zinc-300 w-10 h-11 rounded-md outline-none text-center focus:outline-0 focus:border-primary-500 focus:shadow-lg'}))

    def clean(self):
        cleaned_data = super().clean()
        code = ''.join([
            cleaned_data.get('code1', ''),
            cleaned_data.get('code2', ''),
            cleaned_data.get('code3', ''),
            cleaned_data.get('code4', ''),
            cleaned_data.get('code5', ''),
        ])

        if not code.isdigit():
            raise forms.ValidationError("کد تأیید فقط باید شامل اعداد باشد.")

        if len(code) != 5:
            raise forms.ValidationError("کد تأیید باید دقیقا ۵ رقم باشد.")

        cleaned_data['activeCode'] = code
        return cleaned_data
