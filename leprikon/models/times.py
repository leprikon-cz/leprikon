from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from itertools import product
from typing import Optional

from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from ..utils import attributes, comma_separated
from .fields import DaysOfWeek, DaysOfWeekField
from .startend import StartEndMixin


def start_time_format(start: time) -> str:
    return start.strftime("%H:%M")


def end_time_format(end: time) -> str:
    return "24:00" if end == time(0) else end.strftime("%H:%M")


def time_slot_format(start_time: time, end_time: time) -> str:
    return _("{start_time} - {end_time}").format(
        start_time=start_time_format(start_time), end_time=end_time_format(end_time)
    )


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
    def unlimited(cls) -> "WeeklyTimes":
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
class Time:
    date: date
    start: Optional[time]
    end: Optional[time]

    def _comparable(self) -> "tuple[date, time, time]":
        return (self.date, self.start or time(0), self.end or time(0))

    def __lt__(self, other: "Time") -> bool:
        return self._comparable() < other._comparable()


class AbstractTime(StartEndMixin, models.Model):
    start_date = models.DateField(
        _("start date"),
        blank=True,
        null=True,
        help_text=_("If not set, the time is valid for all dates."),
    )
    end_date = models.DateField(
        _("end date"),
        blank=True,
        null=True,
        help_text=_("If not set, the time is valid for all dates."),
    )
    days_of_week: DaysOfWeek = DaysOfWeekField(_("days of week"))
    start_time: time = models.TimeField(_("start time"), blank=True, null=True)
    end_time: time = models.TimeField(
        _("end time"),
        blank=True,
        null=True,
        help_text=_("If end time is 0:00:00, it means the end of the day (effectively 24:00:00)."),
    )

    class Meta:
        abstract = True

    def __str__(self):
        if self.start_time is not None and self.end_time is not None:
            return _("{days}, {time}").format(
                days=self.days_of_week,
                time=time_slot_format(self.start_time, self.end_time),
            )
        elif self.start_time is not None:
            return _("{days}, {time}").format(
                days=self.days_of_week,
                time=self.start_time.strftime("%H:%M"),
            )
        else:
            return str(self.days_of_week)

    @property
    def weekly_time(self) -> WeeklyTime:
        return WeeklyTime(
            start_date=self.start_date,
            end_date=self.end_date,
            days_of_week=self.days_of_week,
            start_time=time(0) if self.start_time is None else self.start_time,
            end_time=time(0) if self.end_time is None else self.end_time,
        )

    @property
    def delta(self):
        if self.start_time is not None and self.end_time is not None:
            d = date(1, 1, 1)
            return datetime.combine(d, self.end_time) - datetime.combine(d, self.start_time)
        else:
            return timedelta(0)

    def get_next_time(self, now: date | datetime = None):
        now = now or datetime.now()
        now_day = now.isoweekday()
        # If the start time is None or less than now, we want to move to the next day
        force_next_day = isinstance(now, date) or self.start_time is None or self.start_time <= now.time()
        if force_next_day:
            now_day = (now_day + 1) % 7
        daydelta = min((d.isoweekday() - now_day) % 7 for d in self.days_of_week)
        if daydelta == 0 and force_next_day:
            daydelta = 7
        if isinstance(now, datetime):
            next_date = now.date() + timedelta(daydelta)
        else:
            next_date = now + timedelta(daydelta)
        return Time(
            date=next_date,
            start=self.start_time,
            end=self.end_time,
        )


class TimesMixin:
    @cached_property
    def all_times(self):
        return list(self.times.all())

    @attributes(short_description=_("times"))
    def get_times_list(self):
        return comma_separated(self.all_times)

    def get_next_time(self, now=None):
        try:
            return min(t.get_next_time(now) for t in self.all_times)
        except ValueError:
            return None
