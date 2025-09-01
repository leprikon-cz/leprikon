import uuid
from datetime import date, datetime, time, timedelta
from functools import cached_property
from itertools import chain
from typing import TYPE_CHECKING, Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.template.loader import get_template
from django.urls import reverse
from django.utils.formats import date_format, time_format
from django.utils.translation import gettext_lazy as _
from icalendar import Calendar, Event

from leprikon.models.leprikonsite import LeprikonSite
from leprikon.utils.calendar import (
    SimpleEvent,
    TimeSlot,
    TimeSlots,
    WeeklyTimes,
    get_conflicting_timeslots,
    get_reverse_time_slots,
    get_time_slots_by_weekly_times,
)

from .fields import DaysOfWeek, DaysOfWeekField
from .roles import Leader
from .startend import StartEndMixin
from .times import WeeklyTime

if TYPE_CHECKING:
    from .activities import Activity  # Avoid circular import


class Resource(models.Model):
    name = models.CharField(_("name"), max_length=255)
    leader = models.OneToOneField(
        Leader,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="resource",
        verbose_name=_("leader"),
    )

    class Meta:
        app_label = "leprikon"
        verbose_name = _("resource")
        verbose_name_plural = _("resources")

    def __str__(self):
        return self.name

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.leader:
            self.name = str(self.leader)
        return super().save(force_insert, force_update, using, update_fields)

    @property
    def all_availabilities(self) -> list["ResourceAvailability"]:
        return list(self.availabilities.all())

    @property
    def weekly_times(self) -> WeeklyTimes:
        return (
            WeeklyTimes(availability.weekly_time for availability in self.all_availabilities)
            if self.all_availabilities
            else WeeklyTimes.unlimited()
        )


class ResourceAvailability(StartEndMixin, models.Model):
    resource = models.ForeignKey(
        Resource, on_delete=models.CASCADE, related_name="availabilities", verbose_name=_("resource")
    )
    start_date = models.DateField(_("start date"), blank=True, null=True)
    end_date = models.DateField(_("end date"), blank=True, null=True)
    days_of_week: DaysOfWeek = DaysOfWeekField(_("days of week"))
    start_time: time = models.TimeField(_("start time"), default=time(8, 0))
    end_time: time = models.TimeField(_("end time"), default=time(16, 0))

    class Meta:
        app_label = "leprikon"
        ordering = ("start_time",)
        verbose_name = _("availability")
        verbose_name_plural = _("availabilities")

    @property
    def weekly_time(self) -> WeeklyTime:
        return WeeklyTime(
            start_date=self.start_date,
            end_date=self.end_date,
            days_of_week=self.days_of_week,
            start_time=self.start_time,
            end_time=self.end_time,
        )

    def __str__(self):
        return str(self.weekly_time)

    def __and__(self, other: "ResourceAvailability") -> Optional[WeeklyTime]:
        return self.weekly_time & other.weekly_time


class ResourceGroup(models.Model):
    name = models.CharField(_("name"), max_length=255)
    resources = models.ManyToManyField(Resource, related_name="groups", verbose_name=_("resources"))

    class Meta:
        app_label = "leprikon"
        verbose_name = _("resource group")
        verbose_name_plural = _("resource groups")

    def __str__(self):
        return self.name

    @cached_property
    def all_resources(self) -> list[Resource]:
        return list(self.resources.all())


class CalendarEvent(models.Model):
    name = models.CharField(_("name"), max_length=255)
    activity: Optional["Activity"] = models.ForeignKey(
        "leprikon.Activity",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="calendar_events",
        verbose_name=_("activity"),
    )
    start_date = models.DateField(_("start date"))
    start_time = models.TimeField(_("start time"), blank=True, null=True)
    end_date = models.DateField(_("end date"))
    end_time = models.TimeField(_("end time"), blank=True, null=True)
    effective_start = models.DateTimeField(_("effective start"), editable=False)
    effective_end = models.DateTimeField(_("effective end"), editable=False)
    preparation_time = models.DurationField(
        _("preparation time"),
        default=timedelta(0),
        help_text=_("Time to prepare before the event. (HH:MM:SS)"),
    )
    recovery_time = models.DurationField(
        _("recovery time"),
        default=timedelta(0),
        help_text=_("Time to recover after the event. (HH:MM:SS)"),
    )
    blocks_all_resources = models.BooleanField(
        _("blocks all resources"),
        default=False,
        help_text=_("If checked, the event will block all resources, not just the selected ones."),
    )
    resources = models.ManyToManyField(
        Resource, blank=True, related_name="calendar_events", verbose_name=_("resources")
    )
    resource_groups = models.ManyToManyField(
        ResourceGroup, blank=True, related_name="calendar_events", verbose_name=_("resource groups")
    )
    is_canceled = models.BooleanField(_("is canceled"), default=False)

    class Meta:
        app_label = "leprikon"
        verbose_name = _("calendar event")
        verbose_name_plural = _("calendar events")
        ordering = ("start_date", "start_time")

    def __str__(self) -> str:
        return f"{self.event_time} {self.name}"

    def clean(self):
        errors = {}
        if self.start_date is not None and self.end_date is not None:
            if self.start_date > self.end_date:
                errors.setdefault("start_date", []).append(_("Start date must be before end date."))
                errors.setdefault("end_date", []).append(_("End date must be after start date."))
            if (self.start_time is None) ^ (self.end_time is None):
                if self.start_time is None:
                    errors.setdefault("start_time", []).append(_("Start time must be set for timed events."))
                    errors.setdefault("end_time", []).append(_("End time must be empty for all day events."))
                else:
                    errors.setdefault("start_time", []).append(_("Start time must be empty for all day events."))
                    errors.setdefault("end_time", []).append(_("End time must be set for timed events."))
            if self.start_date == self.end_date and self.start_time is not None and self.start_time > self.end_time:
                errors.setdefault("start_time", []).append(_("Start time must be before end time."))
                errors.setdefault("end_time", []).append(_("End time must be after start time."))
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.effective_start = self.start - self.preparation_time if self.start_time else self.start
        self.effective_end = self.end + self.recovery_time if self.end_time else self.end
        super().save(*args, **kwargs)

    @property
    def start(self) -> datetime:
        return datetime.combine(self.start_date, time(0) if self.start_time is None else self.start_time)

    @property
    def end(self) -> datetime:
        if self.end_time:
            return datetime.combine(self.end_date, self.end_time)
        return datetime.combine(self.end_date + timedelta(days=1), time(0))

    @property
    def timeslot(self) -> TimeSlot:
        return TimeSlot(self.effective_start, self.effective_end)

    @cached_property
    def simple_event(self) -> SimpleEvent:
        return SimpleEvent(
            timeslot=self.timeslot,
            resource_groups=[{resource.id} for resource in self.resources.all()]
            + [
                {resource.id for resource in resource_group.resources.all()}
                for resource_group in self.resource_groups.all()
            ],
        )

    @cached_property
    def all_resources(self) -> list[Resource]:
        return list(self.resources.all())

    @cached_property
    def all_resource_groups(self) -> list[ResourceGroup]:
        return list(self.resource_groups.all())

    @cached_property
    def url(self) -> str:
        leprikon_site = LeprikonSite.objects.get_current()
        uri = reverse("admin:leprikon_calendarevent_change", args=(self.pk,))
        return leprikon_site.url + uri

    @cached_property
    def description(self) -> str:
        template = get_template("leprikon/calendar-export.description.txt")
        return template.render({"event": self})

    @cached_property
    def event_time(self) -> str:
        return "{start} - {end}".format(
            start=(
                date_format(self.start, "SHORT_DATETIME_FORMAT")
                if self.start_time
                else date_format(self.start_date, "SHORT_DATE_FORMAT")
            ),
            end=(
                (
                    date_format(self.end, "SHORT_DATETIME_FORMAT")
                    if self.end_date != self.start_date
                    else time_format(self.end_time)
                )
                if self.end_time
                else date_format(self.end_date, "SHORT_DATE_FORMAT")
            ),
        )

    def has_conflicting_events(self) -> bool:
        if self.is_canceled:
            return False
        relevant_calendar_events_by_timeslot = CalendarEvent.objects.filter(
            effective_start__lt=self.effective_end,
            effective_end__gt=self.effective_start,
            is_canceled=False,
        )
        if relevant_calendar_events_by_timeslot.filter(blocks_all_resources=True).exists():
            return True

        required_resource_groups = self.simple_event.resource_groups
        relevant_resource_ids: set[int] = set(chain.from_iterable(required_resource_groups))
        relevant_calendar_events = relevant_calendar_events_by_timeslot.filter(blocks_all_resources=False).filter(
            models.Q(resources__in=relevant_resource_ids)
            | models.Q(resource_groups__resources__in=relevant_resource_ids)
        )
        relevant_resources = Resource.objects.filter(id__in=relevant_resource_ids).prefetch_related("availabilities")

        events: list[SimpleEvent] = [event.simple_event for event in relevant_calendar_events]

        # unavailable times for each relevant resource
        start_date = self.effective_start.date()
        end_date = self.effective_end.date()
        for resource in relevant_resources:
            available_timeslots = get_time_slots_by_weekly_times(resource.weekly_times, start_date, end_date)
            events.extend(
                SimpleEvent(time_slot, [{resource.id}])
                for time_slot in get_reverse_time_slots(available_timeslots, start_date, end_date)
            )

        return bool(TimeSlots(get_conflicting_timeslots(events)) & self.timeslot)


class CalendarExport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("name"), max_length=255)
    resources = models.ManyToManyField(
        Resource,
        blank=True,
        related_name="calendar_exports",
        verbose_name=_("resources"),
        help_text=_("Select resources to export calendar events for. Leave empty to export events for all resources."),
    )
    export_past_days = models.PositiveSmallIntegerField(_("export past days"), default=30)
    limit_events_count = models.PositiveSmallIntegerField(
        _("limit events count"),
        default=1000,
        help_text=_("Limit the number of events to export. Huge exports may fail to import to Your calendar."),
    )

    class Meta:
        app_label = "leprikon"
        verbose_name = _("calendar export")
        verbose_name_plural = _("calendar exports")

    def __str__(self):
        return self.name

    @cached_property
    def resource_ids(self) -> set[int]:
        return set(self.resources.values_list("id", flat=True))

    @property
    def relevant_events(self) -> models.QuerySet[CalendarEvent]:
        qs = CalendarEvent.objects.filter(
            end_date__gte=date.today() - timedelta(days=self.export_past_days),
            is_canceled=False,
        )
        if self.resource_ids:
            qs = qs.filter(
                models.Q(blocks_all_resources=True)
                | models.Q(resources__in=self.resource_ids)
                | models.Q(resource_groups__resources__in=self.resource_ids)
            )
        return qs

    def get_ical(self) -> str:
        calendar = Calendar()
        calendar.add("prodid", "-//Leprikon//Calendar Export//EN")
        calendar.add("version", "2.0")
        calendar.add("calscale", "GREGORIAN")
        calendar.add("method", "PUBLISH")
        calendar.add("x-wr-calname", self.name)
        calendar.add("x-wr-timezone", settings.TIME_ZONE)
        for event in self.relevant_events[: self.limit_events_count]:
            ical_event = Event()
            ical_event.add("summary", event.name)
            ical_event.add("dtstart", event.start if event.start_time else event.start_date)
            # end date is exclusive if end time is not set
            ical_event.add("dtend", event.end if event.end_time else event.end_date + timedelta(days=1))
            ical_event.add("description", event.description)
            ical_event.add("url", event.url)
            calendar.add_component(ical_event)
        return calendar.to_ical().decode("utf-8")
