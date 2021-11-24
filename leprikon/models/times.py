from collections import namedtuple
from datetime import date, datetime, time, timedelta

from django.db import models
from django.utils.encoding import force_text
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from ..utils import comma_separated
from .fields import DAY_OF_WEEK, DayOfWeekField
from .startend import StartEndMixin


class Time(namedtuple("Time", ("date", "start", "end"))):
    def comparable(self):
        return (self.date, self.start or time(0, 0), self.end or time(0, 0))

    def __lt__(self, other):
        return self.comparable() < other.comparable()


class AbstractTime(StartEndMixin, models.Model):
    day_of_week = DayOfWeekField(_("day of week"))
    start = models.TimeField(_("start time"), blank=True, null=True)
    end = models.TimeField(_("end time"), blank=True, null=True)

    class Meta:
        abstract = True
        app_label = "leprikon"
        ordering = ("day_of_week", "start")
        verbose_name = _("time")
        verbose_name_plural = _("times")

    def __str__(self):
        if self.start is not None and self.end is not None:
            return _("{day}, {start:%H:%M} - {end:%H:%M}").format(
                day=self.day,
                start=self.start,
                end=self.end,
            )
        elif self.start is not None:
            return _("{day}, {start:%H:%M}").format(
                day=self.day,
                start=self.start,
            )
        else:
            return force_text(self.day)

    @cached_property
    def day(self):
        return DAY_OF_WEEK[self.day_of_week]

    @property
    def delta(self):
        if self.start is not None and self.end is not None:
            d = date(1, 1, 1)
            return datetime.combine(d, self.end) - datetime.combine(d, self.start)
        else:
            return timedelta(0)

    def get_next_time(self, now=None):
        now = now or datetime.now()
        daydelta = (self.day_of_week - now.isoweekday()) % 7
        if daydelta == 0 and (isinstance(now, date) or self.start is None or self.start <= now.time()):
            daydelta = 7
        if isinstance(now, datetime):
            next_date = now.date() + timedelta(daydelta)
        else:
            next_date = now + timedelta(daydelta)
        return Time(
            date=next_date,
            start=self.start,
            end=self.end,
        )


class TimesMixin:
    @cached_property
    def all_times(self):
        return list(self.times.all())

    def get_times_list(self):
        return comma_separated(self.all_times)

    get_times_list.short_description = _("times")

    def get_next_time(self, now=None):
        try:
            return min(t.get_next_time(now) for t in self.all_times)
        except ValueError:
            return None
