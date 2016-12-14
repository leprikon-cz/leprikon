from __future__ import unicode_literals

from django.contrib.auth.decorators import user_passes_test
from django.core.urlresolvers import reverse_lazy as reverse
from django.views.decorators.csrf import csrf_exempt

from . import (
    clubs, events, leaders, messages, parents, participants, registrations,
    schoolyear, summary, support, terms_conditions, timesheets, user,
)
from ..conf import settings
from .reports import (
    clubs as reports_clubs, debtors as reports_debtors,
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

club_list                       = clubs.ClubListView.as_view()
club_list_mine                  = leader_required(clubs.ClubListMineView.as_view())
club_alternating                = leader_required(clubs.ClubAlternatingView.as_view())
club_detail                     = clubs.ClubDetailView.as_view()
club_registrations              = leader_or_staff_required(clubs.ClubRegistrationsView.as_view())
club_journal                    = leader_or_staff_required(clubs.ClubJournalView.as_view())
club_update                     = leader_or_staff_required(clubs.ClubUpdateView.as_view())
clubjournalentry_create         = leader_or_staff_required(clubs.ClubJournalEntryCreateView.as_view())
clubjournalentry_update         = leader_or_staff_required(clubs.ClubJournalEntryUpdateView.as_view())
clubjournalentry_delete         = leader_or_staff_required(clubs.ClubJournalEntryDeleteView.as_view())
clubjournalleaderentry_update   = leader_or_staff_required(clubs.ClubJournalLeaderEntryUpdateView.as_view())
clubjournalleaderentry_delete   = leader_or_staff_required(clubs.ClubJournalLeaderEntryDeleteView.as_view())
club_registration_form          = login_required(clubs.ClubRegistrationFormView.as_view())
club_registration_confirm       = login_required(clubs.ClubRegistrationConfirmView.as_view())
club_registration_pdf           = login_required(clubs.ClubRegistrationPdfView.as_view())
club_registration_cancel        = login_required(clubs.ClubRegistrationCancelView.as_view())

event_list                      = events.EventListView.as_view()
event_list_mine                 = leader_required(events.EventListMineView.as_view())
event_detail                    = events.EventDetailView.as_view()
event_detail_redirect           = events.EventDetailRedirectView.as_view()
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
report_club_payments            = staff_required(reports_clubs.ReportClubPaymentsView.as_view())
report_club_payments_status     = staff_required(reports_clubs.ReportClubPaymentsStatusView.as_view())
report_club_stats               = staff_required(reports_clubs.ReportClubStatsView.as_view())
report_event_payments           = staff_required(reports_events.ReportEventPaymentsView.as_view())
report_event_payments_status    = staff_required(reports_events.ReportEventPaymentsStatusView.as_view())
report_debtors                  = staff_required(reports_debtors.ReportDebtorsView.as_view())

terms_conditions                = terms_conditions.TermsConditionsView.as_view()
