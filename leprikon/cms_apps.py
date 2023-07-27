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
class LeprikonSubjectTypeApp(CMSApp):
    name = _("Leprikon subject type")
    app_name = "leprikon_subject_type"

    def get_urls(self, page=None, language=None, **kwargs):
        return [
            path("", views.subject_list, name="subject_list"),
            path("<int:pk>/", views.subject_detail, name="subject_detail"),
            path(
                "<int:pk>/{registration}/".format(**LEPRIKON_URL),
                transaction.atomic(views.subject_registration_form),
                name="subject_registration_form",
            ),
            path(
                "<int:pk>/<int:variant_pk>/{registration}/".format(**LEPRIKON_URL),
                transaction.atomic(views.subject_registration_form),
                name="subject_registration_form",
            ),
        ]
