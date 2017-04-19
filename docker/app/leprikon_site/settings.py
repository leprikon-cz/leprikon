"""
Django settings for leprikon_site project.

Generated by 'django-admin startproject' using Django 1.9.12.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

import os
from django.utils.translation import ugettext_lazy as _

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAR_DIR = os.path.join(BASE_DIR, 'var')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
try:
    with open(os.path.join(VAR_DIR, 'data', 'secret_key')) as f:
        SECRET_KEY = f.read()
except IOError:
    with open(os.path.join(VAR_DIR, 'data', 'secret_key'), 'w') as f:
        from django.utils.crypto import get_random_string
        SECRET_KEY = get_random_string(50,
            'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)')
        f.write(SECRET_KEY)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', '') and True or False
DBDEBUG = 'DB' in os.environ.get('DEBUG', '').split(',')
DEBUG_TEMPLATE = 'TEMPLATE' in os.environ.get('DEBUG', '').split(',')

ALLOWED_HOSTS = [h.strip() for h in os.environ.get('ALLOWED_HOSTS', '*').split(',')]


# Application definition

INSTALLED_APPS = [
    'leprikon_site',
    'leprikon',
    'djangocms_admin_style',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.sitemaps',
    'cms',
    'menus',
    'sekizai',
    'treebeard',
    'djangocms_text_ckeditor',
    'filer',
    'easy_thumbnails',
    'djangocms_column',
    'djangocms_link',
    'cmsplugin_filer_file',
    'cmsplugin_filer_folder',
    'cmsplugin_filer_image',
    'cmsplugin_filer_utils',
    # leprikon dependecies
    'ganalytics',
    'raven.contrib.django.raven_compat',
    'social_django',
    'verified_email_field',
]

MIDDLEWARE_CLASSES = [
    'raven.contrib.django.raven_compat.middleware.Sentry404CatchMiddleware',
    'cms.middleware.utils.ApphookReloadMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'cms.middleware.user.CurrentUserMiddleware',
    'cms.middleware.page.CurrentPageMiddleware',
    'cms.middleware.toolbar.ToolbarMiddleware',
    'cms.middleware.language.LanguageCookieMiddleware',
    'leprikon.middleware.LeprikonMiddleware',
]

ROOT_URLCONF = 'leprikon_site.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.csrf',
                'django.template.context_processors.tz',
                'django.template.context_processors.static',
                'sekizai.context_processors.sekizai',
                'cms.context_processors.cms_settings',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
            ],
            'loaders': [
                ('django.template.loaders.cached.Loader', [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ]),
            ]
        },
    },
]

if DEBUG_TEMPLATE:
    TEMPLATES[0]['OPTIONS']['debug'] = True
    del TEMPLATES[0]['OPTIONS']['loaders']
    TEMPLATES[0]['APP_DIRS'] = True

WSGI_APPLICATION = 'leprikon_site.wsgi.application'

AUTHENTICATION_BACKENDS = [
    'social_core.backends.facebook.FacebookOAuth2',
    'social_core.backends.google.GooglePlusAuth',
    'verified_email_field.auth.VerifiedEmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DATABASE_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.environ.get('DATABASE_NAME', os.path.join(VAR_DIR, 'data', 'db.sqlite3')),
        'HOST': os.environ.get('DATABASE_HOST', None),
        'PORT': os.environ.get('DATABASE_PORT', None),
        'USER': os.environ.get('DATABASE_USER', None),
        'PASSWORD': os.environ.get('DATABASE_PASSWORD', None),
    }
}


# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGES = (
    ('cs', _('Czech')),
)

LANGUAGE_CODE = LANGUAGES[0][0]

TIME_ZONE = 'Europe/Prague'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/

STATIC_URL = '/static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(VAR_DIR, 'htdocs', 'media')
STATIC_ROOT = os.path.join(VAR_DIR, 'htdocs', 'static')

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/topics/logging/

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'root': {
        'level': 'DEBUG' if DEBUG else 'WARNING',
        'handlers': ['console'] if DEBUG else ['console', 'sentry'],
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s '
                      '%(process)d %(thread)d %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'filters': [],
        },
        'sentry': {
            'level': 'WARNING',
            'filters': ['require_debug_false'],
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
            # supports SENTRY_TAGS env var in form "tag1:value1,tag2:value2"
            'tags': dict(t.split(':', 1) for t in os.environ.get('SENTRY_TAGS', '').split(',') if ':' in t),
        },
    },
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG' if DBDEBUG else 'ERROR',
            'propagate': True,
        },
        'raven': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
        'sentry.errors': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
    },
}

# Caching and session configuration
if os.environ.get('MEMCACHED_LOCATION'):
    CACHES = {
        'default': {
            'BACKEND':    'django.core.cache.backends.memcached.MemcachedCache',
            'LOCATION':   os.environ.get('MEMCACHED_LOCATION'),
            'KEY_PREFIX': os.environ.get('MEMCACHED_KEY_PREFIX'),
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'

# https://docs.sentry.io/clients/python/integrations/django/
RAVEN_CONFIG = {
    'dsn': os.environ.get('SENTRY_DSN'),
}

# CMS configuration
# http://djangocms.readthedocs.io/en/latest/reference/configuration/
SITE_ID = 1

CMS_LANGUAGES = {
    SITE_ID: [{'code': l[0], 'name': l[1]} for l in LANGUAGES],
    'default': {
        'public': True,
        'fallbacks': [LANGUAGE_CODE],
        'hide_untranslated': True,
        'redirect_on_fallback': True,
    },
}

CMS_TEMPLATES = [
    ('leprikon/cms.html', 'Leprikon'),
]

CMS_PERMISSION = True

CMS_PLACEHOLDER_CONF = {}

THUMBNAIL_DEBUG = os.environ.get('DEBUG', False) == 'THUMBNAIL'

THUMBNAIL_PROCESSORS = (
    'easy_thumbnails.processors.colorspace',
    'easy_thumbnails.processors.autocrop',
    'filer.thumbnail_processors.scale_and_crop_with_subject_location',
    'easy_thumbnails.processors.filters',
)

# Google Analytics configuration
GANALYTICS_TRACKING_CODE = os.environ.get('GANALYTICS_TRACKING_CODE')

# Social configuration
SOCIAL_AUTH_FACEBOOK_SCOPE = ['email']
SOCIAL_AUTH_FACEBOOK_KEY = os.environ.get('SOCIAL_AUTH_FACEBOOK_KEY')
SOCIAL_AUTH_FACEBOOK_SECRET = os.environ.get('SOCIAL_AUTH_FACEBOOK_SECRET')

SOCIAL_AUTH_GOOGLE_PLUS_SCOPE = ['profile', 'email']
SOCIAL_AUTH_GOOGLE_PLUS_KEY = os.environ.get('SOCIAL_AUTH_GOOGLE_PLUS_KEY')
SOCIAL_AUTH_GOOGLE_PLUS_SECRET = os.environ.get('SOCIAL_AUTH_GOOGLE_PLUS_SECRET')

# Leprikon configuration
PRICE_DECIMAL_PLACES = 0
COUNTRIES_FIRST = ['CZ', 'SK']