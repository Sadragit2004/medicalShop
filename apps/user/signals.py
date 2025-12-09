# signals.py در همان اپ user
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models.user import CustomUser
from .models.security import UserSecurity

@receiver(post_save, sender=CustomUser)
def create_user_security(sender, instance, created, **kwargs):
    if created:
        UserSecurity.objects.create(user=instance)




@receiver(post_save, sender=CustomUser)
def save_user_security(sender, instance, **kwargs):
    try:
        instance.security.save()
    except UserSecurity.DoesNotExist:
        UserSecurity.objects.create(user=instance)