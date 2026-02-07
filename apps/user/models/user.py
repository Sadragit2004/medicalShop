from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser, PermissionsMixin, BaseUserManager
)
import uuid
from datetime import date
from ..validators.mobile_validator import validate_iranian_mobile
from django.utils import timezone

class CustomUserManager(BaseUserManager):

    def create_user(self, mobileNumber, password=None, **extra_fields):
        if not mobileNumber:
            raise ValueError("شماره موبایل الزامی است")

        validate_iranian_mobile(mobileNumber)

        user = self.model(mobileNumber=mobileNumber, **extra_fields)
        user.set_password(password)
        user.is_active = True
        user.save(using=self._db)
        return user

    def create_superuser(self, mobileNumber, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(mobileNumber, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):

    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    mobileNumber = models.CharField(max_length=11, unique=True, validators=[validate_iranian_mobile])
    email = models.EmailField(max_length=100, blank=True, null=True)
    name = models.CharField(max_length=60, blank=True, null=True)
    family = models.CharField(max_length=60, blank=True, null=True)

    GENDER_CHOICES = (("M", "مرد"), ("F", "زن"))
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default="M")

    birth_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    createAt = models.DateTimeField(default=timezone.now,verbose_name='تاریخ ثبت')

    USERNAME_FIELD = "mobileNumber"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.mobileNumber}"

    @property
    def age(self):
        if not self.birth_date:
            return None
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )
