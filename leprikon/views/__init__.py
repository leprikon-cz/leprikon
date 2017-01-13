from __future__ import unicode_literals

from django.contrib.auth.decorators import user_passes_test
from django.core.urlresolvers import reverse_lazy as reverse
from django.views.decorators.csrf import csrf_exempt

from . import (
    courses, events, leaders, messages, parents, participants, registrations,
    reports, schoolyear, summary, support, terms_conditions, timesheets, user,
)
from ..conf import settings
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


summary                         = login_required(summary.SummaryView.as_view())

user_create                     =    user.UserCreateView.as_view()
user_update                     = login_required(user.UserUpdateView.as_view())
user_login                      = user.user_login
user_logout                     = user.user_logout
user_password                   = user.user_password
password_reset                  = user.password_reset
password_reset_done             = user.password_reset_done
password_reset_confirm          = user.password_reset_confirm
password_reset_complete         = user.password_reset_complete

registration_list               = login_required(registrations.RegistrationsListView.as_view())

participant_list                = login_required(participants.ParticipantListView.as_view())
participant_create              = login_required(participants.ParticipantCreateView.as_view())
participant_update              = login_required(participants.ParticipantUpdateView.as_view())

parent_create                   = login_required(parents.ParentCreateView.as_view())
parent_update                   = login_required(parents.ParentUpdateView.as_view())

course_list                     = courses.CourseListView.as_view()
course_list_mine                = leader_required(courses.CourseListMineView.as_view())
course_alternating              = leader_required(courses.CourseAlternatingView.as_view())
course_detail                   = courses.CourseDetailView.as_view()
course_registrations            = leader_or_staff_required(courses.CourseRegistrationsView.as_view())
course_journal                  = leader_or_staff_required(courses.CourseJournalView.as_view())
course_update                   = leader_or_staff_required(courses.CourseUpdateView.as_view())
coursejournalentry_create       = leader_or_staff_required(courses.CourseJournalEntryCreateView.as_view())
coursejournalentry_update       = leader_or_staff_required(courses.CourseJournalEntryUpdateView.as_view())
coursejournalentry_delete       = leader_or_staff_required(courses.CourseJournalEntryDeleteView.as_view())
coursejournalleaderentry_update = leader_or_staff_required(courses.CourseJournalLeaderEntryUpdateView.as_view())
coursejournalleaderentry_delete = leader_or_staff_required(courses.CourseJournalLeaderEntryDeleteView.as_view())
course_registration_form        = login_required(courses.CourseRegistrationFormView.as_view())
course_registration_confirm     = login_required(courses.CourseRegistrationConfirmView.as_view())
course_registration_pdf         = login_required(courses.CourseRegistrationPdfView.as_view())
course_registration_cancel      = login_required(courses.CourseRegistrationCancelView.as_view())

event_list                      = events.EventListView.as_view()
event_list_mine                 = leader_required(events.EventListMineView.as_view())
event_detail                    = events.EventDetailView.as_view()
event_registrations             = leader_or_staff_required(events.EventRegistrationsView.as_view())
event_update                    = leader_or_staff_required(events.EventUpdateView.as_view())
event_registration_form         = login_required(events.EventRegistrationFormView.as_view())
event_registration_confirm      = login_required(events.EventRegistrationConfirmView.as_view())
event_registration_pdf          = login_required(events.EventRegistrationPdfView.as_view())
event_registration_cancel       = login_required(events.EventRegistrationCancelView.as_view())

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
support                         = login_required(support.SupportView.as_view())

report_list                     = staff_required(reports.ReportsListView.as_view())
report_course_payments          = staff_required(reports_courses.ReportCoursePaymentsView.as_view())
report_course_payments_status   = staff_required(reports_courses.ReportCoursePaymentsStatusView.as_view())
report_course_stats             = staff_required(reports_courses.ReportCourseStatsView.as_view())
report_event_payments           = staff_required(reports_events.ReportEventPaymentsView.as_view())
report_event_payments_status    = staff_required(reports_events.ReportEventPaymentsStatusView.as_view())
report_debtors                  = staff_required(reports_debtors.ReportDebtorsView.as_view())

terms_conditions                = terms_conditions.TermsConditionsView.as_view()
