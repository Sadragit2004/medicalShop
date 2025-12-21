from django.contrib import admin
from .models import Peyment

# Register your models here.
@admin.register(Peyment)

class Peyment_admin(admin.ModelAdmin):
    
    list_display = ('customer','get_jalali_register_date','amount','isFinaly','statusCode','refId',)

    ordering = ('isFinaly',)
    search_fields = ('refId','customer','get_jalali_register_date',)



