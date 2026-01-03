"""Django ATS - Accounts App Configuration"""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = 'アカウント'

    def ready(self):
        """アプリ起動時にシグナルを登録"""
        import apps.accounts.signals  # noqa: F401
