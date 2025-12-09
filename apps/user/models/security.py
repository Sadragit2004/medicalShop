from django.db import models
from django.utils import timezone
from ..models.user import CustomUser
from ..validators.code_validator import validate_activation_code
from ..validators.common import generate_activation_code, generate_expiration_time


class UserSecurity(models.Model):

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="security")
    activeCode = models.CharField(max_length=16, blank=True, null=True)
    expireCode = models.DateTimeField(blank=True, null=True)
    isBan = models.BooleanField(default=False)
    isInfoFiled = models.BooleanField(default=False)
    createdAt = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Security for {self.user.mobileNumber}"

    def set_activation_code(self):
        self.activeCode = generate_activation_code()
        self.expireCode = generate_expiration_time()
        self.save(update_fields=["activeCode", "expireCode"])

    def validate_code(self, code):
        return validate_activation_code(self, code)
