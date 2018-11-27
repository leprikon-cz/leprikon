from collections import namedtuple
from datetime import date, datetime, timedelta

from cms.models import CMSPlugin
from django.core.urlresolvers import reverse_lazy as reverse
from django.db import models
from django.dispatch import receiver
from django.utils.encoding import force_text, python_2_unicode_compatible
from django.utils.formats import date_format
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from djangocms_text_ckeditor.fields import HTMLField

from ..conf import settings
from ..utils import comma_separated
from .agegroup import AgeGroup
from .department import Department
from .fields import DAY_OF_WEEK, DayOfWeekField
from .roles import Leader
from .schoolyear import SchoolYear, SchoolYearDivision, SchoolYearPeriod
from .startend import StartEndMixin
from .subjects import (
    Subject, SubjectDiscount, SubjectGroup, SubjectRegistration, SubjectType,
)
from .utils import PaymentStatus


class Course(Subject):
    school_year_division = models.ForeignKey(SchoolYearDivision, verbose_name=_('school year division'),
                                             related_name='courses')

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('code', 'name')
        verbose_name        = _('course')
        verbose_name_plural = _('courses')

    @cached_property
    def all_times(self):
        return list(self.times.all())

    @cached_property
    def all_periods(self):
        return list(self.school_year_division.periods.all())

    @cached_property
    def all_journal_periods(self):
        return list(CourseJournalPeriod(self, period) for period in self.all_periods)

    @cached_property
    def all_journal_entries(self):
        return list(self.journal_entries.all())

    @cached_property
    def has_discounts(self):
        return CourseDiscount.objects.filter(registration__subject_id=self.id).exists()

    def get_current_period(self):
        return (
            self.school_year_division.periods.filter(end__gte=date.today()).first() or
            self.school_year_division.periods.last()
        )

    def get_times_list(self):
        return comma_separated(self.all_times)
    get_times_list.short_description = _('times')

    def get_next_time(self, now = None):
        try:
            return min(t.get_next_time(now) for t in self.all_times)
        except ValueError:
            return None

    @property
    def registrations_history_registrations(self):
        return CourseRegistration.objects.filter(course_history__course=self).distinct()

    @property
    def inactive_registrations(self):
        return (CourseRegistration.objects.filter(course_history__course=self)
                .exclude(id__in=self.active_registrations.all()).distinct())

    def get_approved_registrations(self, d):
        ids = list(
            CourseRegistrationHistory.objects
            .filter(course=self, start__lte=d)
            .exclude(end__lt=d)
            .values_list('registration_id', flat=True)
        )
        return CourseRegistration.objects.filter(id__in=ids, approved__lte=d).exclude(canceled__lt=d).distinct()

    def copy_to_school_year(old, school_year):
        new = Course.objects.get(id=old.id)
        new.id, new.pk = None, None
        new.school_year = school_year
        new.public      = False
        new.evaluation  = ''
        new.note        = ''
        try:
            new.school_year_division = SchoolYearDivision.objects.get(
                school_year=school_year,
                name=old.school_year_division.name,
            )
        except:
            new.school_year_division = old.school_year_division.copy_to_school_year(school_year)
        new.save()
        new.groups      = old.groups.all()
        new.age_groups  = old.age_groups.all()
        new.leaders     = old.leaders.all()
        new.questions   = old.questions.all()
        new.times       = old.times.all()
        new.attachments = old.attachments.all()
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
        return new



class CourseJournalPeriod:

    def __init__(self, course, period):
        self.course = course
        self.period = period

    @property
    def journal_entries(self):
        return self.course.journal_entries.filter(date__gte=self.period.start, date__lte=self.period.end)

    @cached_property
    def all_journal_entries(self):
        return list(self.journal_entries.all())

    @cached_property
    def all_registrations(self):
        return list(self.course.registrations_history_registrations.filter(created__lt=self.period.end))

    @cached_property
    def all_alternates(self):
        alternates = set()
        for entry in self.all_journal_entries:
            for alternate in entry.all_alternates:
                alternates.add(alternate)
        return list(alternates)

    PresenceRecord = namedtuple('PresenceRecord', ('name', 'presences'))

    def get_participant_presences(self):
        return [
            self.PresenceRecord(
                reg.participant,
                [
                    reg in entry.all_registrations
                    for entry in self.all_journal_entries
                ]
            ) for reg in self.all_registrations
        ]

    def get_leader_presences(self):
        return [
            self.PresenceRecord(
                leader,
                [
                    entry.all_leader_entries_by_leader.get(leader, None)
                    for entry in self.all_journal_entries
                ]
            ) for leader in self.course.all_leaders
        ]

    def get_alternate_presences(self):
        return [
            self.PresenceRecord(
                alternate,
                [
                    entry.all_leader_entries_by_leader.get(alternate, None)
                    for entry in self.all_journal_entries
                ]
            ) for alternate in self.all_alternates
        ]




@python_2_unicode_compatible
class CourseTime(StartEndMixin, models.Model):
    course      = models.ForeignKey(Course, verbose_name=_('course'), related_name='times')
    day_of_week = DayOfWeekField(_('day of week'))
    start       = models.TimeField(_('start time'), blank=True, null=True)
    end         = models.TimeField(_('end time'), blank=True, null=True)

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('day_of_week', 'start')
        verbose_name        = _('time')
        verbose_name_plural = _('times')

    def __str__(self):
        if self.start is not None and self.end is not None:
            return _('{day}, {start:%H:%M} - {end:%H:%M}').format(
                day     = self.day,
                start   = self.start,
                end     = self.end,
            )
        elif self.start is not None:
            return _('{day}, {start:%H:%M}').format(
                day     = self.day,
                start   = self.start,
            )
        else:
            return force_text(self.day)

    @cached_property
    def day(self):
        return DAY_OF_WEEK[self.day_of_week]

    Time = namedtuple('Time', ('date', 'start', 'end'))

    def get_next_time(self, now = None):
        now = now or datetime.now()
        daydelta = (self.day_of_week - now.isoweekday()) % 7
        if daydelta == 0 and (isinstance(now, date) or self.start is None or self.start <= now.time()):
            daydelta = 7
        if isinstance(now, datetime):
            next_date = now.date() + timedelta(daydelta)
        else:
            next_date = now + timedelta(daydelta)
        return self.Time(
            date    = next_date,
            start   = self.start,
            end     = self.end,
        )



class CourseRegistration(SubjectRegistration):
    subject_type = SubjectType.COURSE

    class Meta:
        app_label           = 'leprikon'
        verbose_name        = _('course registration')
        verbose_name_plural = _('course registrations')

    @property
    def periods(self):
        periods = self.subject.course.school_year_division.periods
        if self.canceled:
            return periods.filter(end__gt=self.created, start__lt=self.canceled)
        else:
            return periods.filter(end__gt=self.created)

    @cached_property
    def all_periods(self):
        return list(self.periods.all())

    @cached_property
    def all_discounts(self):
        return list(self.discounts.all())

    PeriodPaymentStatus = namedtuple('PeriodPaymentStatus', ('period', 'status'))

    def get_period_payment_statuses(self, d=None):
        paid = self.get_paid(d)
        for counter, period in enumerate(self.all_periods, start=1):
            discount = sum(
                discount.amount
                for discount in self.all_discounts
                if discount.period == period and (d is None or discount.accounted <= d)
            )
            yield self.PeriodPaymentStatus(
                period  = period,
                status  = PaymentStatus(
                    price       = self.price,
                    discount    = discount,
                    paid        = min(self.price - discount, paid) if counter < len(self.all_periods) else paid,
                ),
            )
            paid = max(paid - (self.price - discount), 0)

    @cached_property
    def payment_statuses(self):
        return self.get_payment_statuses()

    PaymentStatuses = namedtuple('PaymentStatuses', ('partial', 'total'))

    def get_payment_statuses(self, d=None):
        if d is None:
            d = date.today()
        if self.approved:
            if self.approved.date() <= d:
                partial_price = self.price * (len(tuple(p for p in self.all_periods if p.start <= d)) or 1)
            else:
                partial_price = 0
            total_price = self.price * len(self.all_periods)
        else:
            partial_price = 0
            total_price = 0
        discounted  = self.get_discounted(d)
        partial_discounted  = self.get_partial_discounted(d)
        paid        = self.get_paid(d)
        return self.PaymentStatuses(
            partial = PaymentStatus(price=partial_price, discount=partial_discounted, paid=paid),
            total   = PaymentStatus(price=total_price, discount=discounted, paid=paid),
        )

    def get_partial_discounted(self, d=None):
        if d is None:
            d = date.today()
        return sum(p.amount for p in self.get_discounts(d) if p.period.start <= d)

    @cached_property
    def current_receivable(self):
        d = date.today()
        price = self.price * (len(tuple(p for p in self.all_periods if p.start <= d)) or 1)
        discount = self.get_discounted(d)
        paid = self.get_paid(d)
        return max(price - discount - paid, 0)



class CourseDiscount(SubjectDiscount):
    registration    = models.ForeignKey(CourseRegistration, verbose_name=_('registration'),
                                        related_name='discounts', on_delete=models.PROTECT)
    period          = models.ForeignKey(SchoolYearPeriod, verbose_name=_('period'),
                                        related_name='discounts', on_delete=models.PROTECT)



@python_2_unicode_compatible
class CourseRegistrationHistory(StartEndMixin, models.Model):
    registration = models.ForeignKey(CourseRegistration, verbose_name=_('course'), editable=False,
                                     related_name='course_history', on_delete=models.PROTECT)
    course = models.ForeignKey(Course, verbose_name=_('course'), editable=False,
                               related_name='registrations_history', on_delete=models.PROTECT)
    start = models.DateField()
    end = models.DateField(blank=True, null=True)

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('start',)
        verbose_name        = _('course registration history')
        verbose_name_plural = _('course registration history')

    def __str__(self):
        return '{course}, {start} - {end}'.format(
            course  = self.course.name,
            start   = date_format(self.start, 'SHORT_DATE_FORMAT'),
            end     = date_format(self.end, 'SHORT_DATE_FORMAT') if self.end else _('now'),
        )

    @property
    def course_journal_entries(self):
        qs = CourseJournalEntry.objects.filter(course=self.course, date__gte=self.start)
        if self.end:
            return qs.filter(date__lte=self.end)
        else:
            return qs

    def save(self, *args, **kwargs):
        if self.id:
            original = self.__class__.objects.get(id=self.id)
            min_journal_date = original.course_journal_entries.aggregate(models.Min('date'))['date__min']
            max_journal_date = original.course_journal_entries.aggregate(models.Max('date'))['date__max']
            # if journal entry exists, start must be set and lower or equal to min journal date
            if min_journal_date and self.start > min_journal_date:
                self.start = min_journal_date
            # end can not be lower than max journal date
            if self.end and max_journal_date and self.end < max_journal_date:
                self.end = max_journal_date
        super(CourseRegistrationHistory, self).save(*args, **kwargs)



@receiver(models.signals.post_save, sender=CourseRegistration)
def update_course_registration_history(sender, instance, created, **kwargs):
    if instance.approved:
        d = date.today()
        # if created or changed
        if (instance.course_history.count() == 0 or
                instance.course_history.filter(end=None).exclude(course_id=instance.subject_id).update(end=d)):
            # reopen or create entry starting today
            (
                CourseRegistrationHistory.objects.filter(
                    registration_id=instance.id, course_id=instance.subject_id, start=d,
                ).update(end=None) or
                CourseRegistrationHistory.objects.create(
                    registration_id=instance.id, course_id=instance.subject_id, start=d,
                )
            )



def get_default_agenda():
    return '<p>{}</p>'.format(_('instruction on OSH'))



@python_2_unicode_compatible
class CourseJournalEntry(StartEndMixin, models.Model):
    course      = models.ForeignKey(Course, verbose_name=_('course'), editable=False,
                                    related_name='journal_entries', on_delete=models.PROTECT)
    date        = models.DateField(_('date'))
    start       = models.TimeField(_('start time'), blank=True, null=True,
                                   help_text=_('Leave empty, if the course does not take place'))
    end         = models.TimeField(_('end time'), blank=True, null=True,
                                   help_text=_('Leave empty, if the course does not take place'))
    agenda      = HTMLField(_('session agenda'), default=get_default_agenda)
    registrations = models.ManyToManyField(CourseRegistration, verbose_name=_('participants'), blank=True,
                                           related_name='journal_entries')

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('date', 'start', 'end')
        verbose_name        = _('journal entry')
        verbose_name_plural = _('journal entries')

    def __str__(self):
        return '{course}, {date}'.format(
            course  = self.course.name,
            date    = self.date,
        )

    @cached_property
    def datetime_start(self):
        try:
            return datetime.combine(self.date, self.start)
        except:
            return None

    @cached_property
    def datetime_end(self):
        try:
            return datetime.combine(self.date, self.end)
        except:
            return None

    @cached_property
    def duration(self):
        try:
            return self.datetime_end - self.datetime_start
        except:
            return timedelta()
    duration.short_description = _('duration')

    @cached_property
    def all_registrations(self):
        return list(self.registrations.all())

    @cached_property
    def all_leader_entries(self):
        return list(self.leader_entries.all())

    @cached_property
    def all_leader_entries_by_leader(self):
        return dict((e.timesheet.leader, e) for e in self.all_leader_entries)

    @cached_property
    def all_leaders(self):
        return list(
            le.timesheet.leader for le in self.all_leader_entries
            if le.timesheet.leader in self.course.all_leaders
        )

    @cached_property
    def all_alternates(self):
        return list(
            le.timesheet.leader for le in self.all_leader_entries
            if le.timesheet.leader not in self.course.all_leaders
        )

    @property
    def timesheets(self):
        from .timesheets import Timesheet
        return Timesheet.objects.by_date(self.start).filter(
            leader__in = self.all_leaders + self.all_alternates,
        )

    def save(self, *args, **kwargs):
        if self.end is None:
            self.end = self.start
        super(CourseJournalEntry, self).save(*args, **kwargs)

    def get_edit_url(self):
        return reverse('leprikon:coursejournalentry_update', args=(self.id,))

    def get_delete_url(self):
        return reverse('leprikon:coursejournalentry_delete', args=(self.id,))



@python_2_unicode_compatible
class CourseJournalLeaderEntry(StartEndMixin, models.Model):
    course_entry = models.ForeignKey(CourseJournalEntry, verbose_name=_('course journal entry'),
                                     related_name='leader_entries', editable=False)
    timesheet   = models.ForeignKey('leprikon.Timesheet', verbose_name=_('timesheet'), related_name='course_entries',
                                    editable=False, on_delete=models.PROTECT)
    start       = models.TimeField(_('start time'))
    end         = models.TimeField(_('end time'))

    class Meta:
        app_label           = 'leprikon'
        verbose_name        = _('course journal leader entry')
        verbose_name_plural = _('course journal leader entries')
        unique_together     = (('course_entry', 'timesheet'),)

    def __str__(self):
        return '{}'.format(self.duration)

    @cached_property
    def date(self):
        return self.course_entry.date
    date.short_description = _('date')
    date.admin_order_field = 'course_entry__date'

    @cached_property
    def course(self):
        return self.course_entry.course
    course.short_description = _('course')

    @cached_property
    def datetime_start(self):
        return datetime.combine(self.date, self.start)

    @cached_property
    def datetime_end(self):
        return datetime.combine(self.date, self.end)

    @cached_property
    def duration(self):
        return self.datetime_end - self.datetime_start
    duration.short_description = _('duration')

    @property
    def group(self):
        return self.course

    def get_edit_url(self):
        return reverse('leprikon:coursejournalleaderentry_update', args=(self.id,))

    def get_delete_url(self):
        return reverse('leprikon:coursejournalleaderentry_delete', args=(self.id,))



class CoursePlugin(CMSPlugin):
    course     = models.ForeignKey(Course, verbose_name=_('course'), related_name='+')
    template    = models.CharField(_('template'), max_length=100,
                                   choices=settings.LEPRIKON_COURSE_TEMPLATES,
                                   default=settings.LEPRIKON_COURSE_TEMPLATES[0][0],
                                   help_text=_('The template used to render plugin.'))

    class Meta:
        app_label = 'leprikon'



class CourseListPlugin(CMSPlugin):
    school_year = models.ForeignKey(SchoolYear, verbose_name=_('school year'),
                                    related_name='+', blank=True, null=True)
    departments = models.ManyToManyField(Department, verbose_name=_('departments'), blank=True, related_name='+',
                                         help_text=_('Keep empty to skip searching by departments.'))
    course_types = models.ManyToManyField(SubjectType, verbose_name=_('course types'), blank=True, related_name='+',
                                          limit_choices_to={'subject_type': SubjectType.COURSE},
                                          help_text=_('Keep empty to skip searching by course types.'))
    age_groups  = models.ManyToManyField(AgeGroup, verbose_name=_('age groups'), blank=True, related_name='+',
                                         help_text=_('Keep empty to skip searching by age groups.'))
    groups      = models.ManyToManyField(SubjectGroup, verbose_name=_('course groups'), blank=True, related_name='+',
                                         help_text=_('Keep empty to skip searching by groups.'))
    leaders     = models.ManyToManyField(Leader, verbose_name=_('leaders'), blank=True, related_name='+',
                                         help_text=_('Keep empty to skip searching by leaders.'))
    template    = models.CharField(_('template'), max_length=100,
                                   choices=settings.LEPRIKON_COURSELIST_TEMPLATES,
                                   default=settings.LEPRIKON_COURSELIST_TEMPLATES[0][0],
                                   help_text=_('The template used to render plugin.'))

    class Meta:
        app_label = 'leprikon'

    def copy_relations(self, oldinstance):
        self.departments    = oldinstance.departments.all()
        self.course_types   = oldinstance.course_types.all()
        self.groups         = oldinstance.groups.all()
        self.age_groups     = oldinstance.age_groups.all()
        self.leaders        = oldinstance.leaders.all()

    @cached_property
    def all_departments(self):
        return list(self.departments.all())

    @cached_property
    def all_course_types(self):
        return list(self.course_types.all())

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
        courses = Course.objects.filter(school_year=school_year, public=True).distinct()

        if self.all_departments:
            courses = courses.filter(department__in = self.all_departments)
        if self.all_course_types:
            courses = courses.filter(subject_type__in = self.all_course_types)
        if self.all_age_groups:
            courses = courses.filter(age_groups__in = self.all_age_groups)
        if self.all_leaders:
            courses = courses.filter(leaders__in = self.all_leaders)
        if self.all_groups:
            courses = courses.filter(groups__in = self.all_groups)
            groups = self.all_groups
        elif self.all_course_types:
            groups = SubjectGroup.objects.filter(subject_types__in = self.all_course_types)
        else:
            groups = SubjectGroup.objects.all()

        context.update({
            'school_year':  school_year,
            'courses':      courses,
            'groups':       (
                self.Group(group = group, objects = courses.filter(groups=group))
                for group in groups
            ),
        })
        return context



class FilteredCourseListPlugin(CMSPlugin):
    school_year = models.ForeignKey(SchoolYear, verbose_name=_('school year'),
                                    related_name='+', blank=True, null=True)
    course_types = models.ManyToManyField(SubjectType, verbose_name=_('course types'), related_name='+',
                                          limit_choices_to={'subject_type': SubjectType.COURSE})

    class Meta:
        app_label = 'leprikon'

    def copy_relations(self, oldinstance):
        self.course_types = oldinstance.course_types.all()

    @cached_property
    def all_course_types(self):
        return list(self.course_types.all())

    def render(self, context):
        school_year = (self.school_year or getattr(context.get('request'), 'school_year') or
                       SchoolYear.objects.get_current())

        from ..forms.subjects import SubjectFilterForm
        form = SubjectFilterForm(
            subject_type_type = SubjectType.COURSE,
            subject_types = self.all_course_types,
            school_year = school_year,
            is_staff = context['request'].user.is_staff,
            data=context['request'].GET,
        )
        context.update({
            'school_year':  school_year,
            'form':         form,
            'courses':      form.get_queryset(),
        })
        return context
