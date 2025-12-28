"""
Django ATS - 開発環境設定
"""

from .base import *  # noqa: F401, F403

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# Database
# 開発環境ではSQLiteを使用
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# 開発用のメール設定（コンソールに出力）
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# django-debug-toolbar（オプション）
try:
    import debug_toolbar  # noqa: F401
    INSTALLED_APPS += ['debug_toolbar']  # noqa: F405
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')  # noqa: F405
except ImportError:
    pass

INTERNAL_IPS = [
    '127.0.0.1',
]

# CORS設定（開発環境用）
CORS_ALLOW_ALL_ORIGINS = True

# CSRFの信頼ホスト
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# セッション設定（開発環境用）
SESSION_COOKIE_SECURE = False

# ログレベルを詳細に
LOGGING['loggers']['apps']['level'] = 'DEBUG'  # noqa: F405
LOGGING['loggers']['django']['level'] = 'DEBUG'  # noqa: F405

# キャッシュ設定（開発環境ではローカルメモリ）
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Celery設定（開発環境では同期実行も可）
CELERY_TASK_ALWAYS_EAGER = env.bool('CELERY_TASK_ALWAYS_EAGER', default=True)  # noqa: F405

# ログディレクトリの作成
import os
os.makedirs(BASE_DIR / 'logs', exist_ok=True)  # noqa: F405
