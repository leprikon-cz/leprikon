from django import forms
from django.core.exceptions import ValidationError
from django.utils import formats
from django.utils.translation import ugettext_lazy as _

from ..models.timesheets import Timesheet, TimesheetEntry
from .fields import ReadonlyField
from .form import FormMixin


class TimesheetEntryAdminForm(forms.ModelForm):
    """
    Validation of ManyToManyField must be performed in form.clean()
    Always use TimesheetEntryAdminForm to change TimesheetEntry
    """

    class Meta:
        model = TimesheetEntry
        fields = ("date", "start", "end", "entry_type", "description")

    def __init__(self, **kwargs):
        self.leader = kwargs.pop("leader", None) or kwargs["instance"].timesheet.leader
        super().__init__(**kwargs)

        # make date, start and end read only, if timesheet is already submitted
        if self.instance.id and self.instance.timesheet.submitted:
            self.readonly = True
            self.readonly_fields = [
                ReadonlyField(label=_("Date"), value=self.instance.date),
                ReadonlyField(label=_("Start"), value=self.instance.start),
                ReadonlyField(label=_("End"), value=self.instance.end),
                ReadonlyField(label=_("Entry type"), value=self.instance.entry_type),
            ]
            self.fields = {"description": self.fields["description"]}
        else:
            self.readonly = False

    def clean_date(self):
        if self.instance.id:
            if self.cleaned_data["date"] < self.instance.timesheet.period.start:
                raise ValidationError(
                    _("The timesheet period {period} starts {start}").format(
                        period=self.instance.timesheet.period.name,
                        start=formats.date_format(self.instance.timesheet.period.start, "SHORT_DATE_FORMAT"),
                    )
                )
            if self.cleaned_data["date"] > self.instance.timesheet.period.end:
                raise ValidationError(
                    _("The timesheet period {period} ends {end}").format(
                        period=self.instance.timesheet.period.name,
                        end=formats.date_format(self.instance.timesheet.period.end, "SHORT_DATE_FORMAT"),
                    )
                )
        else:
            self.instance.timesheet = Timesheet.objects.for_leader_and_date(
                leader=self.leader, date=self.cleaned_data["date"]
            )
            if self.instance.timesheet.submitted:
                raise ValidationError(
                    _("Your timesheet for period {period} has already been submitted.").format(
                        period=self.instance.timesheet.period.name,
                    )
                )
        return self.cleaned_data["date"]

    def clean(self):
        # check overlaping entries
        if "date" in self.cleaned_data and "start" in self.cleaned_data and "end" in self.cleaned_data:
            qs = self.instance.timesheet.timesheet_entries.filter(
                date=self.cleaned_data["date"],
                start__lt=self.cleaned_data["end"],
                end__gt=self.cleaned_data["start"],
            )
            if self.instance.id:
                qs = qs.exclude(id=self.instance.id)
            if qs.exists():
                raise ValidationError(_("An overlaping entry has already been added in the timesheet."))
        return self.cleaned_data


class TimesheetEntryForm(FormMixin, TimesheetEntryAdminForm):
    pass
