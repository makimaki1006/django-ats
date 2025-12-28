"""
Django ATS - テスト環境設定
pytest-django用の設定
"""

from .base import *  # noqa: F401, F403

# テスト時はデバッグを有効化
DEBUG = True

# テスト環境ではWhiteNoiseミドルウェアを除外（staticfilesディレクトリ不要）
MIDDLEWARE = [m for m in MIDDLEWARE if 'whitenoise' not in m.lower()]

# テスト用のSECRET_KEY
SECRET_KEY = 'test-secret-key-for-testing-only'

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']

# Database
# テストではSQLite in-memoryを使用
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# パスワードハッシュを高速化（テスト用）
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# メール設定（テスト用）
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# キャッシュ設定（テスト用）
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test-cache',
    }
}

# Celery設定（テストでは同期実行）
CELERY_TASK_ALWAYS_EAGER = True

# ログ設定（テスト用）
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
        'level': 'CRITICAL',
    },
}

# セッション設定（テスト用）
SESSION_COOKIE_SECURE = False

# STATICFILES_STORAGE をテスト用に変更
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
