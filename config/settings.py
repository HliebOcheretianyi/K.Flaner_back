from datetime import timedelta
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    CORS_ALLOWED_ORIGINS=(list, []),
)
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env('ALLOWED_HOSTS')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'kflaner',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db.sqlite3"}'),
}

AUTH_USER_MODEL = 'kflaner.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'uk'
TIME_ZONE = 'Europe/Kyiv'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

MAILERS = {
    'default': {
        'BACKEND': env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend'),
    },
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'kflaner.utils.authentication.BearerTokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_PARSER_CLASSES': ['rest_framework.parsers.JSONParser'],
    'EXCEPTION_HANDLER': 'kflaner.utils.error_handling.handle_exception',
    'DEFAULT_THROTTLE_RATES': {
        'auth': env('AUTH_THROTTLE_RATE', default='10/min'),
    },
}

JWT_SECRET = env('JWT_SECRET')
if len(JWT_SECRET.encode()) < 32:
    raise ImproperlyConfigured('JWT_SECRET must be at least 32 bytes (payment-manager requirement).')
JWT_ISSUER = env('JWT_ISSUER', default='')
JWT_AUDIENCE = env('JWT_AUDIENCE', default='')
ACCESS_TOKEN_LIFETIME = timedelta(minutes=env.int('ACCESS_TOKEN_LIFETIME_MINUTES', default=15))
REFRESH_TOKEN_LIFETIME = timedelta(days=env.int('REFRESH_TOKEN_LIFETIME_DAYS', default=30))

CORS_ALLOWED_ORIGINS = env('CORS_ALLOWED_ORIGINS')

PAYMENT_MANAGER_URL = env('PAYMENT_MANAGER_URL', default='http://localhost:8080')
PAYMENT_MANAGER_TIMEOUT_SECONDS = env.float('PAYMENT_MANAGER_TIMEOUT_SECONDS', default=10.0)
PAYMENT_MANAGER_SERVICE_TOKEN = env('PAYMENT_MANAGER_SERVICE_TOKEN')
if len(PAYMENT_MANAGER_SERVICE_TOKEN.encode()) < 32:
    raise ImproperlyConfigured('PAYMENT_MANAGER_SERVICE_TOKEN must be at least 32 bytes (payment-manager requirement).')

KAFKA_BROKERS = env.list('KAFKA_BROKERS', default=['localhost:9094'])
KAFKA_PAYMENT_STATUS_TOPIC = env('KAFKA_PAYMENT_STATUS_TOPIC', default='payment.status-changed')
KAFKA_CONSUMER_GROUP = env('KAFKA_CONSUMER_GROUP', default='kflaner-back')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'loggers': {'kflaner': {'handlers': ['console'], 'level': env('LOG_LEVEL', default='INFO')}},
}
