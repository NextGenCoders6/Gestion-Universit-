"""Configuration Django de l'ERP UCCB.

Toutes les valeurs sensibles ou propres à l'environnement viennent du
fichier .env (voir .env.example), lu par python-decouple.
"""
from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='cle-de-developpement-a-remplacer')  # refusée hors DEBUG (core.E001)
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'core',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
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
        'DIRS': [BASE_DIR / 'templates'],
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

# ── Base de données ──────────────────────────────────────────────
# DB_ENGINE=sqlite : développement rapide et tests ; sinon MySQL.
if config('DB_ENGINE', default='mysql') == 'sqlite':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': config('DB_SQLITE_PATH', default=str(BASE_DIR / 'db.sqlite3')),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': config('DB_NAME', default='uccb_erp'),
            'USER': config('DB_USER', default='root'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='127.0.0.1'),
            'PORT': config('DB_PORT', default='3306'),
            'OPTIONS': {'charset': 'utf8mb4'},
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Brazzaville'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Build de l'interface React (npm run build dans erp/frontend).
FRONTEND_DIST = BASE_DIR / 'frontend_dist'

CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS', default='http://localhost:5173,http://127.0.0.1:5173', cast=Csv()
)

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'core.authentication.AuthentificationJWT',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
        'core.permissions.CompteActif',
    ),
    # Nombre de proxys devant Django (0 : X-Forwarded-For ignoré). Sert à la
    # limitation des connexions et à l'adresse IP du journal d'audit.
    'NUM_PROXIES': config('NUM_PROXIES', default=0, cast=int),
    'DEFAULT_PAGINATION_CLASS': 'core.pagination.PaginationStandard',
    'PAGE_SIZE': 20,
    'EXCEPTION_HANDLER': 'core.exceptions.exception_handler',
    'DATE_FORMAT': '%Y-%m-%d',
    'DATETIME_FORMAT': '%Y-%m-%dT%H:%M:%S',
    'TIME_FORMAT': '%H:%M',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '120/min',
        'user': '1000/min',
        'login': '30/min',
        'login_ip': '60/min',
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
}

# Tests : hachage rapide des mots de passe (jamais utilisé hors des tests).
import sys  # noqa: E402

if len(sys.argv) > 1 and sys.argv[1] == 'test':
    PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
    # Les tests tournent avec DEBUG=False : clé propre aux tests (vérification core.E001).
    if SECRET_KEY == 'cle-de-developpement-a-remplacer':
        SECRET_KEY = 'cle-propre-aux-tests-automatiques'
