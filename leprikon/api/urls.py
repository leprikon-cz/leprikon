from __future__ import unicode_literals

from django.conf.urls import url

from ..conf import settings

from . import views

def l_url(pattern, name):
    return url(pattern, getattr(views, name), name=name)


urlpatterns = [
    l_url(r'^club-registrations/(?P<club_id>[0-9]+)/$',     'club_registrations'),
]

