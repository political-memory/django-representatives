import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = 'notsecret'

ROOT_URLCONF = 'representatives.tests.urls'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.environ.get('DB_NAME', 'representatives'),
    }
}

if 'DB_USER' in os.environ.keys():
    DATABASES['default']['USER'] = os.environ.get('DB_USER')

INSTALLED_APPS = (
    'django.contrib.staticfiles',
    'dbdiff',
    'rest_framework',
    'representatives',
)

STATIC_URL = '/static/'
DEBUG = True
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'

USE_I18N = False
USE_L10N = False
USE_TZ = False

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(levelname)s[%(module)s]: %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO'
        },
        'representatives': {
            'handlers': ['console'],
            'level': 'INFO'
        },
    },
}
