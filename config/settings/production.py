"""
Django ATS - 本番環境設定
"""

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

from .base import *  # noqa: F401, F403

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# 本番環境では環境変数から取得
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')  # noqa: F405

# Database
# 本番環境ではPostgreSQLを使用
DATABASES = {
    'default': env.db('DATABASE_URL')  # noqa: F405
}

# セキュリティ設定
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HSTS設定 (1年間)
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# CSRFの信頼ホスト
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])  # noqa: F405

# メール設定（本番環境）
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')  # noqa: F405
EMAIL_PORT = env.int('EMAIL_PORT', default=587)  # noqa: F405
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')  # noqa: F405
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')  # noqa: F405
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@example.com')  # noqa: F405

# キャッシュ設定（本番環境ではRedis）
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': env('REDIS_URL', default='redis://localhost:6379/1'),  # noqa: F405
    }
}

# Sentry設定
SENTRY_DSN = env('SENTRY_DSN', default='')  # noqa: F405
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
        ],
        # パフォーマンストレーシング
        traces_sample_rate=0.1,
        # プロファイリング
        profiles_sample_rate=0.1,
        # 環境名
        environment='production',
        # リリースバージョン
        release=env('APP_VERSION', default='1.0.0'),  # noqa: F405
        # PIIを送信しない
        send_default_pii=False,
    )

# ログ設定（本番環境）
LOGGING['handlers']['file']['filename'] = '/var/log/django_ats/django.log'  # noqa: F405
LOGGING['handlers']['sentry'] = {  # noqa: F405
    'level': 'ERROR',
    'class': 'sentry_sdk.integrations.logging.EventHandler',
}
LOGGING['loggers']['django']['handlers'].append('sentry')  # noqa: F405
LOGGING['loggers']['apps']['handlers'].append('sentry')  # noqa: F405

# 静的ファイル設定
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Celery設定（本番環境では非同期実行）
CELERY_TASK_ALWAYS_EAGER = False
