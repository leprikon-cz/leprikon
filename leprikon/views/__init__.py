from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.contrib.auth.decorators import user_passes_test
from django.core.urlresolvers import reverse_lazy as reverse
from django.utils.decorators import available_attrs
from django.views.decorators.csrf import csrf_exempt
from functools import wraps

from ..conf import settings

from .summary import *
from .user import *
from .participants import *
from .parents import *
from .clubs import *
from .events import *
from .leaders import *
from .messages import *
from .timesheets import *
from .schoolyear import *
from .support import *
from .registrations import *
from .reports import *
from .reports.clubs import *
from .reports.events import *
from .reports.debtors import *
from .terms_conditions import *

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


summary                         = login_required(SummaryView.as_view())

user_create                     =    UserCreateView.as_view()
user_update                     = login_required(UserUpdateView.as_view())

registrations                   = login_required(RegistrationsView.as_view())

participant_list                = login_required(ParticipantListView.as_view())
participant_create              = login_required(ParticipantCreateView.as_view())
participant_update              = login_required(ParticipantUpdateView.as_view())

parent_create                   = login_required(ParentCreateView.as_view())
parent_update                   = login_required(ParentUpdateView.as_view())

club_list                       = ClubListView.as_view()
club_list_mine                  = leader_required(ClubListMineView.as_view())
club_alternating                = leader_required(ClubAlternatingView.as_view())
club_detail                     = ClubDetailView.as_view()
club_registrations              = leader_or_staff_required(ClubRegistrationsView.as_view())
club_journal                    = leader_or_staff_required(ClubJournalView.as_view())
club_update                     = leader_or_staff_required(ClubUpdateView.as_view())
clubjournalentry_create         = leader_or_staff_required(ClubJournalEntryCreateView.as_view())
clubjournalentry_update         = leader_or_staff_required(ClubJournalEntryUpdateView.as_view())
clubjournalentry_delete         = leader_or_staff_required(ClubJournalEntryDeleteView.as_view())
clubjournalleaderentry_update   = leader_or_staff_required(ClubJournalLeaderEntryUpdateView.as_view())
clubjournalleaderentry_delete   = leader_or_staff_required(ClubJournalLeaderEntryDeleteView.as_view())
club_registration_form          = login_required(ClubRegistrationFormView.as_view())
club_registration_confirm       = login_required(ClubRegistrationConfirmView.as_view())
club_registration_pdf           = login_required(ClubRegistrationPdfView.as_view())
club_registration_cancel        = login_required(ClubRegistrationCancelView.as_view())

event_list                      = EventListView.as_view()
event_list_mine                 = leader_required(EventListMineView.as_view())
event_detail                    = EventDetailView.as_view()
event_detail_redirect           = EventDetailRedirectView.as_view()
event_registrations             = leader_or_staff_required(EventRegistrationsView.as_view())
event_update                    = leader_or_staff_required(EventUpdateView.as_view())
event_registration_form         = login_required(EventRegistrationFormView.as_view())
event_registration_confirm      = login_required(EventRegistrationConfirmView.as_view())
event_registration_pdf          = login_required(EventRegistrationPdfView.as_view())
event_registration_cancel       = login_required(EventRegistrationCancelView.as_view())

message_list                    = login_required(MessageListView.as_view())
message_detail                  = csrf_exempt(MessageDetailView.as_view())

leader_list                     = LeaderListView.as_view()

timesheet_list                  = leader_required(TimesheetListView.as_view())
timesheet_detail                = leader_required(TimesheetDetailView.as_view())
timesheet_submit                = leader_required(TimesheetSubmitView.as_view())
timesheetentry_create           = leader_required(TimesheetEntryCreateView.as_view())
timesheetentry_update           = leader_required(TimesheetEntryUpdateView.as_view())
timesheetentry_delete           = leader_required(TimesheetEntryDeleteView.as_view())

school_year                     = SchoolYearView.as_view()
support                         = login_required(SupportView.as_view())

reports                         = staff_required(ReportsView.as_view())
report_club_payments            = staff_required(ReportClubPaymentsView.as_view())
report_club_payments_status     = staff_required(ReportClubPaymentsStatusView.as_view())
report_club_stats               = staff_required(ReportClubStatsView.as_view())
report_event_payments           = staff_required(ReportEventPaymentsView.as_view())
report_event_payments_status    = staff_required(ReportEventPaymentsStatusView.as_view())
report_debtors                  = staff_required(ReportDebtorsView.as_view())

terms_conditions                = TermsConditionsView.as_view()
