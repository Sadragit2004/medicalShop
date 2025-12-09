from django.db import models
from django.utils import timezone
from ..models.user import CustomUser


class UserDevice(models.Model):

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="devices")
    deviceInfo = models.CharField(max_length=255)
    ipAddress = models.GenericIPAddressField(blank=True, null=True)
    createdAt = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.mobileNumber} - {self.deviceInfo}"
