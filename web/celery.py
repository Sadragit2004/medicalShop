import os
from celery import Celery

# تنظیمات Django رو لود کن (برای دسترسی به settings.py)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web.settings')

app = Celery('web')

# تنظیمات از فایل settings.py با پیشوند CELERY خوونده بشه
app.config_from_object('django.conf:settings', namespace='CELERY')

# بیا و تمام فایل‌های tasks.py رو در اپ‌های Django پیدا کن
app.autodiscover_tasks()

# این تابع رو برای رفع مشکل دسترسی به دیتابیس اضافه می‌کنیم
@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')