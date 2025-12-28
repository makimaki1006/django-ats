"""Django ATS - Settings App Configuration"""

from django.apps import AppConfig


class SettingsAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.settings_app'
    verbose_name = '設定'
