from datetime import date

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _, ungettext_lazy as ungettext

from ..models.journals import JournalEntry, JournalLeaderEntry
from ..models.roles import Leader
from ..models.timesheets import Timesheet, TimesheetPeriod
from ..utils import comma_separated
from .fields import ReadonlyField
from .form import FormMixin


class JournalLeaderEntryAdminForm(forms.ModelForm):
    class Meta:
        model = JournalLeaderEntry
        fields = ["start", "end"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.timesheet.submitted:
            try:
                del self.fields["start"]
                del self.fields["end"]
            except KeyError:
                pass

    def clean(self):
        cleaned_data = super().clean()

        # readonly start end
        if self.instance.id and self.instance.timesheet.submitted:
            cleaned_data["start"] = self.instance.start
            cleaned_data["end"] = self.instance.end

        # check entry start and end
        errors = {}
        journal_entry = self.instance.journal_entry
        if cleaned_data["start"] < journal_entry.start:
            errors["start"] = _("The journal entry starts at {start}").format(
                start=journal_entry.start,
            )
        if cleaned_data["end"] > journal_entry.end:
            errors["end"] = _("The journal entry ends at {end}").format(
                end=journal_entry.end,
            )
        if errors:
            raise ValidationError(errors)

        return cleaned_data


class JournalLeaderEntryForm(FormMixin, JournalLeaderEntryAdminForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.readonly_fields = [
            ReadonlyField(label=_("Subject"), value=self.instance.journal_entry.subject.name),
            ReadonlyField(label=_("Date"), value=self.instance.journal_entry.date),
            ReadonlyField(label=_("Leader"), value=self.instance.timesheet.leader),
        ]
        if self.instance.timesheet.submitted:
            self.readonly_fields += [
                ReadonlyField(label=_("Start"), value=self.instance.start),
                ReadonlyField(label=_("End"), value=self.instance.end),
            ]


class JournalEntryAdminForm(forms.ModelForm):
    class Meta:
        model = JournalEntry
        fields = ["date", "start", "end", "agenda", "participants", "participants_instructed"]

    def __init__(self, *args, **kwargs):
        self.subject = kwargs.pop("subject", None) or kwargs["instance"].subject
        super().__init__(*args, **kwargs)
        self.instance.subject = self.subject

        if self.instance.id:
            d = self.instance.date
            self.readonly_fields = [
                ReadonlyField(label=_("Date"), value=d),
            ]
            try:
                del self.fields["date"]
            except KeyError:
                pass
        else:
            last = self.instance.subject.journal_entries.last()
            if last:
                last_end = last.datetime_end or last.date
            else:
                last_end = None
            next_time = self.instance.subject.subject.get_next_time(last_end)
            if next_time:
                self.initial["date"] = next_time.date
                self.initial["start"] = next_time.start
                self.initial["end"] = next_time.end
            else:
                self.initial["date"] = date.today()
            try:
                d = self.fields["date"].clean(kwargs["data"]["date"])
            except (KeyError, TypeError, ValidationError):
                d = self.initial["date"]
        self.fields["participants"].widget.choices.queryset = self.instance.subject.get_valid_participants(d)
        self.fields["participants"].help_text = None

        self.fields["participants_instructed"].widget.choices.queryset = self.instance.subject.get_valid_participants(d)
        self.fields["participants_instructed"].help_text = None

    def clean(self):
        date = self.cleaned_data.get("date", self.instance.date)
        start = self.cleaned_data.get("start")
        end = self.cleaned_data.get("end")

        # start and end must be both set or both None
        if start is None and end is not None:
            raise ValidationError({"start": _("If You fill in start time, You must fill end time too.")})
        elif end is None and start is not None:
            raise ValidationError({"end": _("If You fill in end time, You must fill start time too.")})

        # check overlaping entries
        if start:
            qs = JournalEntry.objects.filter(
                subject=self.instance.subject,
                date=self.cleaned_data.get("date", self.instance.date),
                start__lt=end,
                end__gt=start,
            )
            if self.instance.id:
                qs = qs.exclude(id=self.instance.id)
            if qs.exists():
                raise ValidationError(_("An overlaping entry has already been added in the journal."))

        # check instructed participants
        participants = set(self.cleaned_data.get("participants", []))
        participants_instructed = set(self.cleaned_data.get("participants_instructed", []))
        not_present_participants_instructed = participants_instructed - participants
        if not_present_participants_instructed:
            self.add_error(
                "participants_instructed",
                _("Following participants were selected as instructed, but not selected as present: {}").format(
                    comma_separated(map(str, not_present_participants_instructed))
                ),
            )
        not_instructed_participants = []
        for participant in participants - participants_instructed:
            if not participant.instructed.filter(date__lt=date).exists():
                not_instructed_participants.append(participant)
        if not_instructed_participants:
            self.add_error(
                "participants",
                _("Following participants have not yet been instructed: {}").format(
                    comma_separated(map(str, not_instructed_participants))
                ),
            )

        # check submitted leader entries
        submitted_leader_entries = [e for e in self.instance.all_leader_entries if e.timesheet.submitted]
        if submitted_leader_entries:
            max_start = min(e.start for e in submitted_leader_entries)
            min_end = max(e.end for e in submitted_leader_entries)
            errors = {}
            if (start is None) or (start > max_start):
                errors["start"] = _("Some submitted timesheet entries start at {start}").format(
                    start=max_start,
                )
            if (end is None) or (end < min_end):
                errors["end"] = _("Some submitted timesheet entries end at {end}").format(
                    end=min_end,
                )
            if errors:
                raise ValidationError(errors)

        return self.cleaned_data


class JournalEntryForm(FormMixin, JournalEntryAdminForm):
    leaders = forms.ModelMultipleChoiceField(Leader.objects, label=_("Leaders"), required=False)
    alternates = forms.ModelMultipleChoiceField(Leader.objects, label=_("Alternates"), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.readonly_fields = [
            ReadonlyField(label=_("Subject"), value=self.subject),
        ]

        # only allow to select leaders or alterates with not submitted timesheets
        leaders = self.instance.subject.all_leaders
        alternates = [leader for leader in Leader.objects.all() if leader not in leaders]

        self.fields["leaders"].widget.choices = tuple((leader.id, leader) for leader in leaders)
        self.fields["leaders"].help_text = None
        self.fields["alternates"].widget.choices = tuple((leader.id, leader) for leader in alternates)
        self.fields["alternates"].help_text = None

        if self.instance.id:
            self.initial["leaders"] = [leader.id for leader in self.instance.all_leaders]
            self.initial["alternates"] = [leader.id for leader in self.instance.all_alternates]
        else:
            self.initial["leaders"] = [leader.id for leader in leaders]

    def clean(self):
        self.cleaned_data = super().clean()
        self.cleaned_entries = []
        self.deleted_entries = []

        d = self.cleaned_data.get("date", self.instance.date)
        if d is None:
            # no other validation makes sense without date
            return self.cleaned_data

        if (
            "start" in self.cleaned_data
            and "end" in self.cleaned_data
            and self.cleaned_data["start"]
            and self.cleaned_data["end"]
        ):
            errors = {}
            entries_by_leader = {
                "leaders": dict(
                    (entry.timesheet.leader, entry)
                    for entry in self.instance.all_leader_entries
                    if entry.timesheet.leader in self.instance.all_leaders
                ),
                "alternates": dict(
                    (entry.timesheet.leader, entry)
                    for entry in self.instance.all_leader_entries
                    if entry.timesheet.leader in self.instance.all_alternates
                ),
            }
            leaders_with_submitted_timesheets = {}
            period = TimesheetPeriod.objects.for_date(d)

            for group in ("leaders", "alternates"):
                leaders_with_submitted_timesheets[group] = []
                for leader in self.cleaned_data[group]:
                    if leader not in entries_by_leader[group]:
                        # try to create new leader entry
                        timesheet = Timesheet.objects.for_leader_and_date(leader=leader, date=d)
                        if timesheet.submitted:
                            # can not create entry
                            leaders_with_submitted_timesheets[group].append(leader)
                            continue
                        entry = JournalLeaderEntry()
                        entry.journal_entry = self.instance
                        entry.timesheet = timesheet
                        entry.start = self.cleaned_data["start"]
                        entry.end = self.cleaned_data["end"]
                    else:
                        # try to update existing leader entry
                        entry = entries_by_leader[group].pop(leader)
                        if not entry.timesheet.submitted:
                            if self.cleaned_data["start"] != self.instance.start:
                                if entry.start == self.instance.start:
                                    entry.start = self.cleaned_data["start"]
                                else:
                                    entry.start = max(entry.start, self.cleaned_data["start"])
                            if self.cleaned_data["end"] != self.instance.end:
                                if entry.end == self.instance.end:
                                    entry.end = self.cleaned_data["end"]
                                else:
                                    entry.end = min(entry.end, self.cleaned_data["end"])
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

            if leaders_with_submitted_timesheets["leaders"]:
                errors["leaders"] = ungettext(
                    "Leader {leaders} has already submitted timesheet for {period}.",
                    "Leaders {leaders} have already submitted timesheet for {period}.",
                    len(leaders_with_submitted_timesheets["leaders"]),
                ).format(
                    leaders=comma_separated(leaders_with_submitted_timesheets["leaders"]),
                    period=period.name,
                )
            if leaders_with_submitted_timesheets["alternates"]:
                errors["alternates"] = ungettext(
                    "Alternate {leaders} has already submitted timesheet for {period}.",
                    "Alternates {leaders} have already submitted timesheet for {period}.",
                    len(leaders_with_submitted_timesheets["alternates"]),
                ).format(
                    leaders=comma_separated(leaders_with_submitted_timesheets["alternates"]),
                    period=period.name,
                )
            if errors:
                raise ValidationError(errors)

        return self.cleaned_data

    def save(self, commit=True):
        self.instance = super().save(commit)
        for entry in self.cleaned_entries:
            entry.journal_entry = self.instance
            entry.save()
        for entry in self.deleted_entries:
            entry.delete()
