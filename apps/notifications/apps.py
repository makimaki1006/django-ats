"""Django ATS - Notifications App Configuration"""

from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notifications'
    verbose_name = '通知'

    def ready(self):
        # シグナルをインポート
        try:
            from . import signals  # noqa: F401
        except ImportError:
            pass
