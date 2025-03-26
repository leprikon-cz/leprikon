import locale

import icu
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

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
    statgroup,
    subjects,
    targetgroup,
    timesheets,
    transaction,
    user,
)

User = get_user_model()

admin.site.site_header = _("Leprikon administration")
admin.site.site_title = _("Leprikon administration")


def get_app_list(self, request, app_label=None):
    """
    Return a sorted list of all the installed apps that have been
    registered in this site.
    """
    collator = icu.Collator.createInstance(icu.Locale(".".join(locale.getlocale())))
    app_dict = self._build_app_dict(request, app_label)

    # Sort the apps alphabetically.
    app_list = sorted(app_dict.values(), key=lambda x: collator.getSortKey(x["name"].lower()))

    # Sort the models alphabetically within each app.
    for app in app_list:
        app["models"].sort(key=lambda x: collator.getSortKey(x["name"].lower()))

    return app_list


# override default Admin site's app_index and get_app_list
admin.sites.AdminSite.get_app_list = get_app_list
