"""
Django ATS - 共通設定
全環境で共有される基本設定
"""

import os
from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Environment variables
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
)

# .envファイルを読み込み
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY', default='django-insecure-change-me-in-production')

# Application definition
INSTALLED_APPS = [
    # Django標準
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    # サードパーティ
    'allauth',
    'allauth.account',
    'guardian',
    'django_htmx',
    'crispy_forms',
    'crispy_tailwind',
    'django_filters',

    # プロジェクトアプリ
    'apps.core',
    'apps.accounts',
    'apps.tenants',
    'apps.candidates',
    'apps.applications',
    'apps.jobs',
    'apps.interviews',
    'apps.personas',
    'apps.agents',
    'apps.notifications',
    'apps.reports',
    'apps.settings_app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'apps.core.middleware.TenantMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        },
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'ja'
TIME_ZONE = 'Asia/Tokyo'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'accounts.CustomUser'

# django-allauth settings
SITE_ID = 1
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
    'guardian.backends.ObjectPermissionBackend',
]

# カスタムアダプター（メールのみで認証）
ACCOUNT_ADAPTER = 'apps.accounts.adapters.CustomAccountAdapter'

# allauth設定
ACCOUNT_USER_MODEL_USERNAME_FIELD = None  # usernameフィールドを使用しない
ACCOUNT_USERNAME_REQUIRED = False  # username不要（ACCOUNT_USER_MODEL_USERNAME_FIELD=Noneの場合は必須）
ACCOUNT_AUTHENTICATION_METHOD = 'email'  # メールアドレスで認証
ACCOUNT_EMAIL_REQUIRED = True  # メールアドレス必須
ACCOUNT_EMAIL_VERIFICATION = 'optional'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# django-crispy-forms settings
CRISPY_ALLOWED_TEMPLATE_PACKS = 'tailwind'
CRISPY_TEMPLATE_PACK = 'tailwind'

# django-guardian settings
ANONYMOUS_USER_NAME = None

# Session settings
SESSION_COOKIE_AGE = 86400  # 24時間
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True

# Celery settings
CELERY_BROKER_URL = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024 * 1024 * 5,  # 5MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Default tenant ID (for development/testing)
DEFAULT_TENANT_ID = env('DEFAULT_TENANT_ID', default=None)

# =============================================================================
# Encryption Settings (for EncryptedTextField)
# =============================================================================
# 暗号化キー（Fernet形式、32バイトのbase64エンコード文字列）
# 生成方法: from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())
# 本番環境では必ず環境変数で設定すること
# 開発用デフォルトキー（本番では必ず環境変数で別のキーを設定すること）
ENCRYPTION_KEY = env('ENCRYPTION_KEY', default='uW___Jix7ioKHFWRaP0-YRZ826YsBIr59qOPPs9bEfk=')

# =============================================================================
# Google Sheets Integration Settings
# =============================================================================

# Google Cloud Platform設定
GOOGLE_SHEETS_ENABLED = env.bool('GOOGLE_SHEETS_ENABLED', default=False)

# サービスアカウント認証情報（JSON文字列またはファイルパス）
GOOGLE_CREDENTIALS_JSON = env('GOOGLE_CREDENTIALS_JSON', default='')
GOOGLE_CREDENTIALS_FILE = env('GOOGLE_CREDENTIALS_FILE', default='')

# テンプレートスプレッドシートID（新規顧客用にコピーされる）
GOOGLE_TEMPLATE_SPREADSHEET_ID = env('GOOGLE_TEMPLATE_SPREADSHEET_ID', default='')

# API設定
GOOGLE_SHEETS_CACHE_TTL = env.int('GOOGLE_SHEETS_CACHE_TTL', default=60)  # 秒
GOOGLE_SHEETS_RETRY_COUNT = env.int('GOOGLE_SHEETS_RETRY_COUNT', default=3)
GOOGLE_SHEETS_RETRY_DELAY = env.float('GOOGLE_SHEETS_RETRY_DELAY', default=1.0)  # 秒
