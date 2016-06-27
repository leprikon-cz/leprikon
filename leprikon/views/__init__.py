from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.contrib.auth.decorators import login_required
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
from .terms_conditions import *

def lr(function):
    from django.core.urlresolvers import reverse_lazy as reverse
    return login_required(function,
        login_url=reverse('leprikon:user_login'),
        redirect_field_name=settings.LEPRIKON_PARAM_BACK,
    )

def leader_required(view):
    @wraps(view, assigned=available_attrs(view))
    def wrapped_view(request, *args, **kwargs):
        if request.leader:
            return view(request, *args, **kwargs)
        else:
            from django.http import Http404
            raise Http404()
    return wrapped_view

def staff_required(view):
    @wraps(view, assigned=available_attrs(view))
    def wrapped_view(request, *args, **kwargs):
        if request.user.is_staff:
            return view(request, *args, **kwargs)
        else:
            from django.http import Http404
            raise Http404()
    return wrapped_view


summary                         = lr(SummaryView.as_view())

user_create                     =    UserCreateView.as_view()
user_update                     = lr(UserUpdateView.as_view())

registrations                   = lr(RegistrationsView.as_view())

participant_list                = lr(ParticipantListView.as_view())
participant_create              = lr(ParticipantCreateView.as_view())
participant_update              = lr(ParticipantUpdateView.as_view())

parent_create                   = lr(ParentCreateView.as_view())
parent_update                   = lr(ParentUpdateView.as_view())

club_list                       = ClubListView.as_view()
club_list_mine                  = leader_required(ClubListMineView.as_view())
club_alternating                = leader_required(ClubAlternatingView.as_view())
club_detail                     = ClubDetailView.as_view()
club_participants               = lr(ClubParticipantsView.as_view())
club_journal                    = lr(ClubJournalView.as_view())
club_update                     = lr(ClubUpdateView.as_view())
clubjournalentry_create         = lr(ClubJournalEntryCreateView.as_view())
clubjournalentry_update         = lr(ClubJournalEntryUpdateView.as_view())
clubjournalentry_delete         = lr(ClubJournalEntryDeleteView.as_view())
clubjournalleaderentry_update   = lr(ClubJournalLeaderEntryUpdateView.as_view())
clubjournalleaderentry_delete   = lr(ClubJournalLeaderEntryDeleteView.as_view())
club_registration_form          = ClubRegistrationFormView.as_view()
club_registration_confirm       = lr(ClubRegistrationConfirmView.as_view())
club_registration_pdf           = lr(ClubRegistrationPdfView.as_view())
club_registration_cancel        = lr(ClubRegistrationCancelView.as_view())

event_list                      = EventListView.as_view()
event_list_mine                 = leader_required(EventListMineView.as_view())
event_detail                    = EventDetailView.as_view()
event_detail_redirect           = EventDetailRedirectView.as_view()
event_participants              = lr(EventParticipantsView.as_view())
event_update                    = lr(EventUpdateView.as_view())
event_registration_form         = EventRegistrationFormView.as_view()
event_registration_confirm      = lr(EventRegistrationConfirmView.as_view())
event_registration_pdf          = lr(EventRegistrationPdfView.as_view())
event_registration_cancel       = lr(EventRegistrationCancelView.as_view())

message_list                    = lr(MessageListView.as_view())
message_detail                  = csrf_exempt(MessageDetailView.as_view())

leader_list                     = LeaderListView.as_view()

timesheet_list                  = leader_required(TimesheetListView.as_view())
timesheet_detail                = leader_required(TimesheetDetailView.as_view())
timesheet_submit                = leader_required(TimesheetSubmitView.as_view())
timesheetentry_create           = leader_required(TimesheetEntryCreateView.as_view())
timesheetentry_update           = leader_required(TimesheetEntryUpdateView.as_view())
timesheetentry_delete           = leader_required(TimesheetEntryDeleteView.as_view())

school_year                     = SchoolYearView.as_view()
support                         = lr(SupportView.as_view())

reports                         = staff_required(ReportsView.as_view())
report_club_payments            = staff_required(ReportClubPaymentsView.as_view())
report_club_payments_status     = staff_required(ReportClubPaymentsStatusView.as_view())
report_event_payments           = staff_required(ReportEventPaymentsView.as_view())
report_event_payments_status    = staff_required(ReportEventPaymentsStatusView.as_view())

terms_conditions                = TermsConditionsView.as_view()
