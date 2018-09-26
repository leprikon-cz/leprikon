import calendar
from collections import namedtuple
from datetime import date, datetime, timedelta

from django.core.urlresolvers import reverse_lazy as reverse
from django.db import models
from django.utils.dateformat import DateFormat
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from djangocms_text_ckeditor.fields import HTMLField

from .courses import CourseJournalLeaderEntry
from .roles import Leader
from .startend import StartEndMixin


def start_end_by_date(d):
    # we work with monthly timesheets by default
    # TODO: allow weekly and quarterly timesheets by settings
    return {
        'start':    date(d.year, d.month, 1),
        'end':      date(d.year, d.month, calendar.monthrange(d.year, d.month)[1]),
    }



class TimesheetPeriodManager(models.Manager):
    def for_date(self, date):
        return self.get_or_create(**start_end_by_date(date))[0]


@python_2_unicode_compatible
class TimesheetPeriod(StartEndMixin, models.Model):
    start   = models.DateField(_('start date'), editable=False, unique=True)
    end     = models.DateField(_('end date'), editable=False, unique=True)

    objects = TimesheetPeriodManager()

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('-start',)
        verbose_name        = _('timesheet period')
        verbose_name_plural = _('timesheet periods')

    def __str__(self):
        return self.name

    @cached_property
    def name(self):
        # we work with monthly timesheets by default
        # TODO: allow weekly and quarterly timesheets by settings
        return DateFormat(self.start).format('F Y')

    @cached_property
    def all_timesheets(self):
        return list(self.timesheets.all())



class TimesheetManager(models.Manager):

    def for_leader_and_date(self, leader, date):
        return self.get_or_create(
            leader  = leader,
            period  = TimesheetPeriod.objects.for_date(date),
        )[0]


@python_2_unicode_compatible
class Timesheet(models.Model):
    period      = models.ForeignKey(TimesheetPeriod, verbose_name=_('period'), editable=False,
                                    related_name='timesheets', on_delete=models.PROTECT)
    leader      = models.ForeignKey(Leader, verbose_name=_('leader'), editable=False,
                                    related_name='timesheets', on_delete=models.PROTECT)
    submitted   = models.BooleanField(_('submitted'), default=False)
    paid        = models.BooleanField(_('paid'), default=False)

    objects     = TimesheetManager()

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('-period__start',)
        unique_together     = (('period', 'leader'),)
        verbose_name        = _('timesheet')
        verbose_name_plural = _('timesheets')

    def __str__(self):
        return '{leader}, {period}'.format(
            leader  = self.leader,
            period  = self.period.name,
        )

    @property
    def course_entries(self):
        return CourseJournalLeaderEntry.objects.filter(
            course_entry__date__gte = self.period.start,
            course_entry__date__lte = self.period.end,
            leader                  = self.leader,
        )

    @cached_property
    def all_course_entries(self):
        return list(self.course_entries.all())

    @cached_property
    def all_timesheet_entries(self):
        return list(self.timesheet_entries.all())

    @cached_property
    def all_entries(self):
        return sorted(
            self.all_timesheet_entries + self.all_course_entries,
            key=lambda e: e.datetime_start,
        )

    class EntryGroup(namedtuple('_EntryGroup', ('name', 'entries'))):
        @property
        def duration(self):
            return sum((e.duration for e in self.entries), timedelta())

    @cached_property
    def groups(self):
        gs = {}
        for entry in self.all_entries:
            if entry.group not in gs:
                gs[entry.group] = self.EntryGroup(
                    name = entry.group.name,
                    entries = [],
                )
            gs[entry.group].entries.append(entry)
        return list(gs.values())



@python_2_unicode_compatible
class TimesheetEntryType(models.Model):
    name    = models.CharField(_('name'), max_length=150)
    order   = models.IntegerField(_('order'), blank=True, default=0)

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('order',)
        verbose_name        = _('timesheet entry type')
        verbose_name_plural = _('timesheet entry types')

    def __str__(self):
        return self.name



@python_2_unicode_compatible
class TimesheetEntry(StartEndMixin, models.Model):
    timesheet   = models.ForeignKey(Timesheet, verbose_name=_('timesheet'), editable=False,
                                    related_name='timesheet_entries', on_delete=models.PROTECT)
    entry_type  = models.ForeignKey(TimesheetEntryType, verbose_name=_('entry type'), null=True,
                                    related_name='entries', on_delete=models.PROTECT)
    date        = models.DateField(_('date'))
    start       = models.TimeField(_('start time'))
    end         = models.TimeField(_('end time'))
    description = HTMLField(_('work description'))

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('start',)
        verbose_name        = _('timesheet entry')
        verbose_name_plural = _('timesheet entries')

    def __str__(self):
        return '{}'.format(self.duration)

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
        return self.entry_type

    def get_edit_url(self):
        return reverse('leprikon:timesheetentry_update', args=(self.id,))

    def get_delete_url(self):
        return reverse('leprikon:timesheetentry_delete', args=(self.id,))
