from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.auth import get_user_model

from ..models.agegroup import AgeGroup
from ..models.clubs import (
    Club, ClubGroup, ClubJournalEntry, ClubJournalLeaderEntry, ClubPayment,
    ClubRegistration, ClubRegistrationRequest, ClubType,
)
from ..models.events import (
    Event, EventGroup, EventPayment, EventRegistration,
    EventRegistrationRequest, EventType,
)
from ..models.insurance import Insurance
from ..models.messages import Message, MessageRecipient
from ..models.place import Place
from ..models.question import Question
from ..models.roles import Leader, Parent, Participant
from ..models.school import School
from ..models.schoolyear import SchoolYear
from ..models.timesheets import Timesheet, TimesheetEntry, TimesheetEntryType
from .agegroup import AgeGroupAdmin
from .clubs import (
    ClubAdmin, ClubGroupAdmin, ClubJournalEntryAdmin,
    ClubJournalLeaderEntryAdmin, ClubPaymentAdmin, ClubRegistrationAdmin,
    ClubRegistrationRequestAdmin, ClubTypeAdmin,
)
from .events import (
    EventAdmin, EventGroupAdmin, EventPaymentAdmin, EventRegistrationAdmin,
    EventRegistrationRequestAdmin, EventTypeAdmin,
)
from .insurance import InsuranceAdmin
from .messages import MessageAdmin, MessageRecipientAdmin
from .place import PlaceAdmin
from .question import QuestionAdmin
from .roles import LeaderAdmin, ParentAdmin, ParticipantAdmin
from .school import SchoolAdmin
from .schoolyear import SchoolYearAdmin
from .timesheets import (
    TimesheetAdmin, TimesheetEntryAdmin, TimesheetEntryTypeAdmin,
)
from .user import UserAdmin

User = get_user_model()

admin.site.register(AgeGroup,           AgeGroupAdmin)
admin.site.register(Insurance,          InsuranceAdmin)
admin.site.register(Place,              PlaceAdmin)
admin.site.register(School,             SchoolAdmin)
admin.site.register(SchoolYear,         SchoolYearAdmin)

admin.site.register(Leader,             LeaderAdmin)
admin.site.register(Parent,             ParentAdmin)
admin.site.register(Participant,        ParticipantAdmin)

admin.site.register(ClubType,           ClubTypeAdmin)
admin.site.register(ClubGroup,          ClubGroupAdmin)
admin.site.register(Club,               ClubAdmin)
admin.site.register(ClubRegistration,   ClubRegistrationAdmin)
admin.site.register(ClubRegistrationRequest, ClubRegistrationRequestAdmin)
admin.site.register(ClubPayment,        ClubPaymentAdmin)
admin.site.register(ClubJournalEntry,   ClubJournalEntryAdmin)
admin.site.register(ClubJournalLeaderEntry, ClubJournalLeaderEntryAdmin)

admin.site.register(EventType,          EventTypeAdmin)
admin.site.register(EventGroup,         EventGroupAdmin)
admin.site.register(Event,              EventAdmin)
admin.site.register(EventRegistration,  EventRegistrationAdmin)
admin.site.register(EventRegistrationRequest, EventRegistrationRequestAdmin)
admin.site.register(EventPayment,       EventPaymentAdmin)

admin.site.register(Message,            MessageAdmin)
admin.site.register(MessageRecipient,   MessageRecipientAdmin)

admin.site.register(Question,           QuestionAdmin)

admin.site.register(Timesheet,          TimesheetAdmin)
admin.site.register(TimesheetEntry,     TimesheetEntryAdmin)
admin.site.register(TimesheetEntryType, TimesheetEntryTypeAdmin)

admin.site.unregister(User)
admin.site.register(User,               UserAdmin)

