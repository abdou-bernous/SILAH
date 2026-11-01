import sys
import dj_database_url
from pathlib import Path
from decouple import config
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*').split(',')

_INSECURE_SECRET_KEYS = {'django-insecure-change-me-in-production', 'your-secret-key-here'}
if not DEBUG and (SECRET_KEY in _INSECURE_SECRET_KEYS or len(SECRET_KEY) < 32):
    raise RuntimeError(
        'Set a real, unique SECRET_KEY env var (32+ random characters) before running with DEBUG=False. '
        "Generate one with: python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\""
    )

# Tests hash a lot of passwords (registration/login flows); the default hasher is
# deliberately slow, so swap to a fast one only under `manage.py test`.
if 'test' in sys.argv:
    PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'api',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'silah.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'silah.wsgi.application'

# Portable across hosts: a single DATABASE_URL (Railway/Render/Heroku/Fly.io all provide
# one automatically) wins if set; otherwise fall back to the individual DB_* vars for a
# self-managed Postgres; otherwise SQLite, so local dev keeps working with zero setup.
if config('DATABASE_URL', default=''):
    DATABASES = {'default': dj_database_url.config(conn_max_age=600)}
elif config('DB_HOST', default=''):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST'),
            'PORT': config('DB_PORT', default='5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_USER_MODEL = 'api.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'api.permissions.IsActiveMember',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.ScopedRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        # Login is unauthenticated: throttle by IP to slow down password guessing.
        'login': '20/minute',
    },
    'DEFAULT_PAGINATION_CLASS': None,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}

CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS', default='http://localhost:3100'
).split(',')
# Downloads read the file name from this header, which browsers hide cross-origin by default.
CORS_EXPOSE_HEADERS = ['Content-Disposition']
# X-Company: company an accountant / the platform admin is working on.
from corsheaders.defaults import default_headers  # noqa: E402
CORS_ALLOW_HEADERS = [*default_headers, 'x-company']

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
MEDIA_URL = '/media/'
# Uploaded files must outlive the container: in production set MEDIA_ROOT to a
# persistent path (on Azure App Service, anything under /home once
# WEBSITES_ENABLE_APP_SERVICE_STORAGE=true). The default lives inside the app
# directory, which is fine locally but is wiped on every redeploy.
MEDIA_ROOT = Path(config('MEDIA_ROOT', default=str(BASE_DIR / 'media')))

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Algiers'
USE_I18N = True
USE_TZ = True

# Notification emails print to the console in dev; set EMAIL_HOST etc. to send for real.
if config('EMAIL_HOST', default=''):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = config('EMAIL_HOST')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='SILAH <noreply@silah.local>')

# Uploaded payroll documents and receipts: 10 MB max per file.
MAX_UPLOAD_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE

# Security hardening — only enforced when DEBUG=False so local dev is unaffected.
if not DEBUG:
    # Azure/most PaaS hosts terminate TLS at their proxy and forward plain HTTP
    # internally — without this, Django can't tell the request was HTTPS and
    # SECURE_SSL_REDIRECT below would redirect-loop forever.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 7  # 1 week to start; raise once HTTPS is confirmed stable
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
