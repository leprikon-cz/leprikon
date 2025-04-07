from cms.app_base import CMSApp
from cms.apphook_pool import apphook_pool
from django.db import transaction
from django.urls import path
from django.utils.translation import gettext_lazy as _

from . import views
from .urls import LEPRIKON_URL


@apphook_pool.register
class LeprikonApp(CMSApp):
    name = _("Leprikon")
    app_name = "leprikon"

    def get_urls(self, page=None, language=None, **kwargs):
        return ["leprikon.urls"]


@apphook_pool.register
class LeprikonActivityTypeApp(CMSApp):
    name = _("Leprikon activity type")
    app_name = "leprikon_activity_type"

    def get_urls(self, page=None, language=None, **kwargs):
        return [
            path("", views.activity_list, name="activity_list"),
            path("<int:pk>/", views.activity_detail, name="activity_detail"),
            path(
                "<int:pk>/{registration}/".format(**LEPRIKON_URL),
                transaction.atomic(views.registration_form),
                name="registration_form",
            ),
            path(
                "<int:pk>/<int:variant_pk>/{registration}/".format(**LEPRIKON_URL),
                transaction.atomic(views.registration_form),
                name="registration_form",
            ),
        ]


@apphook_pool.register
class LeprikonLeadersApp(CMSApp):
    name = _("Leprikon leaders")
    app_name = "leprikon_leaders"

    def get_urls(self, page=None, language=None, **kwargs):
        return [
            path("", views.leader_list, name="leader_list"),
            path("<slug>/", views.leader_detail, name="leader_detail"),
        ]
