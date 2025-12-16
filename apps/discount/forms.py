from django import forms



class CopouCode(forms.Form):
    
    coupon_code = forms.CharField(max_length=10,label='',widget=forms.TextInput(attrs={'class':'text-eft peer w-full rounded-lg border-none bg-transparent px-4 py-3 placeholder-transparent focus:outline-none focus:ring-0','placeholder':'کد تخفیف','id':'coupon','style':'color:blue;'}),error_messages={'required':'این فیلد نمیتواند خالی باشد'})