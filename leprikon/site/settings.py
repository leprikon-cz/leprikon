"""
Django settings for leprikon.site project.

Generated by 'django-admin startproject' using Django 1.11.13.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.11/ref/settings/
"""

import os

from django.utils.translation import ugettext_lazy as _

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.environ.get('BASE_DIR', os.getcwd())
DATA_DIR = os.environ.get('DATA_DIR', os.path.join(BASE_DIR, 'data'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', os.environ.get('DEBUG'))
if not SECRET_KEY:
    from django.utils.crypto import get_random_string
    SECRET_KEY = get_random_string(
        50,
        'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)',
    )

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', '') and True or False
DBDEBUG = 'DB' in os.environ.get('DEBUG', '').split(',')
DEBUG_TEMPLATE = 'TEMPLATE' in os.environ.get('DEBUG', '').split(',')
DEBUG_LML = 'LML' in os.environ.get('DEBUG', '').split(',')

ALLOWED_HOSTS = [h.strip() for h in os.environ.get('ALLOWED_HOSTS', '*').split(',')]


# Application definition

INSTALLED_APPS = [
    'leprikon.site',
    'leprikon',
    'bankreader',
    'djangocms_admin_style',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.sitemaps',
    'django_pays',
    'cms',
    'haystack',
    'menus',
    'multiselectfield',
    'sekizai',
    'template_admin',
    'treebeard',
    'filer',
    'easy_thumbnails',
    'cmsplugin_filer_file',
    'cmsplugin_filer_folder',
    'cmsplugin_filer_image',
    'cmsplugin_filer_link',
    'cmsplugin_filer_teaser',
    'cmsplugin_filer_utils',
    'cmsplugin_filer_video',
    'djangocms_link',
    'djangocms_text_ckeditor',
    'ganalytics',
    'html2rml',
    'qr_code',
    'social_django',
    'verified_email_field',
]

MIDDLEWARE = [
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
    'social_django.middleware.SocialAuthExceptionMiddleware',
    'leprikon.middleware.LeprikonMiddleware',
]

ROOT_URLCONF = os.environ.get('ROOT_URLCONF', 'leprikon.site.urls')

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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
            'debug': DEBUG_TEMPLATE,
            'loaders': [
                ('template_admin.loader.Loader', [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ]),
            ] if DEBUG_TEMPLATE else [
                ('template_admin.loader.Loader', [
                    ('django.template.loaders.cached.Loader', [
                        'django.template.loaders.filesystem.Loader',
                        'django.template.loaders.app_directories.Loader',
                    ]),
                ]),
            ]
        },
    },
]

WSGI_APPLICATION = os.environ.get('UWSGI_MODULE', 'leprikon.site.wsgi:application').replace(':', '.')

# Social configuration
SOCIAL_AUTH_FACEBOOK_SCOPE = ['email']
SOCIAL_AUTH_FACEBOOK_PROFILE_EXTRA_PARAMS = {'fields': 'id,name,email'}
SOCIAL_AUTH_FACEBOOK_KEY = os.environ.get('SOCIAL_AUTH_FACEBOOK_KEY')
SOCIAL_AUTH_FACEBOOK_SECRET = os.environ.get('SOCIAL_AUTH_FACEBOOK_SECRET')

SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = ['profile', 'email']
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get('SOCIAL_AUTH_GOOGLE_OAUTH2_KEY')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get('SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET')

SOCIAL_AUTH_GOOGLE_PLUS_SCOPE = ['profile', 'email']
SOCIAL_AUTH_GOOGLE_PLUS_KEY = os.environ.get('SOCIAL_AUTH_GOOGLE_PLUS_KEY')
SOCIAL_AUTH_GOOGLE_PLUS_SECRET = os.environ.get('SOCIAL_AUTH_GOOGLE_PLUS_SECRET')

SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.social_auth.associate_by_email',
    'social_core.pipeline.user.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
)

# Authentication configuration
AUTHENTICATION_BACKENDS = (
    ['social_core.backends.facebook.FacebookOAuth2'] if SOCIAL_AUTH_FACEBOOK_KEY else []
) + (
    ['social_core.backends.google.GoogleOAuth2'] if SOCIAL_AUTH_GOOGLE_OAUTH2_KEY else []
) + (
    ['social_core.backends.google.GooglePlusAuth'] if SOCIAL_AUTH_GOOGLE_PLUS_KEY else []
) + [
    'verified_email_field.auth.VerifiedEmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DATABASE_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.environ.get('DATABASE_NAME', os.path.join(DATA_DIR, 'db.sqlite3')),
        'HOST': os.environ.get('DATABASE_HOST', None),
        'PORT': os.environ.get('DATABASE_PORT', None),
        'USER': os.environ.get('DATABASE_USER', None),
        'PASSWORD': os.environ.get('DATABASE_PASSWORD', None),
    }
}

if DATABASES['default']['ENGINE'].endswith('mysql'):
    DATABASES['default']['OPTIONS'] = {
        'init_command': (
            'ALTER DATABASE `{name}` DEFAULT CHARACTER SET utf8 COLLATE {collate}; '
            'SET default_storage_engine=INNODB; SET sql_mode=STRICT_TRANS_TABLES; '
            .format(
                name=DATABASES['default']['NAME'],
                collate=os.environ.get('DATABASE_COLLATE', 'utf8_czech_ci'),
            )
        )
    }

# Leprikon URL
LEPRIKON_URL = os.environ.get('LEPRIKON_URL')

# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

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
] if not DEBUG else []


# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGES = (
    ('cs', _('Czech')),
)

LANGUAGE_CODE = LANGUAGES[0][0]

TIME_ZONE = 'Europe/Prague'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# set max upload size to 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = '/static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'htdocs', 'media')
STATIC_ROOT = os.path.join(BASE_DIR, 'htdocs', 'static')

STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')] if os.path.exists(os.path.join(BASE_DIR, 'static')) else []
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'staticfiles_downloader.DownloaderFinder',
]

LOCALE_PATHS = [os.path.join(BASE_DIR, 'locale')] if os.path.exists(os.path.join(BASE_DIR, 'locale')) else []

# Logging
# https://docs.djangoproject.com/en/1.11/topics/logging/

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
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
    },
    'loggers': {
        '': {
            'level': 'DEBUG' if DEBUG else 'WARNING',
            'handlers': ['console'],
        },
        'django.db.backends': {
            'level': 'DEBUG' if DBDEBUG else 'ERROR',
            'propagate': True,
        },
        'parso': {
            'level': 'INFO',
        },
    },
}
if not DEBUG_LML:
    LOGGING['loggers']['lml'] = {'level': 'WARNING'}
    LOGGING['loggers']['pyexcel'] = {'level': 'WARNING'}
    LOGGING['loggers']['pyexcel_io'] = {'level': 'WARNING'}


# Sentry configuration
if not DEBUG and os.environ.get('SENTRY_DSN'):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from leprikon import __version__

    sentry_sdk.init(
        dsn=os.environ.get('SENTRY_DSN'),
        integrations=[DjangoIntegration()],
        send_default_pii=True,
        release=__version__,
    )


# Caching and session configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': os.environ.get('MEMCACHED_LOCATION', '127.0.0.1:11211'),
        'KEY_PREFIX': os.environ.get('MEMCACHED_KEY_PREFIX', 'leprikon'),
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
if 'SESSION_COOKIE_AGE' in os.environ:
    SESSION_COOKIE_AGE = int(os.environ['SESSION_COOKIE_AGE'])
if 'SESSION_STAFF_COOKIE_AGE' in os.environ:
    SESSION_STAFF_COOKIE_AGE = int(os.environ['SESSION_STAFF_COOKIE_AGE'])

# Login / logout urls
LOGIN_URL = 'leprikon:user_login'
LOGOUT_URL = 'leprikon:user_logout'
LOGIN_REDIRECT_URL = 'leprikon:summary'
LOGIN_ERROR_URL = LOGIN_URL

# Email configuration
SERVER_EMAIL = os.environ.get('SERVER_EMAIL', 'leprikon@localhost')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '25'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_SUBJECT_PREFIX = os.environ.get('EMAIL_SUBJECT_PREFIX', '[Leprikón] ').strip() + ' '
EMAIL_BACKEND = (
    'django.core.mail.backends.console.EmailBackend'
    if 'EMAIL' in os.environ.get('DEBUG', '').split(',')
    else 'django.core.mail.backends.smtp.EmailBackend'
)

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

THUMBNAIL_DEBUG = 'THUMBNAIL' in os.environ.get('DEBUG', '').split(',')

THUMBNAIL_PROCESSORS = (
    'easy_thumbnails.processors.colorspace',
    'easy_thumbnails.processors.autocrop',
    'filer.thumbnail_processors.scale_and_crop_with_subject_location',
    'easy_thumbnails.processors.filters',
)

# Haystack configuration
HAYSTACK_CONNECTIONS = {
    'default': {'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine'},
}
for key, value in os.environ.items():
    if key.startswith('HAYSTACK_'):
        HAYSTACK_CONNECTIONS['default'][key[len('HAYSTACK_'):]] = value
if HAYSTACK_CONNECTIONS['default']['ENGINE'] == 'haystack.backends.whoosh_backend.WhooshEngine':
    HAYSTACK_CONNECTIONS['default'].setdefault('PATH', os.path.join(DATA_DIR, 'whoosh_index'))

# Rocket.Chat URL
ROCKETCHAT_URL = os.environ.get('ROCKETCHAT_URL')

# Google Analytics configuration
GANALYTICS_TRACKING_CODE = os.environ.get('GANALYTICS_TRACKING_CODE')

# Leprikon configuration
PRICE_DECIMAL_PLACES = 0
COUNTRIES_FIRST = ['CZ', 'SK']
if 'LEPRIKON_VARIABLE_SYMBOL_EXPRESSION' in os.environ:
    LEPRIKON_VARIABLE_SYMBOL_EXPRESSION = os.environ.get('LEPRIKON_VARIABLE_SYMBOL_EXPRESSION')

LEPRIKON_SHOW_SUBJECT_CODE = os.environ.get('LEPRIKON_SHOW_SUBJECT_CODE', '').lower() in ('1', 'y', 'yes', 't', 'true')
