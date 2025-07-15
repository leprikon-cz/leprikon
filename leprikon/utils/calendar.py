from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from itertools import chain, product
from typing import Iterable, Iterator, Optional

from dateutil.rrule import DAILY, FR, MO, SA, SU, TH, TU, WE, rrule, weekday
from django.db.models import IntegerChoices
from django.utils.translation import gettext_lazy as _

from . import comma_separated


def start_time_format(start: time) -> str:
    return start.strftime("%H:%M")


def end_time_format(end: time) -> str:
    return "24:00" if end == time(0) else end.strftime("%H:%M")


def time_slot_format(start_time: time, end_time: time) -> str:
    return _("{start_time} - {end_time}").format(
        start_time=start_time_format(start_time), end_time=end_time_format(end_time)
    )


class DayOfWeek(IntegerChoices):
    MONDAY = 1 << 0, _("Monday")
    TUESDAY = 1 << 1, _("Tuesday")
    WEDNESDAY = 1 << 2, _("Wednesday")
    THURSDAY = 1 << 3, _("Thursday")
    FRIDAY = 1 << 4, _("Friday")
    SATURDAY = 1 << 5, _("Saturday")
    SUNDAY = 1 << 6, _("Sunday")

    def isoweekday(self) -> int:
        """
        Returns the ISO weekday number (1=Monday, 7=Sunday).
        """
        return {
            self.MONDAY: 1,
            self.TUESDAY: 2,
            self.WEDNESDAY: 3,
            self.THURSDAY: 4,
            self.FRIDAY: 5,
            self.SATURDAY: 6,
            self.SUNDAY: 7,
        }[
            self  # type: ignore
        ]

    @classmethod
    def from_isoweekday(cls, iso_weekday: int) -> "DayOfWeek":
        """
        Returns the DayOfWeek from an ISO weekday number (1=Monday, 7=Sunday).
        """
        return [
            cls.SUNDAY,
            cls.MONDAY,
            cls.TUESDAY,
            cls.WEDNESDAY,
            cls.THURSDAY,
            cls.FRIDAY,
            cls.SATURDAY,
            cls.SUNDAY,
        ][iso_weekday]


class DaysOfWeek(list[DayOfWeek]):

    def __init__(self, value: int | Iterable[DayOfWeek] = 0) -> None:
        if isinstance(value, (int, DayOfWeek)):
            return super().__init__(day for day in DayOfWeek if value & day)
        return super().__init__(DayOfWeek(day) for day in value)

    def int(self) -> int:
        return sum(int(i) for i in self)

    def __str__(self) -> str:
        i = self.int()
        parts = []
        sequence = []
        for day in DayOfWeek:
            available = day & i
            if available:
                sequence.append(day.label)
            if (not available or day == DayOfWeek.SUNDAY) and sequence:
                if len(sequence) == 1:
                    parts.append(sequence[0])
                else:
                    parts.append(f"{sequence[0]} - {sequence[-1]}")
                sequence = []
        return comma_separated(parts)

    def __and__(self, other: "DaysOfWeek") -> "DaysOfWeek":
        return DaysOfWeek(self.int() & other.int())

    @classmethod
    def all(cls) -> "DaysOfWeek":
        """
        Returns all days of the week.
        """
        return DaysOfWeek(DayOfWeek)


@dataclass
class WeeklyTime:
    """
    Represents a weekly time range.
    If end_time is 0:00, it actually means 24:00 (end of the day)
    """

    start_date: Optional[date]
    end_date: Optional[date]
    days_of_week: DaysOfWeek
    start_time: time
    end_time: time

    def __str__(self):
        return _("{days}, {time}").format(
            days=self.days_of_week,
            time=time_slot_format(self.start_time, self.end_time),
        )

    def __bool__(self) -> bool:
        if not self.days_of_week:
            return False
        if self.start_time >= self.end_time and self.end_time != time(0):
            return False
        if self.start_date and self.end_date and self.start_date > self.end_date:
            return False
        return True

    def __and__(self, other: "WeeklyTime") -> Optional["WeeklyTime"]:
        return (
            WeeklyTime(
                start_date=(
                    max(self.start_date, other.start_date)
                    if self.start_date and other.start_date
                    else self.start_date or other.start_date
                ),
                end_date=(
                    min(self.end_date, other.end_date)
                    if self.end_date and other.end_date
                    else self.end_date or other.end_date
                ),
                days_of_week=DaysOfWeek(self.days_of_week & other.days_of_week),
                start_time=max(self.start_time, other.start_time),
                # if any of the end times is 0:00:00 (which means EOD), use the other one
                end_time=(
                    max(self.end_time, other.end_time)
                    if time(0) in (self.end_time, other.end_time)
                    else min(self.end_time, other.end_time)
                ),
            )
            or None
        )

    @classmethod
    def unlimited(cls) -> "WeeklyTime":
        return WeeklyTime(None, None, DaysOfWeek.all(), time(0), time(0))


class WeeklyTimes(list[WeeklyTime]):
    def __and__(self, other: "WeeklyTimes") -> "WeeklyTimes":
        return WeeklyTimes(a for a in [a1 & a2 for a1, a2 in product(self, other)] if a)

    def __str__(self):
        return comma_separated(self)

    @classmethod
    def unlimited(cls) -> "WeeklyTimes":
        return WeeklyTimes([WeeklyTime.unlimited()])


@dataclass
class TimeSlot:
    start: datetime
    end: datetime

    def __hash__(self) -> int:
        return hash((self.start, self.end))

    def __post_init__(self):
        assert self.start < self.end

    def __and__(self, other: "TimeSlot") -> "TimeSlots":
        if self.start < other.end and self.end > other.start:
            return TimeSlots([TimeSlot(max(self.start, other.start), min(self.end, other.end))])
        return TimeSlots()

    def __or__(self, other: "TimeSlot") -> "TimeSlots":
        return TimeSlots([self, other])

    def __sub__(self, other: "TimeSlot | TimeSlots") -> "TimeSlots":
        if isinstance(other, TimeSlot):
            if self.start >= other.end or self.end <= other.start:
                return TimeSlots([self])
            elif self.start < other.start:
                if self.end > other.end:
                    return TimeSlots(
                        [
                            TimeSlot(self.start, other.start),
                            TimeSlot(other.end, self.end),
                        ]
                    )
                else:
                    return TimeSlots([TimeSlot(self.start, other.start)])
            else:
                if self.end > other.end:
                    return TimeSlots([TimeSlot(other.end, self.end)])
                else:
                    return TimeSlots()
        return TimeSlots([self]) - other


class TimeSlots(list[TimeSlot]):
    def __init__(self, time_slots: Iterable[TimeSlot] = []):
        normalized: list[TimeSlot] = []
        for ts in sorted(time_slots, key=lambda ts: (ts.start, ts.end)):
            if not normalized or normalized[-1].end < ts.start:
                normalized.append(ts)
            else:
                normalized[-1].end = max(normalized[-1].end, ts.end)
        super().__init__(normalized)

    def __and__(self, other: "TimeSlots") -> "TimeSlots":
        return TimeSlots(chain.from_iterable(a1 & a2 for a1, a2 in product(self, other)))

    def __or__(self, other: "TimeSlots") -> "TimeSlots":
        return TimeSlots(self + other)

    def __sub__(self, other: "TimeSlot | TimeSlots") -> "TimeSlots":
        if isinstance(other, TimeSlot):
            return TimeSlots(chain.from_iterable(ts - other for ts in self))
        result = TimeSlots(self)
        for ts in other:
            result = result - ts
        return result


@dataclass
class SimpleEvent:
    timeslot: TimeSlot
    resource_groups: list[set[int]]

    def has_resolvable_resource_groups(self) -> bool:
        number_of_resources = len(self.resource_groups)
        return any(len(set(resources)) == number_of_resources for resources in product(*self.resource_groups))


def get_byweekdays_by_days_of_week(days_of_week: DaysOfWeek) -> list[weekday]:
    return [
        {
            DayOfWeek.MONDAY: MO,
            DayOfWeek.TUESDAY: TU,
            DayOfWeek.WEDNESDAY: WE,
            DayOfWeek.THURSDAY: TH,
            DayOfWeek.FRIDAY: FR,
            DayOfWeek.SATURDAY: SA,
            DayOfWeek.SUNDAY: SU,
        }[day]
        for day in days_of_week
    ]


def get_time_slots_by_weekly_times(
    week_times: WeeklyTimes,
    start_date: date,
    end_date: date,
) -> TimeSlots:
    return TimeSlots(
        TimeSlot(
            start=datetime.combine(dt.date(), week_time.start_time),
            end=(
                datetime.combine(dt.date(), week_time.end_time)
                if week_time.end_time != time(0)
                else dt + timedelta(days=1)
            ),
        )
        for week_time in week_times
        for dt in rrule(
            DAILY,
            dtstart=max(week_time.start_date, start_date) if week_time.start_date else start_date,
            until=min(week_time.end_date, end_date) if week_time.end_date else end_date,
            byweekday=get_byweekdays_by_days_of_week(week_time.days_of_week),
        )
    )


def get_unavailable_time_slots(
    available_time_slots: TimeSlots,
    start_date: date,
    end_date: date,
) -> TimeSlots:
    return (
        TimeSlot(
            start=datetime.combine(start_date, time(0)),
            end=datetime.combine(end_date, time(0)) + timedelta(days=1),
        )
        - available_time_slots
    )


def add_event_to_flattened_events(flattened_events: Iterable[SimpleEvent], event: SimpleEvent) -> Iterator[SimpleEvent]:
    """Add an event to an ordered list of non overlaping events."""
    new_event: SimpleEvent | None = event
    for current_event in flattened_events:
        # nothing to merge
        if new_event is None:
            yield current_event
            continue

        # current event before new event
        if current_event.timeslot.end <= new_event.timeslot.start:
            yield current_event
            continue

        # current event after new event
        if current_event.timeslot.start >= new_event.timeslot.end:
            yield new_event
            new_event = None
            yield current_event
            continue

        # first non overlaping part
        if current_event.timeslot.start < new_event.timeslot.start:
            yield SimpleEvent(
                timeslot=TimeSlot(current_event.timeslot.start, new_event.timeslot.start),
                resource_groups=current_event.resource_groups,
            )
        elif new_event.timeslot.start < current_event.timeslot.start:
            yield SimpleEvent(
                timeslot=TimeSlot(new_event.timeslot.start, current_event.timeslot.start),
                resource_groups=new_event.resource_groups,
            )

        # overlaping part
        overlaping_start = max(new_event.timeslot.start, current_event.timeslot.start)
        overlaping_end = min(new_event.timeslot.end, current_event.timeslot.end)
        yield SimpleEvent(
            timeslot=TimeSlot(overlaping_start, overlaping_end),
            resource_groups=current_event.resource_groups + new_event.resource_groups,
        )

        # remaining part of current event
        if current_event.timeslot.end > overlaping_end:
            yield SimpleEvent(
                timeslot=TimeSlot(overlaping_end, current_event.timeslot.end),
                resource_groups=current_event.resource_groups,
            )

        # remaining part of new event
        if new_event.timeslot.end > overlaping_end:
            new_event = SimpleEvent(
                timeslot=TimeSlot(overlaping_end, new_event.timeslot.end),
                resource_groups=new_event.resource_groups,
            )
        else:
            new_event = None

    if new_event:
        yield new_event


def flatten_events(events: Iterable[SimpleEvent]) -> Iterator[SimpleEvent]:
    """Turn possibly overlaping events into non overlaping events by merging them."""
    flattened_events: Iterator[SimpleEvent] = iter(())
    for event in events:
        flattened_events = add_event_to_flattened_events(flattened_events, event)
    return flattened_events


def get_conflicting_timeslots(events: Iterable[SimpleEvent]) -> Iterator[TimeSlot]:
    for event in flatten_events(events):
        if not event.has_resolvable_resource_groups():
            yield event.timeslot


def apply_preparation_and_recovery_times(
    conflicting_time_slots: Iterable[TimeSlot], preparation_time: timedelta, recovery_time: timedelta
) -> TimeSlots:
    """Apply preparation and recovery time to time conflicting times slots.
    Preparation time is applied to the ends of the conflicting timeslots, and vice versa."""
    return TimeSlots(
        TimeSlot(
            start=ts.start - recovery_time,
            end=ts.end + preparation_time,
        )
        for ts in conflicting_time_slots
    )
