"""leprikon.site URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sites.models import Site
from django.urls import include, path
from django.views.generic.base import RedirectView

try:
    urlpatterns = [
        path("favicon.ico", RedirectView.as_view(url="/static/favicon.ico")),
        path("admin/", admin.site.urls),
        path("pays/", include("django_pays.urls")),
        path("social/", include("social_django.urls")),
        path("verified-email-field/", include("verified_email_field.urls")),
        path("", include("leprikon.api.urls", namespace="api")),
        path("", include("cms.urls")),
        # this won't work for displaying pages,
        # but allows reverse resolving before leprikon apphook is attached to any page
        path("leprikon/", include("leprikon.urls")),
    ]
except Site.DoesNotExist:
    # this may happen during data migration
    print("Failed to load urls, because there is no Site.")
    urlpatterns = []

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
