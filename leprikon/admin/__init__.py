import locale

import icu
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.http import Http404
from django.template.response import TemplateResponse
from django.utils.translation import ugettext_lazy as _

from . import (  # NOQA
    account,
    agegroup,
    agreements,
    citizenship,
    courses,
    department,
    donation,
    events,
    journals,
    leprikonsite,
    messages,
    orderables,
    organizations,
    place,
    printsetup,
    question,
    refundrequest,
    registrationlink,
    roles,
    school,
    schoolyear,
    subjects,
    targetgroup,
    timesheets,
    transaction,
    user,
)

User = get_user_model()

admin.site.site_header = _("Leprikon administration")
admin.site.site_title = _("Leprikon administration")


def app_index(self, request, app_label, extra_context=None):
    app_dict = self._build_app_dict(request, app_label)
    if not app_dict:
        raise Http404("The requested admin page does not exist.")
    # Sort the models alphabetically within each app.
    collator = icu.Collator.createInstance(icu.Locale(".".join(locale.getlocale())))
    app_dict["models"].sort(key=lambda x: collator.getSortKey(x["name"].lower()))
    context = dict(
        self.each_context(request),
        title=_("Leprikon administration"),
        app_list=[app_dict],
        app_label=app_label,
    )
    context.update(extra_context or {})

    request.current_app = self.name

    return TemplateResponse(
        request, self.app_index_template or ["admin/%s/app_index.html" % app_label, "admin/app_index.html"], context
    )


def get_app_list(self, request):
    """
    Returns a sorted list of all the installed apps that have been
    registered in this site.
    """
    collator = icu.Collator.createInstance(icu.Locale(".".join(locale.getlocale())))

    app_dict = self._build_app_dict(request)

    # Sort the apps alphabetically.
    app_list = sorted(app_dict.values(), key=lambda x: collator.getSortKey(x["name"].lower()))

    # Sort the models alphabetically within each app.
    for app in app_list:
        app["models"].sort(key=lambda x: collator.getSortKey(x["name"].lower()))

    return app_list


# override default Admin site's app_index and get_app_list
admin.sites.AdminSite.app_index = app_index
admin.sites.AdminSite.get_app_list = get_app_list
