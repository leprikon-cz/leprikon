import locale

import icu
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.http import Http404
from django.template.response import TemplateResponse
from django.utils.translation import ugettext_lazy as _

from ..models.account import AccountClosure
from ..models.agegroup import AgeGroup
from ..models.agreements import Agreement
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
from .account import AccountClosureAdmin
from .agegroup import AgeGroupAdmin
from .agreements import AgreementAdmin
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

admin.site.register(AccountClosure,             AccountClosureAdmin)

admin.site.register(AgeGroup,                   AgeGroupAdmin)
admin.site.register(Agreement,                  AgreementAdmin)
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


def app_index(self, request, app_label, extra_context=None):
    app_dict = self._build_app_dict(request, app_label)
    if not app_dict:
        raise Http404('The requested admin page does not exist.')
    # Sort the models alphabetically within each app.
    collator = icu.Collator.createInstance(icu.Locale('.'.join(locale.getlocale())))
    app_dict['models'].sort(key=lambda x: collator.getSortKey(x['name'].lower()))
    context = dict(
        self.each_context(request),
        title=_('Leprikon administration'),
        app_list=[app_dict],
        app_label=app_label,
    )
    context.update(extra_context or {})

    request.current_app = self.name

    return TemplateResponse(request, self.app_index_template or [
        'admin/%s/app_index.html' % app_label,
        'admin/app_index.html'
    ], context)


def get_app_list(self, request):
    """
    Returns a sorted list of all the installed apps that have been
    registered in this site.
    """
    collator = icu.Collator.createInstance(icu.Locale('.'.join(locale.getlocale())))

    app_dict = self._build_app_dict(request)

    # Sort the apps alphabetically.
    app_list = sorted(app_dict.values(), key=lambda x: collator.getSortKey(x['name'].lower()))

    # Sort the models alphabetically within each app.
    for app in app_list:
        app['models'].sort(key=lambda x: collator.getSortKey(x['name'].lower()))

    return app_list


# override default Admin site's app_index and get_app_list
admin.sites.AdminSite.app_index = app_index
admin.sites.AdminSite.get_app_list = get_app_list
