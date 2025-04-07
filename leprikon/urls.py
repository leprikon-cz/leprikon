from django.db import transaction
from django.urls import path
from django.views.generic.base import RedirectView

from . import views
from .conf import settings

# dictionary of all LEPRIKON_URL_* attributes of settings
LEPRIKON_URL = dict(
    (attr.lower()[len("LEPRIKON_URL_") :], getattr(settings, attr))
    for attr in dir(settings)
    if attr.startswith("LEPRIKON_URL_")
)


def d_path(pattern, name):
    return path(pattern.format(**LEPRIKON_URL), transaction.atomic(getattr(views, name)), name=name)


app_name = "leprikon"

urlpatterns = [
    path("", RedirectView.as_view(url="{summary}/".format(**LEPRIKON_URL), permanent=True), name="index"),
    d_path("{summary}/", "summary"),
    d_path("{create_account}/", "user_create"),
    d_path("{user}/{agreement}/", "user_agreement"),
    d_path("{user}/{email}/", "user_email"),
    d_path("{user}/", "user_update"),
    d_path("{user}/{password}/", "user_password"),
    d_path("{login}/", "user_login"),
    d_path("{logout}/", "user_logout"),
    d_path("{password_reset}/", "password_reset"),
    d_path("{password_reset}/done/", "password_reset_done"),
    d_path(
        "{password_reset}/<uidb64>/<token>/",
        "password_reset_confirm",
    ),
    d_path("{password_reset}/complete/", "password_reset_complete"),
    d_path("{leader}/", "leader_summary"),
    d_path("{leader}/{journal}/<int:pk>/", "journal"),
    d_path("{leader}/{journal}/{add}/<int:activity>/", "journal_create"),
    d_path("{leader}/{journal}/<int:pk>/{edit}/", "journal_update"),
    d_path("{leader}/{journal}/<int:pk>/{delete}/", "journal_delete"),
    d_path("{leader}/{journal}/{journalentry}/{add}/<int:journal>/", "journalentry_create"),
    d_path("{leader}/{journal}/{journalentry}/<int:pk>/", "journalentry_update"),
    d_path("{leader}/{journal}/{journalentry}/<int:pk>/{delete}/", "journalentry_delete"),
    d_path("{leader}/{journal}/{alternating}/", "alternating"),
    d_path("{leader}/{timesheets}/", "timesheet_list"),
    d_path("{leader}/{timesheets}/<int:pk>/", "timesheet_detail"),
    d_path("{leader}/{timesheets}/<int:pk>/{submit}/", "timesheet_submit"),
    d_path("{leader}/{timesheets}/{entry}/{add}/", "timesheetentry_create"),
    d_path("{leader}/{timesheets}/{entry}/<int:pk>/", "timesheetentry_update"),
    d_path("{leader}/{timesheets}/{entry}/<int:pk>/{delete}/", "timesheetentry_delete"),
    d_path("{leader}/{timesheets}/{journalentry}/<int:pk>/", "journalleaderentry_update"),
    d_path("{leader}/{timesheets}/{journalentry}/<int:pk>/{delete}/", "journalleaderentry_delete"),
    d_path("{leader}/<activity_type>/", "activity_list_mine"),
    d_path("{leader}/<activity_type>/<int:pk>/{edit}/", "activity_update"),
    d_path("{leader}/<activity_type>/<int:pk>/{journals}/", "activity_journals"),
    d_path("{leader}/<activity_type>/<int:pk>/{registrations}/", "activity_registrations"),
    d_path("{registrations}/", "registration_list"),
    d_path(
        "{registrations}/<int:pk>/{payment_request}-<variable_symbol>.pdf",
        "registration_payment_request",
    ),
    d_path("{registrations}/<int:pk>/<slug>.pdf", "registration_pdf"),
    d_path("{registrations}/<int:pk>/{cancel}/", "registration_cancel"),
    d_path("{registration_link}/<registration_link>/", "registration_link"),
    d_path("{registration_link}/<registration_link>/<int:pk>/", "registration_link_form"),
    d_path("{registration_link}/<registration_link>/<int:pk>/<int:variant_pk>/", "registration_link_form"),
    d_path("{payments}/", "payment_list"),
    d_path("{received_payments}/<int:pk>/<slug>.pdf", "received_payment_pdf"),
    d_path("{returned_payments}/<int:pk>/<slug>.pdf", "returned_payment_pdf"),
    d_path("{refund_requests}/<int:pk>/{add}/", "refund_request_create"),
    d_path("{refund_requests}/<int:pk>/", "refund_request_update"),
    d_path("{refund_requests}/<int:pk>/{delete}/", "refund_request_delete"),
    d_path("{payment_transfer}/<int:pk>/{add}/", "payment_transfer_create"),
    d_path("{donations}/<int:pk>/{add}/", "donation_create"),
    d_path("{donations}/", "donation_list"),
    d_path("{donations}/<pk>/<slug>.pdf", "donation_pdf"),
    d_path("{participants}/", "participant_list"),
    d_path("{participants}/{add}/", "participant_create"),
    d_path("{participants}/<int:pk>/", "participant_update"),
    d_path("{participants}/<int:pk>/{delete}/", "participant_delete"),
    d_path("{participants}/{parent}/{add}/", "parent_create"),
    d_path("{participants}/{parent}/<int:pk>/", "parent_update"),
    d_path("{participants}/{parent}/<int:pk>/{delete}/", "parent_delete"),
    d_path("{billing_info}/", "billing_info_list"),
    d_path("{billing_info}/{add}/", "billing_info_create"),
    d_path("{billing_info}/<int:pk>/", "billing_info_update"),
    d_path("{billing_info}/<int:pk>/{delete}/", "billing_info_delete"),
    d_path("{messages}/", "message_list"),
    d_path("{messages}/<slug>/", "message_detail"),
    d_path("{school_year}/", "school_year"),
    d_path("{reports}/", "report_list"),
    d_path("{reports}/{courses}/{payments}/", "report_course_payments"),
    d_path("{reports}/{courses}/{payments_status}/", "report_course_payments_status"),
    d_path("{reports}/{courses}/{stats}/", "report_course_stats"),
    d_path("{reports}/{events}/{payments}/", "report_event_payments"),
    d_path("{reports}/{events}/{payments_status}/", "report_event_payments_status"),
    d_path("{reports}/{events}/{stats}/", "report_event_stats"),
    d_path("{reports}/{orderables}/{payments}/", "report_orderable_payments"),
    d_path("{reports}/{orderables}/{payments_status}/", "report_orderable_payments_status"),
    d_path("{reports}/{orderables}/{stats}/", "report_orderable_stats"),
    d_path("{reports}/{debtors}/", "report_debtors"),
    d_path("{terms_conditions}/", "terms_conditions"),
]
