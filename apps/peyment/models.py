from django.db import models
from apps.user.models.user import CustomUser
from django.utils import timezone
from apps.order.models import Order
import utils
import jdatetime
# Create your models here.

class Peyment(models.Model):

    order = models.ForeignKey(Order,on_delete=models.CASCADE,related_name='peyment_order',verbose_name='سفارش')
    customer = models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name='peyment_customer',verbose_name='مشتری')
    createAt = models.DateTimeField(default=timezone.now, verbose_name="تاریخ ساخته شده")
    updateAt = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")
    amount = models.IntegerField(verbose_name='مبلغ پرداخت')
    description = models.TextField(verbose_name='توضیحات پرداخت')
    isFinaly = models.BooleanField(default=False,verbose_name='وضعیت پرداخت')
    statusCode = models.IntegerField(verbose_name='کد وضعیت پرداخت',null=True,blank=True)
    refId = models.CharField(max_length=50,verbose_name='کد پیگیری پرداخت',null=True,blank=True)


    def get_jalali_register_date(self):
        return jdatetime.datetime.fromgregorian(datetime=self.createAt).strftime('%Y/%m/%d')


    def __str__(self) -> str:
        return f'{self.order}\t\t{self.customer}\t\t{self.refId}'




    class Meta:
        verbose_name = 'پرداخت'
        verbose_name_plural = 'پرداخت ها'

