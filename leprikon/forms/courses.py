from datetime import date

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import (
    ugettext_lazy as _, ungettext_lazy as ungettext,
)

from ..models.courses import (
    CourseDiscount, CourseJournalEntry, CourseJournalLeaderEntry,
)
from ..models.roles import Leader
from ..models.timesheets import Timesheet, TimesheetPeriod
from ..utils import comma_separated
from .fields import ReadonlyField
from .form import FormMixin

User = get_user_model()


class CourseDiscountAdminForm(forms.ModelForm):

    class Meta:
        model = CourseDiscount
        fields = ['registration', 'period', 'accounted', 'amount', 'explanation']

    def __init__(self, *args, **kwargs):
        super(CourseDiscountAdminForm, self).__init__(*args, **kwargs)
        if 'period' in self.fields:
            if self.data:
                registration_id = int(self.data['registration'])
            elif self.initial:
                registration_id = int(self.initial['registration'])
            else:
                registration_id = self.instance.registration_id
            self.fields['period'].widget.choices.queryset = self.fields['period'].widget.choices.queryset.filter(
                school_year_division__courses__registrations__id = registration_id
            )


class CourseJournalLeaderEntryAdminForm(forms.ModelForm):

    class Meta:
        model = CourseJournalLeaderEntry
        fields = ['start', 'end']

    def __init__(self, *args, **kwargs):
        super(CourseJournalLeaderEntryAdminForm, self).__init__(*args, **kwargs)
        if self.instance.timesheet.submitted:
            try:
                del(self.fields['start'])
                del(self.fields['end'])
            except KeyError:
                pass

    def clean(self):
        cleaned_data = super(CourseJournalLeaderEntryAdminForm, self).clean()

        # readonly start end
        if self.instance.id and self.instance.timesheet.submitted:
            cleaned_data['start']   = self.instance.start
            cleaned_data['end']     = self.instance.end

        # check entry start and end
        errors = {}
        course_entry = self.instance.course_entry
        if cleaned_data['start'] < course_entry.start:
            errors['start'] = _('The course journal entry starts at {start}').format(
                start = course_entry.start,
            )
        if cleaned_data['end'] > course_entry.end:
            errors['end'] = _('The course journal entry ends at {end}').format(
                end = course_entry.end,
            )
        if errors:
            raise ValidationError(errors)

        return cleaned_data



class CourseJournalLeaderEntryForm(FormMixin, CourseJournalLeaderEntryAdminForm):

    def __init__(self, *args, **kwargs):
        super(CourseJournalLeaderEntryForm, self).__init__(*args, **kwargs)
        self.readonly_fields = [
            ReadonlyField(label=_('Course'),    value=self.instance.course_entry.course.name),
            ReadonlyField(label=_('Date'),      value=self.instance.course_entry.date),
            ReadonlyField(label=_('Leader'),    value=self.instance.timesheet.leader),
        ]
        if self.instance.timesheet.submitted:
            self.readonly_fields += [
                ReadonlyField(label=_('Start'), value=self.instance.start),
                ReadonlyField(label=_('End'),   value=self.instance.end),
            ]




class CourseJournalEntryAdminForm(forms.ModelForm):

    class Meta:
        model = CourseJournalEntry
        fields = ['date', 'start', 'end', 'agenda', 'registrations']

    def __init__(self, *args, **kwargs):
        self.course = kwargs.pop('course', None) or kwargs['instance'].course
        super(CourseJournalEntryAdminForm, self).__init__(*args, **kwargs)
        self.instance.course = self.course

        if self.instance.id:
            d = self.instance.date
            self.readonly_fields = [
                ReadonlyField(label=_('Date'),  value=d),
            ]
            try:
                del(self.fields['date'])
            except:
                pass
        else:
            last = self.instance.course.journal_entries.last()
            if last:
                last_end = last.datetime_end or last.date
            else:
                last_end = None
            next_time = self.instance.course.get_next_time(last_end)
            if next_time:
                self.initial['date']  = next_time.date
                self.initial['start'] = next_time.start
                self.initial['end']   = next_time.end
            else:
                self.initial['date']  = date.today()
            try:
                d = self.fields['date'].clean(kwargs['data']['date'])
            except:
                d = self.initial['date']

        self.fields['registrations'].widget.choices.queryset = self.instance.course.get_approved_registrations(d)
        self.fields['registrations'].help_text = None

    def clean(self):
        start   = self.cleaned_data.get('start', None)
        end     = self.cleaned_data.get('end', None)

        # start and end must be both set or both None
        if start is None and end is not None:
            raise ValidationError({'start': _('If You fill in start time, You must fill end time too.')})
        elif end is None and start is not None:
            raise ValidationError({'end':   _('If You fill in end time, You must fill start time too.')})

        # check overlaping entries
        if start:
            qs = CourseJournalEntry.objects.filter(
                course      = self.instance.course,
                date        = self.cleaned_data.get('date', self.instance.date),
                start__lt   = end,
                end__gt     = start,
            )
            if self.instance.id:
                qs = qs.exclude(id=self.instance.id)
            if qs.exists():
                raise ValidationError(_('An overlaping entry has already been added in the course journal.'))

        # check submitted leader entries
        submitted_leader_entries = [
            e for e in self.instance.all_leader_entries
            if e.timesheet.submitted
        ]
        if submitted_leader_entries:
            max_start   = min(e.start for e in submitted_leader_entries)
            min_end     = max(e.end   for e in submitted_leader_entries)
            errors = {}
            if (start is None) or (start > max_start):
                errors['start'] = _('Some submitted timesheet entries start at {start}').format(
                    start = max_start,
                )
            if (end is None) or (end < min_end):
                errors['end'] = _('Some submitted timesheet entries end at {end}').format(
                    end = min_end,
                )
            if errors:
                raise ValidationError(errors)

        return self.cleaned_data



class CourseJournalEntryForm(FormMixin, CourseJournalEntryAdminForm):
    leaders     = forms.ModelMultipleChoiceField(Leader.objects, label=_('Leaders'), required=False)
    alternates  = forms.ModelMultipleChoiceField(Leader.objects, label=_('Alternates'), required=False)

    def __init__(self, *args, **kwargs):
        super(CourseJournalEntryForm, self).__init__(*args, **kwargs)
        self.readonly_fields = [
            ReadonlyField(label=_('Course'), value=self.course),
        ]

        # only allow to select leaders or alterates with not submitted timesheets
        leaders     = self.instance.course.all_leaders
        alternates  = [l for l in Leader.objects.all() if l not in leaders]

        self.fields['leaders'].widget.choices = tuple((l.id, l) for l in leaders)
        self.fields['leaders'].help_text = None
        self.fields['alternates'].widget.choices = tuple((l.id, l) for l in alternates)
        self.fields['alternates'].help_text = None

        if self.instance.id:
            self.initial['leaders']     = [l.id for l in self.instance.all_leaders]
            self.initial['alternates']  = [l.id for l in self.instance.all_alternates]
        else:
            self.initial['leaders']     = [l.id for l in leaders]

    def clean(self):
        self.cleaned_data = super(CourseJournalEntryForm, self).clean()
        self.cleaned_entries = []
        self.deleted_entries = []

        d   = self.cleaned_data.get('date', self.instance.date)
        if d is None:
            # no other validation makes sense without date
            return self.cleaned_data

        if 'start' in self.cleaned_data and 'end' in self.cleaned_data:
            errors = {}
            entries_by_leader = {
                'leaders': dict(
                    (entry.timesheet.leader, entry) for entry in self.instance.all_leader_entries
                    if entry.timesheet.leader in self.instance.all_leaders
                ),
                'alternates': dict(
                    (entry.timesheet.leader, entry) for entry in self.instance.all_leader_entries
                    if entry.timesheet.leader in self.instance.all_alternates
                ),
            }
            leaders_with_submitted_timesheets = {}
            period  = TimesheetPeriod.objects.for_date(d)

            for group in ('leaders', 'alternates'):
                leaders_with_submitted_timesheets[group] = []
                for leader in self.cleaned_data[group]:
                    if leader not in entries_by_leader[group]:
                        # try to create new leader entry
                        timesheet = Timesheet.objects.for_leader_and_date(leader=leader, date=d)
                        if timesheet.submitted:
                            # can not create entry
                            leaders_with_submitted_timesheets[group].append(leader)
                            continue
                        entry = CourseJournalLeaderEntry()
                        entry.course_entry = self.instance
                        entry.timesheet = Timesheet.objects.for_leader_and_date(leader=leader, date=d)
                        entry.start = self.cleaned_data['start']
                        entry.end   = self.cleaned_data['end']
                    else:
                        # try to update existing leader entry
                        entry = entries_by_leader[group].pop(leader)
                        if not entry.timesheet.submitted:
                            if self.cleaned_data['start'] != self.instance.start:
                                if entry.start == self.instance.start:
                                    entry.start = self.cleaned_data['start']
                                else:
                                    entry.start = max(entry.start, self.cleaned_data['start'])
                            if self.cleaned_data['end'] != self.instance.end:
                                if entry.end == self.instance.end:
                                    entry.end = self.cleaned_data['end']
                                else:
                                    entry.end = min(entry.end, self.cleaned_data['end'])
                    # store cleaned entry, or delete it, if it is broken by the update
                    if entry.start < entry.end:
                        self.cleaned_entries.append(entry)
                    elif entry.id:
                        self.deleted_entries.append(entry)
                # try to delete stale entries
                for entry in entries_by_leader[group].values():
                    if entry.timesheet.submitted:
                        # can not delete entry
                        leaders_with_submitted_timesheets[group].append(entry.timesheet.leader)
                        continue
                    # store deleted entry
                    self.deleted_entries.append(entry)

            if leaders_with_submitted_timesheets['leaders']:
                errors['leaders'] = ungettext(
                    'Leader {leaders} has already submitted timesheet for {period}.',
                    'Leaders {leaders} have already submitted timesheet for {period}.',
                    len(leaders_with_submitted_timesheets['leaders'])
                ).format(
                    leaders = comma_separated(leaders_with_submitted_timesheets['leaders']),
                    period  = period.name,
                )
            if leaders_with_submitted_timesheets['alternates']:
                errors['alternates'] = ungettext(
                    'Alternate {leaders} has already submitted timesheet for {period}.',
                    'Alternates {leaders} have already submitted timesheet for {period}.',
                    len(leaders_with_submitted_timesheets['alternates'])
                ).format(
                    leaders = comma_separated(leaders_with_submitted_timesheets['alternates']),
                    period  = period.name,
                )
            if errors:
                raise ValidationError(errors)

        return self.cleaned_data

    def save(self, commit=True):
        self.instance = super(CourseJournalEntryForm, self).save(commit)
        for entry in self.cleaned_entries:
            entry.course_entry = self.instance
            entry.save()
        for entry in self.deleted_entries:
            entry.delete()
