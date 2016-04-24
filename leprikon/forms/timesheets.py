from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django import forms
from django.core.exceptions import ValidationError
from django.utils import formats
from django.utils.translation import ugettext_lazy as _

from ..models import TimesheetEntry

from .fields import ReadonlyField
from .form import FormMixin


class TimesheetEntryAdminForm(forms.ModelForm):
    """
    Validation of ManyToManyField must be performed in form.clean()
    Always use TimesheetEntryAdminForm to change TimesheetEntry
    """

    class Meta:
        model   = TimesheetEntry
        fields  = ('date', 'start', 'end', 'entry_type', 'description')

    def __init__(self, *args, **kwargs):
        timesheet = kwargs.pop('timesheet', None) or kwargs['instance'].timesheet
        super(TimesheetEntryAdminForm, self).__init__(*args, **kwargs)
        self.instance.timesheet = timesheet

        # make date, start and end read only, if timesheet is already submitted
        if self.instance.id and self.instance.timesheet.submitted:
            self.readonly = True
            self.readonly_fields = [
                ReadonlyField(label=_('Date'),      value=self.instance.date),
                ReadonlyField(label=_('Start'),     value=self.instance.start),
                ReadonlyField(label=_('End'),       value=self.instance.end),
                ReadonlyField(label=_('Entry type'),value=self.instance.entry_type),
            ]
            self.fields = {'description': self.fields['description']}
        else:
            self.readonly = False

    def clean_date(self):
        if self.cleaned_data['date'] < self.instance.timesheet.period.start:
            raise ValidationError(_('The timesheet period {period} starts {start}').format(
                period  = self.instance.timesheet.period.name,
                start   = formats.date_format(self.instance.timesheet.period.start, "SHORT_DATE_FORMAT"),
            ))
        if self.cleaned_data['date'] > self.instance.timesheet.period.end:
            raise ValidationError(_('The timesheet period {period} ends {end}').format(
                period  = self.instance.timesheet.period.name,
                end   = formats.date_format(self.instance.timesheet.period.end, "SHORT_DATE_FORMAT"),
            ))
        return self.cleaned_data['date']

    def clean(self):
        # check overlaping entries
        if 'date' in self.cleaned_data and 'start' in self.cleaned_data and 'end' in self.cleaned_data:
            qs = self.instance.timesheet.timesheet_entries.filter(
                date        = self.cleaned_data['date'],
                start__lt   = self.cleaned_data['end'],
                end__gt     = self.cleaned_data['start'],
            )
            if self.instance.id:
                qs = qs.exclude(id=self.instance.id)
            if qs.exists():
                raise ValidationError(_('An overlaping entry has already been added in the timesheet.'))
        return self.cleaned_data



class TimesheetEntryForm(FormMixin, TimesheetEntryAdminForm):
    pass

