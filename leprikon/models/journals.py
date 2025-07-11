from collections import namedtuple
from datetime import datetime, timedelta
from typing import Optional

from django.db import models
from django.urls import reverse_lazy as reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from djangocms_text_ckeditor.fields import HTMLField

from ..utils import attributes
from .activities import Activity, RegistrationParticipant
from .pdfmail import PdfExportAndMailMixin
from .roles import Leader
from .schoolyear import SchoolYearDivision, SchoolYearPeriod
from .startend import StartEndMixin
from .times import AbstractTime, TimesMixin


class JournalPeriod:
    def __init__(self, journal: "Journal", period: SchoolYearPeriod = None):
        self.journal: Journal = journal
        self.period: Optional[SchoolYearPeriod] = period

    @property
    def all_journal_entries(self):
        return list(self.journal.journal_entries.filter(period=self.period))

    @cached_property
    def all_participants(self):
        if self.period:  # course
            return [
                participant
                for participant in self.journal.all_participants
                if (
                    (self.period.end is None or participant.created.date() <= self.period.end)
                    and (
                        participant.canceled is None
                        or self.period.start is None
                        or participant.canceled.date() >= self.period.start
                    )
                )
            ]
        else:  # event
            return self.journal.all_participants

    @cached_property
    def all_alternates(self):
        alternates = set()
        for entry in self.all_journal_entries:
            for alternate in entry.all_alternates:
                alternates.add(alternate)
        return list(alternates)

    PresenceRecord = namedtuple("PresenceRecord", ("person", "presences"))

    def get_participant_presences(self):
        return [
            self.PresenceRecord(
                participant, [participant.id in entry.all_participants_idset for entry in self.all_journal_entries]
            )
            for participant in self.all_participants
        ]

    def get_leader_presences(self):
        return [
            self.PresenceRecord(
                leader, [entry.all_leader_entries_by_leader.get(leader, None) for entry in self.all_journal_entries]
            )
            for leader in self.journal.all_leaders
        ]

    def get_alternate_presences(self):
        return [
            self.PresenceRecord(
                alternate,
                [entry.all_leader_entries_by_leader.get(alternate, None) for entry in self.all_journal_entries],
            )
            for alternate in self.all_alternates
        ]


class Journal(PdfExportAndMailMixin, TimesMixin, models.Model):
    object_name = "journal"
    activity = models.ForeignKey(
        Activity, on_delete=models.CASCADE, related_name="journals", verbose_name=_("activity")
    )
    school_year_division = models.ForeignKey(
        SchoolYearDivision,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="journals",
        verbose_name=_("school year division"),
    )
    name = models.CharField(_("journal name"), blank=True, default="", max_length=150)
    leaders = models.ManyToManyField(Leader, blank=True, related_name="journals", verbose_name=_("leaders"))
    participants = models.ManyToManyField(
        RegistrationParticipant, blank=True, related_name="journals", verbose_name=_("participants")
    )
    risks = HTMLField(_("risks"), blank=True)
    plan = HTMLField(_("plan"), blank=True)
    evaluation = HTMLField(_("evaluation"), blank=True)

    class Meta:
        app_label = "leprikon"
        verbose_name = _("journal")
        verbose_name_plural = _("journal")

    def __str__(self):
        return f"{self.activity.display_name} - {self.name}" if self.name else self.activity.display_name

    @cached_property
    def all_journal_entries(self):
        return list(self.journal_entries.all())

    @cached_property
    def all_journal_periods(self):
        if self.school_year_division:
            return [JournalPeriod(self, period) for period in self.school_year_division.all_periods]
        return [JournalPeriod(self)]

    @cached_property
    def all_leaders(self):
        return list(self.leaders.all())

    @cached_property
    def all_participants(self):
        return list(
            self.participants.annotate(
                created=models.F("registration__created"),
                approved=models.F("registration__approved"),
                canceled=models.F("registration__canceled"),
            )
        )

    def get_absolute_url(self):
        return reverse("leprikon:journal", kwargs={"pk": self.pk})

    def get_valid_participants(self, d):
        return self.participants.exclude(registration__canceled__date__lt=d)


class JournalTime(AbstractTime):
    journal = models.ForeignKey(Journal, on_delete=models.CASCADE, related_name="times", verbose_name=_("journal"))

    class Meta:
        app_label = "leprikon"
        ordering = ("start_date", "days_of_week", "start_time")
        verbose_name = _("time")
        verbose_name_plural = _("times")


class JournalEntry(StartEndMixin, models.Model):
    journal = models.ForeignKey(
        Journal, editable=False, on_delete=models.PROTECT, related_name="journal_entries", verbose_name=_("journal")
    )
    period = models.ForeignKey(
        SchoolYearPeriod,
        null=True,
        on_delete=models.PROTECT,
        related_name="journal_entries",
        verbose_name=_("school year period"),
    )
    date = models.DateField(_("date"))
    start = models.TimeField(_("start time"), blank=True, null=True)
    end = models.TimeField(_("end time"), blank=True, null=True)
    agenda = HTMLField(_("session agenda"), default="")
    participants = models.ManyToManyField(
        RegistrationParticipant, blank=True, related_name="journal_entries", verbose_name=_("participants")
    )
    participants_instructed = models.ManyToManyField(
        RegistrationParticipant,
        blank=True,
        related_name="instructed",
        verbose_name=_("participants instructed about safety and internal rules"),
    )

    class Meta:
        app_label = "leprikon"
        ordering = ("date", "start", "end")
        verbose_name = _("journal entry")
        verbose_name_plural = _("journal entries")

    def __str__(self):
        return f"{self.journal}, {self.date}, {self.duration}"

    @cached_property
    def datetime_start(self):
        try:
            return datetime.combine(self.date, self.start)
        except TypeError:
            return None

    @cached_property
    def datetime_end(self):
        try:
            return datetime.combine(self.date, self.end)
        except TypeError:
            return None

    @attributes(short_description=_("duration"))
    @cached_property
    def duration(self):
        try:
            return self.datetime_end - self.datetime_start
        except TypeError:
            return timedelta()

    @cached_property
    def all_participants(self):
        return list(self.participants.all())

    @cached_property
    def all_participants_instructed(self):
        return list(self.participants_instructed.all())

    @cached_property
    def all_participants_idset(self):
        return set(r.id for r in self.all_participants)

    @cached_property
    def all_leader_entries(self):
        return list(self.leader_entries.all())

    @cached_property
    def all_leader_entries_by_leader(self):
        return dict((e.timesheet.leader, e) for e in self.all_leader_entries)

    @cached_property
    def all_leaders(self):
        return list(
            le.timesheet.leader for le in self.all_leader_entries if le.timesheet.leader in self.journal.all_leaders
        )

    @cached_property
    def all_alternates(self):
        return list(
            le.timesheet.leader for le in self.all_leader_entries if le.timesheet.leader not in self.journal.all_leaders
        )

    @cached_property
    def affects_submitted_timesheets(self):
        return self.leader_entries.filter(timesheet__submitted=True).exists()

    def save(self, *args, **kwargs):
        if self.end is None:
            self.end = self.start
        super().save(*args, **kwargs)

    def get_edit_url(self):
        return reverse("leprikon:journalentry_update", args=(self.id,))

    def get_delete_url(self):
        return reverse("leprikon:journalentry_delete", args=(self.id,))


class JournalLeaderEntry(StartEndMixin, models.Model):
    journal_entry = models.ForeignKey(
        JournalEntry,
        editable=False,
        on_delete=models.CASCADE,
        related_name="leader_entries",
        verbose_name=_("journal entry"),
    )
    timesheet = models.ForeignKey(
        "leprikon.Timesheet",
        editable=False,
        on_delete=models.PROTECT,
        related_name="journal_entries",
        verbose_name=_("timesheet"),
    )
    start = models.TimeField(_("start time"))
    end = models.TimeField(_("end time"))

    class Meta:
        app_label = "leprikon"
        verbose_name = _("journal leader entry")
        verbose_name_plural = _("journal leader entries")
        unique_together = (("journal_entry", "timesheet"),)

    def __str__(self):
        return f"{self.journal_entry}"

    @attributes(admin_order_field="journal_entry__date", short_description=_("date"))
    @cached_property
    def date(self):
        return self.journal_entry.date

    @attributes(short_description=_("journal"))
    @cached_property
    def journal(self):
        return self.journal_entry.journal

    @attributes(short_description=_("activity"))
    @cached_property
    def activity(self):
        return self.journal_entry.journal.activity

    @cached_property
    def datetime_start(self):
        return datetime.combine(self.date, self.start)

    @cached_property
    def datetime_end(self):
        return datetime.combine(self.date, self.end)

    @attributes(short_description=_("duration"))
    @cached_property
    def duration(self):
        return self.datetime_end - self.datetime_start

    @property
    def group(self):
        return self.activity

    def get_edit_url(self):
        return reverse("leprikon:journalleaderentry_update", args=(self.id,))

    def get_delete_url(self):
        return reverse("leprikon:journalleaderentry_delete", args=(self.id,))
