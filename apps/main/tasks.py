# your_app/tasks.py
from celery import shared_task
import subprocess
import os
from datetime import datetime
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import logging

logger = logging.getLogger(__name__)

@shared_task
def backup_database():
    """
    تسک سلری برای گرفتن بکاپ از دیتابیس medical
    """
    try:
        # تنظیمات دیتابیس
        db_settings = settings.DATABASES['default']
        db_name = db_settings['NAME']
        db_user = db_settings['USER']
        db_password = db_settings['PASSWORD']
        db_host = db_settings['HOST']
        db_port = db_settings['PORT']

        # ایجاد نام فایل با تاریخ و زمان
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"backup_{db_name}_{timestamp}.sql"

        # مسیر ذخیره فایل (می‌توانید تغییر دهید)
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)

        backup_path = os.path.join(backup_dir, backup_filename)

        # دستور mysql dump
        dump_cmd = [
            'mysqldump',
            f'--host={db_host}',
            f'--port={db_port}',
            f'--user={db_user}',
            f'--password={db_password}',
            '--single-transaction',
            '--routines',
            '--triggers',
            '--add-drop-database',
            '--databases',
            db_name
        ]

        # اجرای دستور
        with open(backup_path, 'w') as f:
            result = subprocess.run(
                dump_cmd,
                stdout=f,
                stderr=subprocess.PIPE,
                text=True
            )

        if result.returncode != 0:
            raise Exception(f"خطا در گرفتن بکاپ: {result.stderr}")

        # فشرده‌سازی فایل
        compressed_path = compress_backup(backup_path)

        # حذف فایل غیرفشرده
        os.remove(backup_path)

        # ثبت در لاگ
        logger.info(f"بکاپ با موفقیت ایجاد شد: {compressed_path}")

        # (اختیاری) آپلود در فضای ابری یا ارسال ایمیل
        # upload_to_cloud(compressed_path)
        # send_backup_email(compressed_path)

        # حذف بکاپ‌های قدیمی (اختیاری)
        cleanup_old_backups(backup_dir, keep_last=5)

        return {
            'status': 'success',
            'filename': backup_filename,
            'path': compressed_path,
            'size': os.path.getsize(compressed_path)
        }

    except Exception as e:
        logger.error(f"خطا در گرفتن بکاپ: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }


def compress_backup(file_path):
    """
    فشرده‌سازی فایل بکاپ
    """
    import gzip
    import shutil

    compressed_path = f"{file_path}.gz"

    with open(file_path, 'rb') as f_in:
        with gzip.open(compressed_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

    return compressed_path


def cleanup_old_backups(backup_dir, keep_last=5):
    """
    حذف بکاپ‌های قدیمی
    """
    import glob

    backup_files = glob.glob(os.path.join(backup_dir, "*.sql.gz"))

    # مرتب‌سازی بر اساس زمان ایجاد
    backup_files.sort(key=os.path.getctime)

    # حذف فایل‌های اضافی
    for old_file in backup_files[:-keep_last]:
        try:
            os.remove(old_file)
            logger.info(f"بکاپ قدیمی حذف شد: {old_file}")
        except Exception as e:
            logger.warning(f"خطا در حذف فایل {old_file}: {e}")