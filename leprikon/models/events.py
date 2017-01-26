from __future__ import unicode_literals

from datetime import date, datetime

from django.db import models
from django.utils.formats import date_format, time_format
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from .subjects import Subject, SubjectDiscount, SubjectRegistration
from .utils import PaymentStatus


class Event(Subject):
    start_date  = models.DateField(_('start date'))
    end_date    = models.DateField(_('end date'))
    start_time  = models.TimeField(_('start time'), blank=True, null=True)
    end_time    = models.TimeField(_('end time'), blank=True, null=True)

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('start_date', 'start_time')
        verbose_name        = _('event')
        verbose_name_plural = _('events')

    @property
    def inactive_registrations(self):
        return self.registrations.filter(canceled__isnull=False)

    def get_active_registrations(self, d):
        return self.registrations.filter(created__lte=d).exclude(canceled__lt=d)

    def get_times_list(self):
        return '{start}{separator}{end}'.format(
            start = (date_format(datetime.combine(self.start_date, self.start_time), 'SHORT_DATETIME_FORMAT')
                     if self.start_time else date_format(self.start_date, 'SHORT_DATE_FORMAT')),
            separator = ' - ' if self.start_date != self.end_date or self.end_time is not None else '',
            end = ((time_format(self.end_time, 'TIME_FORMAT') if self.end_time else '')
                   if self.start_date == self.end_date
                   else (date_format(datetime.combine(self.end_date, self.end_time), 'SHORT_DATETIME_FORMAT')
                         if self.end_time else date_format(self.end_date, 'SHORT_DATE_FORMAT'))),
        )
    get_times_list.short_description = _('times')

    def copy_to_school_year(old, school_year):
        new = Event.objects.get(id=old.id)
        new.id = None
        new.school_year = school_year
        new.public      = False
        new.evaluation  = ''
        new.note        = ''
        year_offset = school_year.year - old.school_year.year
        if new.reg_from:
            try:
                new.reg_from = datetime(
                    new.reg_from.year + year_offset,
                    new.reg_from.month,
                    new.reg_from.day,
                    new.reg_from.hour,
                    new.reg_from.minute,
                    new.reg_from.second,
                )
            except ValueError:
                # handle leap-year
                new.reg_from = datetime(
                    new.reg_from.year + year_offset,
                    new.reg_from.month,
                    new.reg_from.day - 1,
                    new.reg_from.hour,
                    new.reg_from.minute,
                    new.reg_from.second,
                )
        if new.reg_to:
            try:
                new.reg_to = datetime(
                    new.reg_to.year + year_offset,
                    new.reg_to.month,
                    new.reg_to.day,
                    new.reg_to.hour,
                    new.reg_to.minute,
                    new.reg_to.second,
                )
            except ValueError:
                # handle leap-year
                new.reg_to = datetime(
                    new.reg_to.year + year_offset,
                    new.reg_to.month,
                    new.reg_to.day - 1,
                    new.reg_to.hour,
                    new.reg_to.minute,
                    new.reg_to.second,
                )
        try:
            new.start_date = date(new.start_date.year + year_offset, new.start_date.month, new.start_date.day)
        except ValueError:
            # handle leap-year
            new.start_date = date(new.start_date.year + year_offset, new.start_date.month, new.start_date.day - 1)
        try:
            new.end_date   = date(new.end_date.year   + year_offset, new.end_date.month,   new.end_date.day)
        except ValueError:
            # handle leap-year
            new.end_date   = date(new.end_date.year   + year_offset, new.end_date.month,   new.end_date.day - 1)
        new.save()
        new.groups      = old.groups.all()
        new.age_groups  = old.age_groups.all()
        new.leaders     = old.leaders.all()
        new.questions   = old.questions.all()
        new.attachments = old.attachments.all()
        return new



class EventRegistration(SubjectRegistration):

    class Meta:
        app_label           = 'leprikon'
        verbose_name        = _('event registration')
        verbose_name_plural = _('event registrations')

    @cached_property
    def payment_status(self):
        return self.get_payment_status()

    def get_payment_status(self, d=None):
        return PaymentStatus(
            price       = self.price,
            discount    = self.get_discounted(d),
            paid        = self.get_paid(d),
        )



class EventDiscount(SubjectDiscount):
    registration    = models.ForeignKey(EventRegistration, verbose_name=_('registration'),
                                        related_name='discounts', on_delete=models.PROTECT)
