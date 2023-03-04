from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter

from . import views


def l_path(pattern, name):
    return path(pattern, getattr(views, name), name=name)


app_name = "api"

api_router = DefaultRouter(trailing_slash=False)
api_router.register(r"journal", views.JournalViewSet, "journal")
api_router.register(r"schoolyear", views.SchoolYearViewSet, "schoolyear")
api_router.register(r"user", views.UserViewSet, "user")

urlpatterns = [
    l_path("api/participants/<int:journal_id>/", "participants"),
    path("api/", include(api_router.urls)),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("swagger/", SpectacularSwaggerView.as_view(url_name="api:schema"), name="swagger"),
    path("docs/", SpectacularRedocView.as_view(url_name="api:schema"), name="redoc"),
]
