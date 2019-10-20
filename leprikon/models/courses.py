from collections import namedtuple
from datetime import date, datetime, timedelta

from cms.models import CMSPlugin
from django.db import models
from django.dispatch import receiver
from django.utils.encoding import force_text
from django.utils.formats import date_format
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from ..conf import settings
from ..utils import comma_separated
from .agegroup import AgeGroup
from .department import Department
from .fields import DAY_OF_WEEK, DayOfWeekField
from .journals import JournalEntry
from .roles import Leader
from .schoolyear import SchoolYear, SchoolYearDivision, SchoolYearPeriod
from .startend import StartEndMixin
from .subjects import (
    Subject, SubjectDiscount, SubjectGroup, SubjectRegistration, SubjectType,
)
from .utils import PaymentStatus


class Course(Subject):
    school_year_division = models.ForeignKey(SchoolYearDivision, on_delete=models.PROTECT,
                                             related_name='courses', verbose_name=_('school year division'))

    class Meta:
        app_label = 'leprikon'
        ordering = ('code', 'name')
        verbose_name = _('course')
        verbose_name_plural = _('courses')

    @cached_property
    def all_times(self):
        return list(self.times.all())

    @cached_property
    def all_periods(self):
        return list(self.school_year_division.periods.all())

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

    def get_next_time(self, now=None):
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

    def copy_to_school_year(old, school_year):
        new = Course.objects.get(id=old.id)
        new.id, new.pk = None, None
        new.school_year = school_year
        new.public = False
        new.evaluation = ''
        new.note = ''
        try:
            new.school_year_division = SchoolYearDivision.objects.get(
                school_year=school_year,
                name=old.school_year_division.name,
            )
        except SchoolYearDivision.DoesNotExist:
            new.school_year_division = old.school_year_division.copy_to_school_year(school_year)
        new.save()
        new.groups = old.groups.all()
        new.age_groups = old.age_groups.all()
        new.leaders = old.leaders.all()
        new.questions = old.questions.all()
        new.times = old.times.all()
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


class CourseTime(StartEndMixin, models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE,
                               related_name='times', verbose_name=_('course'))
    day_of_week = DayOfWeekField(_('day of week'))
    start = models.TimeField(_('start time'), blank=True, null=True)
    end = models.TimeField(_('end time'), blank=True, null=True)

    class Meta:
        app_label = 'leprikon'
        ordering = ('day_of_week', 'start')
        verbose_name = _('time')
        verbose_name_plural = _('times')

    def __str__(self):
        if self.start is not None and self.end is not None:
            return _('{day}, {start:%H:%M} - {end:%H:%M}').format(
                day=self.day,
                start=self.start,
                end=self.end,
            )
        elif self.start is not None:
            return _('{day}, {start:%H:%M}').format(
                day=self.day,
                start=self.start,
            )
        else:
            return force_text(self.day)

    @cached_property
    def day(self):
        return DAY_OF_WEEK[self.day_of_week]

    Time = namedtuple('Time', ('date', 'start', 'end'))

    def get_next_time(self, now=None):
        now = now or datetime.now()
        daydelta = (self.day_of_week - now.isoweekday()) % 7
        if daydelta == 0 and (isinstance(now, date) or self.start is None or self.start <= now.time()):
            daydelta = 7
        if isinstance(now, datetime):
            next_date = now.date() + timedelta(daydelta)
        else:
            next_date = now + timedelta(daydelta)
        return self.Time(
            date=next_date,
            start=self.start,
            end=self.end,
        )


class CourseRegistration(SubjectRegistration):
    subject_type = SubjectType.COURSE

    class Meta:
        app_label = 'leprikon'
        verbose_name = _('course registration')
        verbose_name_plural = _('course registrations')

    @property
    def periods(self):
        periods = self.subject.course.school_year_division.periods.filter(
            end__gte=self.created.date(),
        )
        if self.canceled:
            # include at least the first one (if any)
            first_period_start = periods.values_list('start', flat=True).first()
            return periods.filter(
                start__lte=max(self.canceled.date(), first_period_start or self.canceled.date())
            )
        else:
            return periods

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
                period=period,
                status=PaymentStatus(
                    price=self.price,
                    discount=discount,
                    paid=min(self.price - discount, paid) if counter < len(self.all_periods) else paid,
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
        discounted = self.get_discounted(d)
        partial_discounted = self.get_partial_discounted(d)
        paid = self.get_paid(d)
        return self.PaymentStatuses(
            partial=PaymentStatus(price=partial_price, discount=partial_discounted, paid=paid),
            total=PaymentStatus(price=total_price, discount=discounted, paid=paid),
        )

    def get_partial_discounted(self, d=None):
        if d is None:
            d = date.today()
        # always count the first period (if any)
        if self.all_periods:
            d = max(d, self.all_periods[0].start)
        return sum(p.amount for p in self.get_discounts(d) if p.period.start <= d)

    @cached_property
    def current_receivable(self):
        d = date.today()
        price = self.price * (len(tuple(p for p in self.all_periods if p.start <= d)) or 1)
        discount = self.get_discounted(d)
        paid = self.get_paid(d)
        return max(price - discount - paid, 0)


class CourseDiscount(SubjectDiscount):
    registration = models.ForeignKey(CourseRegistration, on_delete=models.CASCADE,
                                     related_name='discounts', verbose_name=_('registration'))
    period = models.ForeignKey(SchoolYearPeriod, on_delete=models.PROTECT,
                               related_name='discounts', verbose_name=_('period'))


class CourseRegistrationHistory(StartEndMixin, models.Model):
    registration = models.ForeignKey(CourseRegistration, editable=False, on_delete=models.PROTECT,
                                     related_name='course_history', verbose_name=_('course'))
    course = models.ForeignKey(Course, editable=False, on_delete=models.PROTECT,
                               related_name='registrations_history', verbose_name=_('course'))
    start = models.DateField()
    end = models.DateField(blank=True, null=True)

    class Meta:
        app_label = 'leprikon'
        ordering = ('start',)
        verbose_name = _('course registration history')
        verbose_name_plural = _('course registration history')

    def __str__(self):
        return '{course}, {start} - {end}'.format(
            course=self.course.name,
            start=date_format(self.start, 'SHORT_DATE_FORMAT'),
            end=date_format(self.end, 'SHORT_DATE_FORMAT') if self.end else _('now'),
        )

    @property
    def journal_entries(self):
        qs = JournalEntry.objects.filter(subject_id=self.course_id, date__gte=self.start)
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


class CoursePlugin(CMSPlugin):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='+', verbose_name=_('course'))
    template = models.CharField(_('template'), max_length=100,
                                choices=settings.LEPRIKON_COURSE_TEMPLATES,
                                default=settings.LEPRIKON_COURSE_TEMPLATES[0][0],
                                help_text=_('The template used to render plugin.'))

    class Meta:
        app_label = 'leprikon'


class CourseListPlugin(CMSPlugin):
    school_year = models.ForeignKey(SchoolYear, blank=True, null=True, on_delete=models.CASCADE,
                                    related_name='+', verbose_name=_('school year'))
    departments = models.ManyToManyField(Department, blank=True, related_name='+', verbose_name=_('departments'),
                                         help_text=_('Keep empty to skip searching by departments.'))
    course_types = models.ManyToManyField(SubjectType, blank=True,
                                          limit_choices_to={'subject_type': SubjectType.COURSE},
                                          related_name='+', verbose_name=_('course types'),
                                          help_text=_('Keep empty to skip searching by course types.'))
    age_groups = models.ManyToManyField(AgeGroup, blank=True, related_name='+', verbose_name=_('age groups'),
                                        help_text=_('Keep empty to skip searching by age groups.'))
    groups = models.ManyToManyField(SubjectGroup, blank=True, related_name='+', verbose_name=_('course groups'),
                                    help_text=_('Keep empty to skip searching by groups.'))
    leaders = models.ManyToManyField(Leader, blank=True, related_name='+', verbose_name=_('leaders'),
                                     help_text=_('Keep empty to skip searching by leaders.'))
    template = models.CharField(_('template'), max_length=100,
                                choices=settings.LEPRIKON_COURSELIST_TEMPLATES,
                                default=settings.LEPRIKON_COURSELIST_TEMPLATES[0][0],
                                help_text=_('The template used to render plugin.'))

    class Meta:
        app_label = 'leprikon'

    def copy_relations(self, oldinstance):
        self.departments = oldinstance.departments.all()
        self.course_types = oldinstance.course_types.all()
        self.groups = oldinstance.groups.all()
        self.age_groups = oldinstance.age_groups.all()
        self.leaders = oldinstance.leaders.all()

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
            courses = courses.filter(department__in=self.all_departments)
        if self.all_course_types:
            courses = courses.filter(subject_type__in=self.all_course_types)
        if self.all_age_groups:
            courses = courses.filter(age_groups__in=self.all_age_groups)
        if self.all_leaders:
            courses = courses.filter(leaders__in=self.all_leaders)
        if self.all_groups:
            courses = courses.filter(groups__in=self.all_groups)
            groups = self.all_groups
        elif self.all_course_types:
            groups = SubjectGroup.objects.filter(subject_types__in=self.all_course_types)
        else:
            groups = SubjectGroup.objects.all()

        context.update({
            'school_year': school_year,
            'courses': courses,
            'groups': (
                self.Group(group=group, objects=courses.filter(groups=group))
                for group in groups
            ),
        })
        return context


class FilteredCourseListPlugin(CMSPlugin):
    school_year = models.ForeignKey(SchoolYear, blank=True, null=True, on_delete=models.CASCADE,
                                    related_name='+', verbose_name=_('school year'))
    course_types = models.ManyToManyField(SubjectType, limit_choices_to={'subject_type': SubjectType.COURSE},
                                          related_name='+', verbose_name=_('course types'))

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
            subject_type_type=SubjectType.COURSE,
            subject_types=self.all_course_types,
            school_year=school_year,
            is_staff=context['request'].user.is_staff,
            data=context['request'].GET,
        )
        context.update({
            'school_year': school_year,
            'form': form,
            'courses': form.get_queryset(),
        })
        return context
