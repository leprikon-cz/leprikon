"""
Django settings for leprikon.site project.

Generated by 'django-admin startproject' using Django 3.2.15.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

import os
import re

from django.utils.translation import gettext_lazy as _

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.environ.get("BASE_DIR", os.getcwd())
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY", os.environ.get("DEBUG"))
if not SECRET_KEY:
    from string import ascii_letters, digits, punctuation

    from django.utils.crypto import get_random_string

    SECRET_KEY = get_random_string(
        64,
        ascii_letters + digits + punctuation,
    )

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG_TOKENS = os.environ.get("DEBUG", "").split(",")
DEBUG = "DEBUG" in DEBUG_TOKENS
DEBUG_DB = "DB" in DEBUG_TOKENS
DEBUG_TEMPLATE = "TEMPLATE" in DEBUG_TOKENS
DEBUG_LML = "LML" in DEBUG_TOKENS
DEBUG_LOG = "LOG" in DEBUG_TOKENS

ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "*").split(",")]


# Application definition

INSTALLED_APPS = [
    "user_unique_email",
    "leprikon.site",
    "leprikon",
    "adminsortable2",
    "bankreader",
    "djangocms_admin_style",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.sitemaps",
    "django_cron",
    "django_pays",
    "djangocms_audio",
    "djangocms_file",
    "djangocms_picture",
    "djangocms_video",
    "cms",
    "haystack",
    "mathfilters",
    "menus",
    "multiselectfield",
    "sekizai",
    "template_admin",
    "treebeard",
    "filer",
    "easy_thumbnails",
    "djangocms_link",
    "djangocms_text_ckeditor",
    "ganalytics",
    "html2rml",
    "qr_code",
    "social_django",
    "verified_email_field",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "rest_framework",
]

CMSPLUGIN_FILER_MIGRATED = os.environ.get("CMSPLUGIN_FILER_MIGRATED", "no").lower() in ("yes", "true")
if not CMSPLUGIN_FILER_MIGRATED:
    print(
        """
        Please migrate all content using plugins from cmsplugin_filer
        to corresponding djangocms_* plugins.
        When done, run commands:

        for app in cmsplugin_filer_{folder,file,image,link,teaser,video}; do
            leprikon migrate $app zero
        done

        and set CMSPLUGIN_FILER_MIGRATED environment variable to "yes".
        """
    )
    INSTALLED_APPS += [
        "cmsplugin_filer_file",
        "cmsplugin_filer_folder",
        "cmsplugin_filer_image",
        "cmsplugin_filer_link",
        "cmsplugin_filer_teaser",
        "cmsplugin_filer_utils",
        "cmsplugin_filer_video",
    ]

MIDDLEWARE = [
    "cms.middleware.utils.ApphookReloadMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "cms.middleware.user.CurrentUserMiddleware",
    "cms.middleware.page.CurrentPageMiddleware",
    "cms.middleware.toolbar.ToolbarMiddleware",
    "cms.middleware.language.LanguageCookieMiddleware",
    "social_django.middleware.SocialAuthExceptionMiddleware",
    "leprikon.middleware.LeprikonMiddleware",
]

CRON_CLASSES = [
    "leprikon.cronjobs.SendPaymentRequest",
]

CRON_SEND_PAYMENT_REQUEST_TIME = os.environ.get("CRON_SEND_PAYMENT_REQUEST_TIME", "8:00")

ROOT_URLCONF = os.environ.get("ROOT_URLCONF", "leprikon.site.urls")

BASE_TEMPLATE_LOADERS = [
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
]
TEMPLATE_LOADERS = [
    (
        "template_admin.loader.Loader",
        (
            BASE_TEMPLATE_LOADERS
            if DEBUG_TEMPLATE
            else [
                ("django.template.loaders.cached.Loader", BASE_TEMPLATE_LOADERS),
            ]
        ),
    ),
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.csrf",
                "django.template.context_processors.tz",
                "django.template.context_processors.static",
                "sekizai.context_processors.sekizai",
                "cms.context_processors.cms_settings",
                "social_django.context_processors.backends",
                "social_django.context_processors.login_redirect",
            ],
            "debug": DEBUG_TEMPLATE,
            "loaders": TEMPLATE_LOADERS,
        },
    },
]

WSGI_APPLICATION = os.environ.get("UWSGI_MODULE", "leprikon.site.wsgi:application").replace(":", ".")

# Social configuration
SOCIAL_AUTH_FACEBOOK_SCOPE = ["email"]
SOCIAL_AUTH_FACEBOOK_PROFILE_EXTRA_PARAMS = {"fields": "id,name,email"}
SOCIAL_AUTH_FACEBOOK_KEY = os.environ.get("SOCIAL_AUTH_FACEBOOK_KEY")
SOCIAL_AUTH_FACEBOOK_SECRET = os.environ.get("SOCIAL_AUTH_FACEBOOK_SECRET")

SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = ["profile", "email"]
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY")
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get("SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET")

SOCIAL_AUTH_GOOGLE_PLUS_SCOPE = ["profile", "email"]
SOCIAL_AUTH_GOOGLE_PLUS_KEY = os.environ.get("SOCIAL_AUTH_GOOGLE_PLUS_KEY")
SOCIAL_AUTH_GOOGLE_PLUS_SECRET = os.environ.get("SOCIAL_AUTH_GOOGLE_PLUS_SECRET")

SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.get_username",
    "social_core.pipeline.social_auth.associate_by_email",
    "social_core.pipeline.user.create_user",
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
    "social_core.pipeline.user.user_details",
)

# Authentication configuration
AUTHENTICATION_BACKENDS = (
    (["social_core.backends.facebook.FacebookOAuth2"] if SOCIAL_AUTH_FACEBOOK_KEY else [])
    + (["social_core.backends.google.GoogleOAuth2"] if SOCIAL_AUTH_GOOGLE_OAUTH2_KEY else [])
    + (["social_core.backends.google.GooglePlusAuth"] if SOCIAL_AUTH_GOOGLE_PLUS_KEY else [])
    + [
        "verified_email_field.auth.VerifiedEmailBackend",
        "django.contrib.auth.backends.ModelBackend",
    ]
)

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DATABASE_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.environ.get("DATABASE_NAME", os.path.join(DATA_DIR, "db.sqlite3")),
        "HOST": os.environ.get("DATABASE_HOST", None),
        "PORT": os.environ.get("DATABASE_PORT", None),
        "USER": os.environ.get("DATABASE_USER", None),
        "PASSWORD": os.environ.get("DATABASE_PASSWORD", None),
    }
}

if DATABASES["default"]["ENGINE"].endswith("mysql"):
    DATABASES["default"]["OPTIONS"] = {
        "charset": "utf8mb4",
        "use_unicode": True,
        "init_command": (
            "ALTER DATABASE `{name}` CHARACTER SET utf8mb4 COLLATE {collate}; "
            "SET default_storage_engine=INNODB; SET sql_mode=STRICT_TRANS_TABLES; ".format(
                name=DATABASES["default"]["NAME"],
                collate=os.environ.get("DATABASE_COLLATE", "utf8mb4_czech_ci"),
            )
        ),
    }

# Leprikon URL
LEPRIKON_DOMAIN = os.environ.get("LEPRIKON_DOMAIN")
LEPRIKON_URL = os.environ.get("LEPRIKON_URL", LEPRIKON_DOMAIN and f"https://{LEPRIKON_DOMAIN}")

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = (
    [
        {
            "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        },
        {
            "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        },
        {
            "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
        },
        {
            "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
        },
    ]
    if not DEBUG
    else []
)

# Custom User model
AUTH_USER_MODEL = "user_unique_email.User"

# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGES = (("cs", _("Czech")),)

LANGUAGE_CODE = LANGUAGES[0][0]

TIME_ZONE = "Europe/Prague"

USE_I18N = True

USE_L10N = True

USE_TZ = True

# set max upload size to 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = "/static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "htdocs", "media")
STATIC_ROOT = os.path.join(BASE_DIR, "htdocs", "static")

STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")] if os.path.exists(os.path.join(BASE_DIR, "static")) else []
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "staticfiles_downloader.DownloaderFinder",
]
if not DEBUG:
    STATICFILES_STORAGE = "leprikon.staticfiles.NotStrictManifestStaticFilesStorage"

LOCALE_PATHS = [os.path.join(BASE_DIR, "locale")] if os.path.exists(os.path.join(BASE_DIR, "locale")) else []

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Logging
# https://docs.djangoproject.com/en/3.2/topics/logging/

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "%(levelname)s %(asctime)s %(module)s " "%(process)d %(thread)d %(message)s"},
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "filters": [],
        },
    },
    "loggers": {
        "": {
            "level": "DEBUG" if DEBUG_LOG else "WARNING",
            "handlers": ["console"],
        },
        "django.db.backends": {
            "level": "DEBUG" if DEBUG_DB else "ERROR",
            "propagate": True,
        },
        "parso": {
            "level": "INFO",
        },
    },
}
if not DEBUG_LML:
    LOGGING["loggers"]["lml"] = {"level": "WARNING"}
    LOGGING["loggers"]["pyexcel"] = {"level": "WARNING"}
    LOGGING["loggers"]["pyexcel_io"] = {"level": "WARNING"}


# Sentry configuration
if not DEBUG and os.environ.get("SENTRY_DSN"):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    from leprikon import __version__

    sentry_sdk.init(
        dsn=os.environ.get("SENTRY_DSN"),
        integrations=[DjangoIntegration()],
        send_default_pii=True,
        release=__version__,
    )


# Caching and session configuration
# Only configure remote cache if explicitly specified in the environment.
# Otherwise it would be enabled during `leprikon collectstatic` during build.
if "CACHE_LOCATION" in os.environ:
    CACHES = {
        "default": {
            "BACKEND": os.environ.get("CACHE_BACKEND", "django_redis.cache.RedisCache"),
            "LOCATION": os.environ.get("CACHE_LOCATION"),
        }
    }
    if CACHES["default"]["BACKEND"] == "django_redis.cache.RedisCache":
        CACHES["default"]["OPTIONS"] = {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    if "CACHE_KEY_PREFIX" in os.environ:
        CACHES["default"]["KEY_PREFIX"] = os.environ["CACHE_KEY_PREFIX"]

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
if "SESSION_COOKIE_AGE" in os.environ:
    SESSION_COOKIE_AGE = int(os.environ["SESSION_COOKIE_AGE"])
if "SESSION_STAFF_COOKIE_AGE" in os.environ:
    SESSION_STAFF_COOKIE_AGE = int(os.environ["SESSION_STAFF_COOKIE_AGE"])

# Login / logout urls
LOGIN_URL = "leprikon:user_login"
LOGOUT_URL = "leprikon:user_logout"
LOGIN_REDIRECT_URL = "leprikon:summary"
LOGIN_ERROR_URL = LOGIN_URL

# Email configuration
SERVER_EMAIL = os.environ.get("SERVER_EMAIL", "leprikon@localhost")
SERVER_EMAIL_PLAIN = re.search("[^<]+@[^>]+", SERVER_EMAIL).group()

EMAIL_BACKEND = (
    "django.core.mail.backends.console.EmailBackend"
    if "EMAIL" in os.environ.get("DEBUG", "").split(",")
    else "django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "25"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_SUBJECT_PREFIX = os.environ.get("EMAIL_SUBJECT_PREFIX", "[Leprikón] ").strip() + " "
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "").lower() in ("y", "yes", "t", "true", "1", "on")
DEFAULT_FROM_EMAIL = SERVER_EMAIL

# CMS configuration
# http://djangocms.readthedocs.io/en/latest/reference/configuration/
SITE_ID = 1

CMS_LANGUAGES = {
    SITE_ID: [{"code": lang[0], "name": lang[1]} for lang in LANGUAGES],
    "default": {
        "public": True,
        "fallbacks": [LANGUAGE_CODE],
        "hide_untranslated": True,
        "redirect_on_fallback": True,
    },
}

CMS_TEMPLATES = [
    ("leprikon/cms.html", "Leprikon"),
]

CMS_PERMISSION = True

CMS_PLACEHOLDER_CONF = {}

THUMBNAIL_DEBUG = "THUMBNAIL" in os.environ.get("DEBUG", "").split(",")

THUMBNAIL_PROCESSORS = (
    "easy_thumbnails.processors.colorspace",
    "easy_thumbnails.processors.autocrop",
    # "easy_thumbnails.processors.scale_and_crop",
    "filer.thumbnail_processors.scale_and_crop_with_subject_location",
    "easy_thumbnails.processors.filters",
    "easy_thumbnails.processors.background",
)

# Haystack configuration
HAYSTACK_CONNECTIONS = {
    "default": {"ENGINE": "haystack.backends.whoosh_backend.WhooshEngine"},
}
for key, value in os.environ.items():
    if key.startswith("HAYSTACK_"):
        HAYSTACK_CONNECTIONS["default"][key[len("HAYSTACK_") :]] = value
if HAYSTACK_CONNECTIONS["default"]["ENGINE"] == "haystack.backends.whoosh_backend.WhooshEngine":
    HAYSTACK_CONNECTIONS["default"].setdefault("PATH", os.path.join(DATA_DIR, "whoosh_index"))

# Google Analytics configuration
GANALYTICS_TRACKING_CODE = os.environ.get("GANALYTICS_TRACKING_CODE")

# Leprikon configuration
PRICE_DECIMAL_PLACES = 0
COUNTRIES_FIRST = ["CZ", "SK"]
if "LEPRIKON_VARIABLE_SYMBOL_EXPRESSION" in os.environ:
    LEPRIKON_VARIABLE_SYMBOL_EXPRESSION = os.environ.get("LEPRIKON_VARIABLE_SYMBOL_EXPRESSION")

LEPRIKON_SHOW_SUBJECT_CODE = os.environ.get("LEPRIKON_SHOW_SUBJECT_CODE", "").lower() in ("1", "y", "yes", "t", "true")

X_FRAME_OPTIONS = "SAMEORIGIN"


#
# Rest Framework
#
REST_FRAMEWORK = {
    "DEFAULT_PARSER_CLASSES": [
        "djangorestframework_camel_case.parser.CamelCaseJSONParser",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "djangorestframework_camel_case.render.CamelCaseJSONRenderer",
        "djangorestframework_camel_case.render.CamelCaseBrowsableAPIRenderer",
    ],
    "DEFAULT_SCHEMA_CLASS": "leprikon.api.openapi.Schema",
}

SPECTACULAR_SETTINGS = {
    # header
    "TITLE": "Leprikon API",
    "DESCRIPTION": "",
    "CONTACT": None,
    "LICENSE": None,
    "TOS": None,
    "VERSION": "v1",
    "SERVERS": [
        {"url": "http://localhost:8000/", "description": "local"},
    ],
    # options
    "CAMELIZE_NAMES": True,
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.contrib.djangorestframework_camel_case.camelize_serializer_fields",
        "drf_spectacular.hooks.postprocess_schema_enums",
    ],
    "REDOC_DIST": "SIDECAR",
    "SCHEMA_PATH_PREFIX": "/api",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
}
