from datetime import datetime, timedelta

from django.core.urlresolvers import reverse_lazy as reverse
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from djangocms_text_ckeditor.fields import HTMLField

from .startend import StartEndMixin
from .subjects import Subject, SubjectRegistration


def get_default_agenda():
    return '<p>{}</p>'.format(_('instruction on OSH'))


@python_2_unicode_compatible
class JournalEntry(StartEndMixin, models.Model):
    subject     = models.ForeignKey(Subject, verbose_name=_('subject'), editable=False,
                                    related_name='journal_entries', on_delete=models.PROTECT)
    date        = models.DateField(_('date'))
    start       = models.TimeField(_('start time'), blank=True, null=True)
    end         = models.TimeField(_('end time'), blank=True, null=True)
    agenda      = HTMLField(_('session agenda'), default=get_default_agenda)
    registrations = models.ManyToManyField(SubjectRegistration, verbose_name=_('participants'), blank=True,
                                           related_name='journal_entries')

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('date', 'start', 'end')
        verbose_name        = _('journal entry')
        verbose_name_plural = _('journal entries')

    def __str__(self):
        return '{subject_name}, {date}, {duration}'.format(
            subject_name=self.subject.name,
            date=self.date,
            duration=self.duration,
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
    def all_registrations_idset(self):
        return set(r.id for r in self.all_registrations)

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
            if le.timesheet.leader in self.subject.all_leaders
        )

    @cached_property
    def all_alternates(self):
        return list(
            le.timesheet.leader for le in self.all_leader_entries
            if le.timesheet.leader not in self.subject.all_leaders
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
        super(JournalEntry, self).save(*args, **kwargs)

    def get_edit_url(self):
        return reverse('leprikon:journalentry_update', args=(self.id,))

    def get_delete_url(self):
        return reverse('leprikon:journalentry_delete', args=(self.id,))


@python_2_unicode_compatible
class JournalLeaderEntry(StartEndMixin, models.Model):
    journal_entry = models.ForeignKey(JournalEntry, verbose_name=_('journal entry'),
                                      related_name='leader_entries', editable=False)
    timesheet   = models.ForeignKey('leprikon.Timesheet', verbose_name=_('timesheet'), related_name='journal_entries',
                                    editable=False, on_delete=models.PROTECT)
    start       = models.TimeField(_('start time'))
    end         = models.TimeField(_('end time'))

    class Meta:
        app_label           = 'leprikon'
        verbose_name        = _('journal leader entry')
        verbose_name_plural = _('journal leader entries')
        unique_together     = (('journal_entry', 'timesheet'),)

    def __str__(self):
        return '{subject_name}, {date}, {duration}'.format(
            subject_name=self.journal_entry.subject.name,
            date=self.journal_entry.date,
            duration=self.duration,
        )

    @cached_property
    def date(self):
        return self.journal_entry.date
    date.short_description = _('date')
    date.admin_order_field = 'journal_entry__date'

    @cached_property
    def subject(self):
        return self.journal_entry.subject
    subject.short_description = _('subject')

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
        return self.subject

    def get_edit_url(self):
        return reverse('leprikon:journalleaderentry_update', args=(self.id,))

    def get_delete_url(self):
        return reverse('leprikon:journalleaderentry_delete', args=(self.id,))
