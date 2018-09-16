from collections import namedtuple
from datetime import date, datetime

from cms.models import CMSPlugin
from django.db import models
from django.utils.formats import date_format, time_format
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from ..conf import settings
from .agegroup import AgeGroup
from .department import Department
from .roles import Leader
from .schoolyear import SchoolYear
from .subjects import (
    Subject, SubjectDiscount, SubjectGroup, SubjectRegistration, SubjectType,
)
from .utils import PaymentStatus


class Event(Subject):
    start_date  = models.DateField(_('start date'))
    end_date    = models.DateField(_('end date'))
    start_time  = models.TimeField(_('start time'), blank=True, null=True)
    end_time    = models.TimeField(_('end time'), blank=True, null=True)

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('-start_date', 'start_time')
        verbose_name        = _('event')
        verbose_name_plural = _('events')

    @property
    def inactive_registrations(self):
        return self.registrations.filter(canceled__isnull=False)

    def get_approved_registrations(self, d):
        return self.registrations.filter(created__lte=d, approved__lte=d).exclude(canceled__lt=d)

    def get_times_list(self):
        return '{start}{separator}{end}'.format(
            start = (date_format(datetime.combine(self.start_date, self.start_time), 'SHORT_DATETIME_FORMAT')
                     if self.start_time else date_format(self.start_date, 'SHORT_DATE_FORMAT')),
            separator = ' - ' if self.start_date != self.end_date or self.end_time is not None else '',
            end = ((time_format(self.end_time, 'TIME_FORMAT') if self.end_time else '')
                   if self.start_date == self.end_date
                   else (date_format(datetime.combine(self.end_date, self.end_time), 'SHORT_DATETIME_FORMAT')
                         if self.end_time else date_format(self.end_date, 'SHORT_DATE_FORMAT'))),
        )
    get_times_list.short_description = _('times')

    def copy_to_school_year(old, school_year):
        new = Event.objects.get(id=old.id)
        new.id, new.pk = None, None
        new.school_year = school_year
        new.public      = False
        new.evaluation  = ''
        new.note        = ''
        year_offset = school_year.year - old.school_year.year
        if new.reg_from:
            try:
                new.reg_from = datetime(
                    new.reg_from.year + year_offset,
                    new.reg_from.month,
                    new.reg_from.day,
                    new.reg_from.hour,
                    new.reg_from.minute,
                    new.reg_from.second,
                )
            except ValueError:
                # handle leap-year
                new.reg_from = datetime(
                    new.reg_from.year + year_offset,
                    new.reg_from.month,
                    new.reg_from.day - 1,
                    new.reg_from.hour,
                    new.reg_from.minute,
                    new.reg_from.second,
                )
        if new.reg_to:
            try:
                new.reg_to = datetime(
                    new.reg_to.year + year_offset,
                    new.reg_to.month,
                    new.reg_to.day,
                    new.reg_to.hour,
                    new.reg_to.minute,
                    new.reg_to.second,
                )
            except ValueError:
                # handle leap-year
                new.reg_to = datetime(
                    new.reg_to.year + year_offset,
                    new.reg_to.month,
                    new.reg_to.day - 1,
                    new.reg_to.hour,
                    new.reg_to.minute,
                    new.reg_to.second,
                )
        try:
            new.start_date = date(new.start_date.year + year_offset, new.start_date.month, new.start_date.day)
        except ValueError:
            # handle leap-year
            new.start_date = date(new.start_date.year + year_offset, new.start_date.month, new.start_date.day - 1)
        try:
            new.end_date   = date(new.end_date.year   + year_offset, new.end_date.month,   new.end_date.day)
        except ValueError:
            # handle leap-year
            new.end_date   = date(new.end_date.year   + year_offset, new.end_date.month,   new.end_date.day - 1)
        new.save()
        new.groups      = old.groups.all()
        new.age_groups  = old.age_groups.all()
        new.leaders     = old.leaders.all()
        new.questions   = old.questions.all()
        new.attachments = old.attachments.all()
        return new



class EventRegistration(SubjectRegistration):

    class Meta:
        app_label           = 'leprikon'
        verbose_name        = _('event registration')
        verbose_name_plural = _('event registrations')

    @cached_property
    def payment_status(self):
        return self.get_payment_status()

    def get_payment_status(self, d=None):
        return PaymentStatus(
            price       = self.price if self.approved and (d is None or d >= self.approved.date()) else 0,
            discount    = self.get_discounted(d),
            paid        = self.get_paid(d),
        )

    @cached_property
    def current_receivable(self):
        d = date.today()
        price = self.price
        discount = self.get_discounted(d)
        paid = self.get_paid(d)
        return max(price - discount - paid, 0)



class EventDiscount(SubjectDiscount):
    registration    = models.ForeignKey(EventRegistration, verbose_name=_('registration'),
                                        related_name='discounts', on_delete=models.PROTECT)



class EventPlugin(CMSPlugin):
    event       = models.ForeignKey(Event, verbose_name=_('event'), related_name='+')
    template    = models.CharField(_('template'), max_length=100,
                                   choices=settings.LEPRIKON_EVENT_TEMPLATES,
                                   default=settings.LEPRIKON_EVENT_TEMPLATES[0][0],
                                   help_text=_('The template used to render plugin.'))

    class Meta:
        app_label = 'leprikon'



class EventListPlugin(CMSPlugin):
    school_year = models.ForeignKey(SchoolYear, verbose_name=_('school year'),
                                    related_name='+', blank=True, null=True)
    departments = models.ManyToManyField(Department, verbose_name=_('departments'), blank=True, related_name='+',
                                         help_text=_('Keep empty to skip searching by departments.'))
    event_types = models.ManyToManyField(SubjectType, verbose_name=_('event types'), blank=True, related_name='+',
                                         limit_choices_to={'subject_type': SubjectType.EVENT},
                                         help_text=_('Keep empty to skip searching by event types.'))
    age_groups  = models.ManyToManyField(AgeGroup, verbose_name=_('age groups'), blank=True, related_name='+',
                                         help_text=_('Keep empty to skip searching by age groups.'))
    groups      = models.ManyToManyField(SubjectGroup, verbose_name=_('event groups'), blank=True, related_name='+',
                                         help_text=_('Keep empty to skip searching by groups.'))
    leaders     = models.ManyToManyField(Leader, verbose_name=_('leaders'), blank=True, related_name='+',
                                         help_text=_('Keep empty to skip searching by leaders.'))
    template    = models.CharField(_('template'), max_length=100,
                                   choices=settings.LEPRIKON_EVENTLIST_TEMPLATES,
                                   default=settings.LEPRIKON_EVENTLIST_TEMPLATES[0][0],
                                   help_text=_('The template used to render plugin.'))

    class Meta:
        app_label = 'leprikon'

    def copy_relations(self, oldinstance):
        self.departments    = oldinstance.departments.all()
        self.event_types    = oldinstance.event_types.all()
        self.groups         = oldinstance.groups.all()
        self.age_groups     = oldinstance.age_groups.all()
        self.leaders        = oldinstance.leaders.all()

    @cached_property
    def all_departments(self):
        return list(self.departments.all())

    @cached_property
    def all_event_types(self):
        return list(self.event_types.all())

    @cached_property
    def all_age_groups(self):
        return list(self.age_groups.all())

    @cached_property
    def all_groups(self):
        return list(self.groups.all())

    @cached_property
    def all_leaders(self):
        return list(self.leaders.all())

    Group = namedtuple('Group', ('group', 'objects'))

    def render(self, context):
        school_year = (self.school_year or getattr(context.get('request'), 'school_year') or
                       SchoolYear.objects.get_current())
        events = Event.objects.filter(school_year=school_year, public=True).distinct()

        if self.all_departments:
            events = events.filter(department__in = self.all_departments)
        if self.all_event_types:
            events = events.filter(subject_type__in = self.all_event_types)
        if self.all_age_groups:
            events = events.filter(age_groups__in = self.all_age_groups)
        if self.all_leaders:
            events = events.filter(leaders__in = self.all_leaders)
        if self.all_groups:
            events = events.filter(groups__in = self.all_groups)
            groups = self.all_groups
        elif self.all_event_types:
            groups = SubjectGroup.objects.filter(subject_types__in = self.all_event_types)
        else:
            groups = SubjectGroup.objects.all()

        context.update({
            'school_year':  school_year,
            'events':       events,
            'groups':       (
                self.Group(group = group, objects = events.filter(groups=group))
                for group in groups
            ),
        })
        return context



class FilteredEventListPlugin(CMSPlugin):
    school_year = models.ForeignKey(SchoolYear, verbose_name=_('school year'),
                                    related_name='+', blank=True, null=True)
    event_types = models.ManyToManyField(SubjectType, verbose_name=_('event types'), related_name='+',
                                         limit_choices_to={'subject_type': SubjectType.EVENT})

    class Meta:
        app_label = 'leprikon'

    def copy_relations(self, oldinstance):
        self.event_types = oldinstance.event_types.all()

    @cached_property
    def all_event_types(self):
        return list(self.event_types.all())

    def render(self, context):
        school_year = (self.school_year or getattr(context.get('request'), 'school_year') or
                       SchoolYear.objects.get_current())

        from ..forms.subjects import SubjectFilterForm
        form = SubjectFilterForm(
            subject_type_type = SubjectType.EVENT,
            subject_types = self.all_event_types,
            school_year = school_year,
            is_staff = context['request'].user.is_staff,
            data=context['request'].GET,
        )
        context.update({
            'school_year':  school_year,
            'form':         form,
            'events':      form.get_queryset(),
        })
        return context
