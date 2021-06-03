from django.conf.urls import include, url
from django.db import transaction
from django.views.generic.base import RedirectView

from . import views
from .api import urls as api_urls
from .conf import settings

# dictionary of all LEPRIKON_URL_* attributes of settings
LEPRIKON_URL = dict(
    (attr.lower()[len("LEPRIKON_URL_") :], getattr(settings, attr))
    for attr in dir(settings)
    if attr.startswith("LEPRIKON_URL_")
)


def d_url(pattern, name):
    return url(pattern.format(**LEPRIKON_URL), transaction.atomic(getattr(views, name)), name=name)


app_name = "leprikon"

urlpatterns = [
    url(r"^$", RedirectView.as_view(url="{summary}/".format(**LEPRIKON_URL), permanent=True), name="index"),
    d_url(r"^{summary}/$", "summary"),
    d_url(r"^{create_account}/$", "user_create"),
    d_url(r"^{user}/{agreement}/$", "user_agreement"),
    d_url(r"^{user}/{email}/$", "user_email"),
    d_url(r"^{user}/$", "user_update"),
    d_url(r"^{user}/{password}/$", "user_password"),
    d_url(r"^{login}/$", "user_login"),
    d_url(r"^{logout}/$", "user_logout"),
    d_url(r"^{password_reset}/$", "password_reset"),
    d_url(r"^{password_reset}/done/$", "password_reset_done"),
    d_url(
        r"^{password_reset}/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{{1,13}}-[0-9A-Za-z]{{1,20}})/$",
        "password_reset_confirm",
    ),
    d_url(r"^{password_reset}/complete/$", "password_reset_complete"),
    d_url(r"^{leader}/$", "leader_summary"),
    d_url(r"^{leader}/{journal}/(?P<pk>[0-9]+)/$", "journal"),
    d_url(r"^{leader}/{journal}/{journalentry}/{add}/(?P<subject>[0-9]+)/$", "journalentry_create"),
    d_url(r"^{leader}/{journal}/{journalentry}/(?P<pk>[0-9]+)/$", "journalentry_update"),
    d_url(r"^{leader}/{journal}/{journalentry}/(?P<pk>[0-9]+)/{delete}/$", "journalentry_delete"),
    d_url(r"^{leader}/{journal}/{alternating}/$", "alternating"),
    d_url(r"^{leader}/{timesheets}/$", "timesheet_list"),
    d_url(r"^{leader}/{timesheets}/(?P<pk>[0-9]+)/$", "timesheet_detail"),
    d_url(r"^{leader}/{timesheets}/(?P<pk>[0-9]+)/{submit}/$", "timesheet_submit"),
    d_url(r"^{leader}/{timesheets}/{entry}/{add}/$", "timesheetentry_create"),
    d_url(r"^{leader}/{timesheets}/{entry}/(?P<pk>[0-9]+)/$", "timesheetentry_update"),
    d_url(r"^{leader}/{timesheets}/{entry}/(?P<pk>[0-9]+)/{delete}/$", "timesheetentry_delete"),
    d_url(r"^{leader}/{timesheets}/{journalentry}/(?P<pk>[0-9]+)/$", "journalleaderentry_update"),
    d_url(r"^{leader}/{timesheets}/{journalentry}/(?P<pk>[0-9]+)/{delete}/$", "journalleaderentry_delete"),
    d_url(r"^{leader}/(?P<subject_type>[^/]+)/$", "subject_list_mine"),
    d_url(r"^{leader}/(?P<subject_type>[^/]+)/(?P<pk>[0-9]+)/{edit}/$", "subject_update"),
    d_url(r"^{leader}/(?P<subject_type>[^/]+)/(?P<pk>[0-9]+)/{registrations}/$", "subject_registrations"),
    d_url(r"^{registrations}/$", "registration_list"),
    d_url(
        r"^{registrations}/(?P<pk>[^/]+)/{payment_request}-(?P<variable_symbol>[0-9]+).pdf$",
        "registration_payment_request",
    ),
    d_url(r"^{registrations}/(?P<pk>[^/]+)/(?P<slug>[^.]+).pdf$", "registration_pdf"),
    d_url(r"^{registrations}/(?P<pk>[^/]+)/{cancel}/$", "registration_cancel"),
    d_url(r"^{registration_link}/(?P<registration_link>[^/]+)/$", "registration_link"),
    d_url(r"^{registration_link}/(?P<registration_link>[^/]+)/(?P<pk>[0-9]+)/$", "registration_link_form"),
    d_url(r"^{payments}/$", "payment_list"),
    d_url(r"^{received_payments}/(?P<pk>[^/]+)/(?P<slug>[^.]+).pdf$", "received_payment_pdf"),
    d_url(r"^{returned_payments}/(?P<pk>[^/]+)/(?P<slug>[^.]+).pdf$", "returned_payment_pdf"),
    d_url(r"^{refund_requests}/(?P<pk>[0-9]+)/{add}/$", "refund_request_create"),
    d_url(r"^{refund_requests}/(?P<pk>[0-9]+)/$", "refund_request_update"),
    d_url(r"^{refund_requests}/(?P<pk>[0-9]+)/{delete}/$", "refund_request_delete"),
    d_url(r"^{payment_transfer}/(?P<pk>[0-9]+)/{add}/$", "payment_transfer_create"),
    d_url(r"^{donations}/(?P<pk>[0-9]+)/{add}/$", "donation_create"),
    d_url(r"^{donations}/$", "donation_list"),
    d_url(r"^{donations}/(?P<pk>[^/]+)/(?P<slug>[^.]+).pdf$", "donation_pdf"),
    d_url(r"^{participants}/$", "participant_list"),
    d_url(r"^{participants}/{add}/$", "participant_create"),
    d_url(r"^{participants}/(?P<pk>[0-9]+)/$", "participant_update"),
    d_url(r"^{participants}/(?P<pk>[0-9]+)/{delete}/$", "participant_delete"),
    d_url(r"^{participants}/{parent}/{add}/$", "parent_create"),
    d_url(r"^{participants}/{parent}/(?P<pk>[0-9]+)/$", "parent_update"),
    d_url(r"^{participants}/{parent}/(?P<pk>[0-9]+)/{delete}/$", "parent_delete"),
    d_url(r"^{billing_info}/$", "billing_info_list"),
    d_url(r"^{billing_info}/{add}/$", "billing_info_create"),
    d_url(r"^{billing_info}/(?P<pk>[0-9]+)/$", "billing_info_update"),
    d_url(r"^{billing_info}/(?P<pk>[0-9]+)/{delete}/$", "billing_info_delete"),
    d_url(r"^{messages}/$", "message_list"),
    d_url(r"^{messages}/(?P<slug>[^.]+)/$", "message_detail"),
    d_url(r"^{leaders}/$", "leader_list"),
    d_url(r"^{school_year}/$", "school_year"),
    d_url(r"^{reports}/$", "report_list"),
    d_url(r"^{reports}/{courses}/{payments}/$", "report_course_payments"),
    d_url(r"^{reports}/{courses}/{payments_status}/$", "report_course_payments_status"),
    d_url(r"^{reports}/{courses}/{stats}/$", "report_course_stats"),
    d_url(r"^{reports}/{events}/{payments}/$", "report_event_payments"),
    d_url(r"^{reports}/{events}/{payments_status}/$", "report_event_payments_status"),
    d_url(r"^{reports}/{events}/{stats}/$", "report_event_stats"),
    d_url(r"^{reports}/{orderables}/{payments}/$", "report_orderable_payments"),
    d_url(r"^{reports}/{orderables}/{payments_status}/$", "report_orderable_payments_status"),
    d_url(r"^{reports}/{orderables}/{stats}/$", "report_orderable_stats"),
    d_url(r"^{reports}/{debtors}/$", "report_debtors"),
    d_url(r"^{terms_conditions}/$", "terms_conditions"),
    url(r"^api/", include(api_urls, "api")),
]
