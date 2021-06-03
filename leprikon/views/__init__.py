from django.contrib.auth.decorators import user_passes_test
from django.urls import reverse_lazy as reverse
from django.views.decorators.csrf import csrf_exempt

from ..conf import settings
from . import (
    billing_info,
    donation,
    journals,
    leaders,
    messages,
    parents,
    participants,
    refundrequest,
    registrationlink,
    registrations,
    reports,
    schoolyear,
    subjects,
    summaries,
    terms_conditions,
    timesheets,
    user,
)
from .reports import (
    courses as reports_courses,
    debtors as reports_debtors,
    events as reports_events,
    orderables as reports_orderables,
)

login_url = reverse("leprikon:user_login")


def _user_is_leader(u):
    try:
        u.leprikon_leader
        return True
    except Exception:
        return False


login_required = user_passes_test(
    lambda u: u.is_authenticated,
    login_url=login_url,
    redirect_field_name=settings.LEPRIKON_PARAM_BACK,
)

leader_required = user_passes_test(
    _user_is_leader,
    login_url=login_url,
    redirect_field_name=settings.LEPRIKON_PARAM_BACK,
)

leader_or_staff_required = user_passes_test(
    lambda u: u.is_staff or _user_is_leader(u),
    login_url=login_url,
    redirect_field_name=settings.LEPRIKON_PARAM_BACK,
)

staff_required = user_passes_test(
    lambda u: u.is_staff,
    login_url=login_url,
    redirect_field_name=settings.LEPRIKON_PARAM_BACK,
)


summary = login_required(summaries.SummaryView.as_view())

user_create = user.UserCreateView.as_view()
user_agreement = login_required(user.UserAgreementView.as_view())
user_update = login_required(user.UserUpdateView.as_view())
user_email = login_required(user.UserEmailView.as_view())
user_login = user.UserLoginView.as_view()
user_logout = user.UserLogoutView.as_view()
user_password = user.UserPasswordView.as_view()
password_reset = user.PasswordResetView.as_view()
password_reset_done = user.PasswordResetDoneView.as_view()
password_reset_confirm = user.PasswordResetConfirmView.as_view()
password_reset_complete = user.PasswordResetCompleteView.as_view()

registration_list = login_required(registrations.RegistrationsListView.as_view())
registration_pdf = login_required(subjects.SubjectRegistrationPdfView.as_view())
registration_payment_request = login_required(subjects.SubjectRegistrationPaymentRequestView.as_view())
registration_cancel = login_required(subjects.SubjectRegistrationCancelView.as_view())

registration_link = registrationlink.RegistrationLinkView.as_view()
registration_link_form = login_required(registrationlink.RegistrationLinkFormView.as_view())

payment_list = login_required(subjects.SubjectPaymentsListView.as_view())
received_payment_pdf = login_required(subjects.SubjectReceivedPaymentPdfView.as_view())
returned_payment_pdf = login_required(subjects.SubjectReturnedPaymentPdfView.as_view())

refund_request_create = login_required(refundrequest.RefundRequestCreateView.as_view())
refund_request_update = login_required(refundrequest.RefundRequestUpdateView.as_view())
refund_request_delete = login_required(refundrequest.RefundRequestDeleteView.as_view())
payment_transfer_create = login_required(refundrequest.PaymentTransferCreateView.as_view())
donation_create = login_required(refundrequest.DonationCreateView.as_view())
donation_list = login_required(donation.DonationListView.as_view())
donation_pdf = login_required(donation.DonationPdfView.as_view())

participant_list = login_required(participants.ParticipantListView.as_view())
participant_create = login_required(participants.ParticipantCreateView.as_view())
participant_update = login_required(participants.ParticipantUpdateView.as_view())
participant_delete = login_required(participants.ParticipantDeleteView.as_view())

parent_create = login_required(parents.ParentCreateView.as_view())
parent_update = login_required(parents.ParentUpdateView.as_view())
parent_delete = login_required(parents.ParentDeleteView.as_view())

billing_info_list = login_required(billing_info.BillingInfoListView.as_view())
billing_info_create = login_required(billing_info.BillingInfoCreateView.as_view())
billing_info_update = login_required(billing_info.BillingInfoUpdateView.as_view())
billing_info_delete = login_required(billing_info.BillingInfoDeleteView.as_view())

leader_summary = leader_required(summaries.LeaderSummaryView.as_view())
alternating = leader_required(journals.AlternatingView.as_view())
journal = leader_or_staff_required(journals.JournalView.as_view())
journalentry_create = leader_or_staff_required(journals.JournalEntryCreateView.as_view())
journalentry_update = leader_or_staff_required(journals.JournalEntryUpdateView.as_view())
journalentry_delete = leader_or_staff_required(journals.JournalEntryDeleteView.as_view())
journalleaderentry_update = leader_or_staff_required(journals.JournalLeaderEntryUpdateView.as_view())
journalleaderentry_delete = leader_or_staff_required(journals.JournalLeaderEntryDeleteView.as_view())

subject_list = subjects.SubjectListView.as_view()
subject_list_mine = leader_required(subjects.SubjectListMineView.as_view())
subject_detail = subjects.SubjectDetailView.as_view()
subject_registration_form = login_required(subjects.SubjectRegistrationFormView.as_view())
subject_update = leader_or_staff_required(subjects.SubjectUpdateView.as_view())
subject_registrations = leader_or_staff_required(subjects.SubjectRegistrationsView.as_view())

message_list = login_required(messages.MessageListView.as_view())
message_detail = csrf_exempt(messages.MessageDetailView.as_view())

leader_list = leaders.LeaderListView.as_view()

timesheet_list = leader_required(timesheets.TimesheetListView.as_view())
timesheet_detail = leader_required(timesheets.TimesheetDetailView.as_view())
timesheet_submit = leader_required(timesheets.TimesheetSubmitView.as_view())
timesheetentry_create = leader_required(timesheets.TimesheetEntryCreateView.as_view())
timesheetentry_update = leader_required(timesheets.TimesheetEntryUpdateView.as_view())
timesheetentry_delete = leader_required(timesheets.TimesheetEntryDeleteView.as_view())

school_year = schoolyear.SchoolYearView.as_view()

report_list = staff_required(reports.ReportsListView.as_view())
report_course_payments = staff_required(reports_courses.ReportCoursePaymentsView.as_view())
report_course_payments_status = staff_required(reports_courses.ReportCoursePaymentsStatusView.as_view())
report_course_stats = staff_required(reports_courses.ReportCourseStatsView.as_view())
report_event_payments = staff_required(reports_events.ReportEventPaymentsView.as_view())
report_event_payments_status = staff_required(reports_events.ReportEventPaymentsStatusView.as_view())
report_event_stats = staff_required(reports_events.ReportEventStatsView.as_view())
report_orderable_payments = staff_required(reports_orderables.ReportOrderablePaymentsView.as_view())
report_orderable_payments_status = staff_required(reports_orderables.ReportOrderablePaymentsStatusView.as_view())
report_orderable_stats = staff_required(reports_orderables.ReportOrderableStatsView.as_view())
report_debtors = staff_required(reports_debtors.ReportDebtorsView.as_view())

terms_conditions = terms_conditions.TermsConditionsView.as_view()
