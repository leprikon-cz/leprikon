"""leprikon.site URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sites.models import Site

try:
    urlpatterns = [
        url(r"^admin/", include(admin.site.urls)),
        url(r"^pays/", include("django_pays.urls")),
        url(r"^social/", include("social_django.urls")),
        url(r"^verified-email-field/", include("verified_email_field.urls")),
        url(r"^", include("cms.urls")),
        # this won't work for displaying pages,
        # but allows reverse resolving before leprikon apphook is attached to any page
        url(r"^leprikon", include("leprikon.urls")),
    ]
except Site.DoesNotExist:
    # this may happen during data migration
    print("Failed to load urls, because there is no Site.")
    urlpatterns = []

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
