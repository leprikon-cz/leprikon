from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _

from ..models.agegroup import AgeGroup
from ..models.citizenship import Citizenship
from ..models.courses import (
    Course, CourseDiscount, CourseJournalEntry, CourseJournalLeaderEntry,
    CourseRegistration,
)
from ..models.department import Department
from ..models.events import Event, EventDiscount, EventRegistration
from ..models.leprikonsite import LeprikonSite
from ..models.messages import Message, MessageRecipient
from ..models.place import Place
from ..models.printsetup import PrintSetup
from ..models.question import Question
from ..models.roles import Leader, Parent, Participant
from ..models.school import School
from ..models.schoolyear import SchoolYear, SchoolYearDivision
from ..models.subjects import (
    Subject, SubjectGroup, SubjectPayment, SubjectRegistration, SubjectType,
)
from ..models.timesheets import Timesheet, TimesheetEntry, TimesheetEntryType
from .agegroup import AgeGroupAdmin
from .citizenship import CitizenshipAdmin
from .courses import (
    CourseAdmin, CourseDiscountAdmin, CourseJournalEntryAdmin,
    CourseJournalLeaderEntryAdmin, CourseRegistrationAdmin,
)
from .department import DepartmentAdmin
from .events import EventAdmin, EventDiscountAdmin, EventRegistrationAdmin
from .leprikonsite import LeprikonSiteAdmin
from .messages import MessageAdmin, MessageRecipientAdmin
from .place import PlaceAdmin
from .printsetup import PrintSetupAdmin
from .question import QuestionAdmin
from .roles import LeaderAdmin, ParentAdmin, ParticipantAdmin
from .school import SchoolAdmin
from .schoolyear import SchoolYearAdmin, SchoolYearDivisionAdmin
from .subjects import (
    SubjectAdmin, SubjectGroupAdmin, SubjectPaymentAdmin,
    SubjectRegistrationAdmin, SubjectTypeAdmin,
)
from .timesheets import (
    TimesheetAdmin, TimesheetEntryAdmin, TimesheetEntryTypeAdmin,
)
from .user import UserAdmin

User = get_user_model()

admin.site.site_header = _('Leprikon administration')
admin.site.site_title = _('Leprikon administration')

admin.site.register(AgeGroup,                   AgeGroupAdmin)
admin.site.register(Citizenship,                CitizenshipAdmin)
admin.site.register(LeprikonSite,               LeprikonSiteAdmin)
admin.site.register(Place,                      PlaceAdmin)
admin.site.register(PrintSetup,                 PrintSetupAdmin)
admin.site.register(School,                     SchoolAdmin)
admin.site.register(SchoolYear,                 SchoolYearAdmin)
admin.site.register(SchoolYearDivision,         SchoolYearDivisionAdmin)

admin.site.register(Leader,                     LeaderAdmin)
admin.site.register(Parent,                     ParentAdmin)
admin.site.register(Participant,                ParticipantAdmin)

admin.site.register(Subject,                    SubjectAdmin)
admin.site.register(SubjectType,                SubjectTypeAdmin)
admin.site.register(SubjectGroup,               SubjectGroupAdmin)
admin.site.register(SubjectRegistration,        SubjectRegistrationAdmin)
admin.site.register(SubjectPayment,             SubjectPaymentAdmin)

admin.site.register(Course,                     CourseAdmin)
admin.site.register(CourseRegistration,         CourseRegistrationAdmin)
admin.site.register(CourseDiscount,             CourseDiscountAdmin)
admin.site.register(CourseJournalEntry,         CourseJournalEntryAdmin)
admin.site.register(CourseJournalLeaderEntry,   CourseJournalLeaderEntryAdmin)

admin.site.register(Department,                 DepartmentAdmin)

admin.site.register(Event,                      EventAdmin)
admin.site.register(EventRegistration,          EventRegistrationAdmin)
admin.site.register(EventDiscount,              EventDiscountAdmin)

admin.site.register(Message,                    MessageAdmin)
admin.site.register(MessageRecipient,           MessageRecipientAdmin)

admin.site.register(Question,                   QuestionAdmin)

admin.site.register(Timesheet,                  TimesheetAdmin)
admin.site.register(TimesheetEntry,             TimesheetEntryAdmin)
admin.site.register(TimesheetEntryType,         TimesheetEntryTypeAdmin)

admin.site.unregister(User)
admin.site.register(User,                       UserAdmin)
