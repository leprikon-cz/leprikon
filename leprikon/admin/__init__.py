from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.contrib import admin
from django.contrib.auth import get_user_model

from .place import PlaceAdmin
from .school import SchoolAdmin
from .schoolyear import SchoolYearAdmin
from .agegroup import AgeGroupAdmin
from .roles import LeaderAdmin, ParentAdmin, ParticipantAdmin
from .clubs import ClubAdmin, ClubGroupAdmin, ClubRegistrationAdmin, ClubPaymentAdmin, ClubJournalEntryAdmin, ClubJournalLeaderEntryAdmin
from .events import EventAdmin, EventTypeAdmin, EventGroupAdmin, EventRegistrationAdmin, EventPaymentAdmin
from .question import QuestionAdmin
from .user import UserAdmin
from .timesheets import TimesheetAdmin, TimesheetEntryAdmin, TimesheetEntryTypeAdmin

from ..models import *
User = get_user_model()

admin.site.register(AgeGroup,           AgeGroupAdmin)
admin.site.register(Place,              PlaceAdmin)
admin.site.register(School,             SchoolAdmin)
admin.site.register(SchoolYear,         SchoolYearAdmin)

admin.site.register(Leader,             LeaderAdmin)
admin.site.register(Parent,             ParentAdmin)
admin.site.register(Participant,        ParticipantAdmin)

admin.site.register(ClubGroup,          ClubGroupAdmin)
admin.site.register(Club,               ClubAdmin)
admin.site.register(ClubRegistration,   ClubRegistrationAdmin)
admin.site.register(ClubPayment,        ClubPaymentAdmin)
admin.site.register(ClubJournalEntry,   ClubJournalEntryAdmin)
admin.site.register(ClubJournalLeaderEntry, ClubJournalLeaderEntryAdmin)

admin.site.register(EventType,          EventTypeAdmin)
admin.site.register(EventGroup,         EventGroupAdmin)
admin.site.register(Event,              EventAdmin)
admin.site.register(EventRegistration,  EventRegistrationAdmin)
admin.site.register(EventPayment,       EventPaymentAdmin)

admin.site.register(Question,           QuestionAdmin)

admin.site.register(Timesheet,          TimesheetAdmin)
admin.site.register(TimesheetEntry,     TimesheetEntryAdmin)
admin.site.register(TimesheetEntryType, TimesheetEntryTypeAdmin)

admin.site.unregister(User)
admin.site.register(User,               UserAdmin)

