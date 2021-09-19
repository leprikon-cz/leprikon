from django.conf.urls import url

from . import views


def l_url(pattern, name):
    return url(pattern, getattr(views, name), name=name)


urlpatterns = [
    l_url(r"^participants/(?P<journal_id>[0-9]+)/$", "participants"),
    l_url(r"^rocketchat/$", "rocketchat"),
]
