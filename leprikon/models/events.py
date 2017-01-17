from __future__ import unicode_literals

from datetime import date

from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from .fields import PriceField
from .subjects import Subject, SubjectRegistration
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

    def copy_to_school_year(old, school_year):
        new = Event.objects.get(id=old.id)
        new.id = None
        new.school_year = school_year
        new.public      = False
        new.reg_active  = False
        new.evaluation  = ''
        new.note        = ''
        year_offset = school_year.year - old.school_year.year
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
    discount        = PriceField(_('discount'), default=0)
    explanation     = models.TextField(_('discount explanation'), blank=True, default='')

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
            discount    = self.discount,
            explanation = self.explanation,
            paid        = self.get_paid(d),
        )
