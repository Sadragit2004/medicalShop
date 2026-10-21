
from celery import shared_task
import subprocess
import os
from datetime import datetime
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
from django.db import transaction
import logging

from .models import DatabaseBackup

logger = logging.getLogger(__name__)


@shared_task
def backup_database():
    """
    تسک سلری برای گرفتن بکاپ از دیتابیس medical
    """
    backup_record = None
    backup_path = None
    compressed_path = None

    try:
        db_settings = settings.DATABASES['default']
        db_name = db_settings['NAME']
        db_user = db_settings['USER']
        db_password = db_settings['PASSWORD']
        db_host = db_settings['HOST']
        db_port = db_settings['PORT']

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"backup_{db_name}_{timestamp}.sql"

        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)

        backup_path = os.path.join(backup_dir, backup_filename)
        compressed_path = f"{backup_path}.gz"

        backup_record = DatabaseBackup.objects.create(
            filename=os.path.basename(compressed_path),
            file_path=compressed_path,
            file_size=0,
            status=DatabaseBackup.Status.RUNNING,
        )

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

        with open(backup_path, 'w') as f:
            result = subprocess.run(
                dump_cmd,
                stdout=f,
                stderr=subprocess.PIPE,
                text=True
            )

        if result.returncode != 0:
            raise Exception(f"خطا در گرفتن بکاپ: {result.stderr}")

        compressed_path = compress_backup(backup_path)
        os.remove(backup_path)

        file_size = os.path.getsize(compressed_path)

        with transaction.atomic():
            backup_record.filename = os.path.basename(compressed_path)
            backup_record.file_path = compressed_path
            backup_record.file_size = file_size
            backup_record.status = DatabaseBackup.Status.SUCCESS
            backup_record.completed_at = timezone.now()
            backup_record.error_message = ''
            backup_record.save()

        logger.info(f"بکاپ با موفقیت ایجاد شد: {compressed_path}")

        cleanup_old_backups(backup_dir, keep_last=5)

        return {
            'status': 'success',
            'filename': os.path.basename(compressed_path),
            'path': compressed_path,
            'size': file_size
        }

    except Exception as e:
        logger.error(f"خطا در گرفتن بکاپ: {str(e)}")

        if backup_record is not None:
            try:
                backup_record.status = DatabaseBackup.Status.FAILED
                backup_record.error_message = str(e)
                backup_record.completed_at = timezone.now()
                backup_record.save()
            except Exception:
                logger.exception("خطا در ثبت وضعیت ناموفق بکاپ")

        if backup_path and os.path.exists(backup_path):
            try:
                os.remove(backup_path)
            except OSError:
                logger.warning(f"حذف فایل موقت ناموفق بود: {backup_path}")

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

    backup_files.sort(key=os.path.getctime, reverse=True)

    for old_file in backup_files[keep_last:]:
        try:
            os.remove(old_file)

            DatabaseBackup.objects.filter(
                file_path=old_file
            ).delete()

            logger.info(f"بکاپ قدیمی حذف شد: {old_file}")

        except Exception as e:
            logger.warning(f"خطا در حذف فایل {old_file}: {e}")
