from cms.app_base import CMSApp
from cms.apphook_pool import apphook_pool
from django.conf.urls import url
from django.db import transaction
from django.utils.translation import ugettext_lazy as _

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
            url(r"^$", views.subject_list, name="subject_list"),
            url(r"^(?P<pk>[0-9]+)/$", views.subject_detail, name="subject_detail"),
            url(
                r"^(?P<pk>[0-9]+)/{registration}/$".format(**LEPRIKON_URL),
                transaction.atomic(views.subject_registration_form),
                name="subject_registration_form",
            ),
        ]
