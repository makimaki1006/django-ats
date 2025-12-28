"""Django ATS - Interviews App Configuration"""

from django.apps import AppConfig


class InterviewsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.interviews'
    verbose_name = '面接'
