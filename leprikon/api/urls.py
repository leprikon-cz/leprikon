from django.urls import path

from . import views


def l_path(pattern, name):
    return path(pattern, getattr(views, name), name=name)


urlpatterns = [
    l_path("participants/<int:journal_id>/", "participants"),
]
