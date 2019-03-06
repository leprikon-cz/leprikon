from django.contrib.auth.decorators import user_passes_test
from django.core.urlresolvers import reverse_lazy as reverse
from django.views.decorators.csrf import csrf_exempt

from ..conf import settings
from . import (
    courses, leaders, messages, parents, participants, registrations, reports,
    schoolyear, subjects, summaries, terms_conditions, timesheets, user,
)
from .reports import (
    courses as reports_courses, debtors as reports_debtors,
    events as reports_events,
)

login_url = reverse('leprikon:user_login')


def _user_is_leader(u):
    try:
        u.leprikon_leader
        return True
    except:
        return False


login_required = user_passes_test(
    lambda u: u.is_authenticated(),
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


summary                         = login_required(summaries.SummaryView.as_view())

user_create                     = user.UserCreateView.as_view()
user_agreement                  = login_required(user.UserAgreementView.as_view())
user_update                     = login_required(user.UserUpdateView.as_view())
user_email                      = login_required(user.UserEmailView.as_view())
user_login                      = user.user_login
user_logout                     = user.user_logout
user_password                   = user.user_password
password_reset                  = user.password_reset
password_reset_done             = user.password_reset_done
password_reset_confirm          = user.password_reset_confirm
password_reset_complete         = user.password_reset_complete

registration_list               = login_required(registrations.RegistrationsListView.as_view())
registration_pdf                = login_required(subjects.SubjectRegistrationPdfView.as_view())
registration_cancel             = login_required(subjects.SubjectRegistrationCancelView.as_view())

payment_list                    = login_required(subjects.SubjectPaymentsListView.as_view())
payment_pdf                     = login_required(subjects.SubjectPaymentPdfView.as_view())

participant_list                = login_required(participants.ParticipantListView.as_view())
participant_create              = login_required(participants.ParticipantCreateView.as_view())
participant_update              = login_required(participants.ParticipantUpdateView.as_view())

parent_create                   = login_required(parents.ParentCreateView.as_view())
parent_update                   = login_required(parents.ParentUpdateView.as_view())

leader_summary                  = leader_required(summaries.LeaderSummaryView.as_view())
course_alternating              = leader_required(courses.CourseAlternatingView.as_view())
course_journal                  = leader_or_staff_required(courses.CourseJournalView.as_view())
coursejournalentry_create       = leader_or_staff_required(courses.CourseJournalEntryCreateView.as_view())
coursejournalentry_update       = leader_or_staff_required(courses.CourseJournalEntryUpdateView.as_view())
coursejournalentry_delete       = leader_or_staff_required(courses.CourseJournalEntryDeleteView.as_view())
coursejournalleaderentry_update = leader_or_staff_required(courses.CourseJournalLeaderEntryUpdateView.as_view())
coursejournalleaderentry_delete = leader_or_staff_required(courses.CourseJournalLeaderEntryDeleteView.as_view())

subject_list                    = subjects.SubjectListView.as_view()
subject_list_mine               = leader_required(subjects.SubjectListMineView.as_view())
subject_detail                  = subjects.SubjectDetailView.as_view()
subject_registration_form       = subjects.SubjectRegistrationFormView.as_view()
subject_update                  = leader_or_staff_required(subjects.SubjectUpdateView.as_view())
subject_registrations           = leader_or_staff_required(subjects.SubjectRegistrationsView.as_view())

message_list                    = login_required(messages.MessageListView.as_view())
message_detail                  = csrf_exempt(messages.MessageDetailView.as_view())

leader_list                     = leaders.LeaderListView.as_view()

timesheet_list                  = leader_required(timesheets.TimesheetListView.as_view())
timesheet_detail                = leader_required(timesheets.TimesheetDetailView.as_view())
timesheet_submit                = leader_required(timesheets.TimesheetSubmitView.as_view())
timesheetentry_create           = leader_required(timesheets.TimesheetEntryCreateView.as_view())
timesheetentry_update           = leader_required(timesheets.TimesheetEntryUpdateView.as_view())
timesheetentry_delete           = leader_required(timesheets.TimesheetEntryDeleteView.as_view())

school_year                     = schoolyear.SchoolYearView.as_view()

report_list                     = staff_required(reports.ReportsListView.as_view())
report_course_payments          = staff_required(reports_courses.ReportCoursePaymentsView.as_view())
report_course_payments_status   = staff_required(reports_courses.ReportCoursePaymentsStatusView.as_view())
report_course_stats             = staff_required(reports_courses.ReportCourseStatsView.as_view())
report_event_payments           = staff_required(reports_events.ReportEventPaymentsView.as_view())
report_event_payments_status    = staff_required(reports_events.ReportEventPaymentsStatusView.as_view())
report_event_stats              = staff_required(reports_events.ReportEventStatsView.as_view())
report_debtors                  = staff_required(reports_debtors.ReportDebtorsView.as_view())

terms_conditions                = terms_conditions.TermsConditionsView.as_view()
