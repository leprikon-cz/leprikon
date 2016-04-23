from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

import colorsys

from cms.models import CMSPlugin
from cms.models.fields import PageField
from collections import namedtuple
from datetime import date
from django.core.urlresolvers import reverse_lazy as reverse
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.encoding import smart_text, force_text
from django.utils.text import slugify
from django.utils.timezone import localtime
from django.utils.translation import ugettext_lazy as _
from djangocms_text_ckeditor.fields import HTMLField
from filer.fields.file import FilerFileField
from filer.fields.image import FilerImageField
from json import loads

from ..conf import settings
from ..mailers import EventRegistrationMailer
from ..utils import currency, comma_separated

from .fields import ColorField, BirthNumberField, PostalCodeField, PriceField

from .question import Question
from .agegroup import AgeGroup
from .place import Place
from .roles import Leader, Participant
from .school import School
from .schoolyear import SchoolYear
from .startend import StartEndMixin
from .utils import PaymentStatus


@python_2_unicode_compatible
class EventType(models.Model):
    name        = models.CharField(_('name'), max_length=150)
    slug        = models.SlugField()
    order       = models.IntegerField(_('order'), blank=True, default=0)
    questions   = models.ManyToManyField(Question, verbose_name=_('additional questions'),
                    blank=True,
                    help_text=_('Add additional questions to be asked in the registration form.'))

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('order',)
        verbose_name        = _('event type')
        verbose_name_plural = _('event types')

    def __str__(self):
        return self.name

    @cached_property
    def all_questions(self):
        return list(self.questions.all())

    @cached_property
    def all_attachments(self):
        return list(self.attachments.all())



@python_2_unicode_compatible
class EventTypeAttachment(models.Model):
    event   = models.ForeignKey(EventType, verbose_name=_('event type'), related_name='attachments')
    file    = FilerFileField(related_name='+')
    order   = models.IntegerField(_('order'), blank=True, default=0)

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('order',)
        verbose_name        = _('attachment')
        verbose_name_plural = _('attachments')

    def __str__(self):
        return force_text(self.file)



@python_2_unicode_compatible
class EventGroup(models.Model):
    name    = models.CharField(_('name'), max_length=150)
    plural  = models.CharField(_('plural'), max_length=150)
    color   = ColorField(_('color'))
    order   = models.IntegerField(_('order'), blank=True, default=0)

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('order',)
        verbose_name        = _('event group')
        verbose_name_plural = _('event groups')

    def __str__(self):
        return self.name

    @cached_property
    def font_color(self):
        (h, s, v) = colorsys.rgb_to_hsv(
            int(self.color[1:3], 16) / 255.0,
            int(self.color[3:5], 16) / 255.0,
            int(self.color[5:6], 16) / 255.0,
        )
        if v > .5:
            v = 0
        else:
            v = 1
        if s > .5:
            s = 0
        else:
            s = 1
        (r, g, b) = colorsys.hsv_to_rgb(h, s, v)
        return '#{:02x}{:02x}{:02x}'.format(
            int(r*255),
            int(g*255),
            int(b*255),
        )



@python_2_unicode_compatible
class Event(models.Model):
    school_year = models.ForeignKey(SchoolYear, verbose_name=_('school year'), related_name='events')
    name        = models.CharField(_('name'), max_length=150)
    description = HTMLField(_('description'), blank=True, default='')
    start_date  = models.DateField(_('start date'))
    end_date    = models.DateField(_('end date'))
    start_time  = models.TimeField(_('start time'), blank=True, null=True)
    end_time    = models.TimeField(_('end time'), blank=True, null=True)
    event_type  = models.ForeignKey(EventType, verbose_name=_('event type'), related_name='events')
    groups      = models.ManyToManyField(EventGroup, verbose_name=_('groups'), related_name='events')
    place       = models.ForeignKey(Place, verbose_name=_('place'), related_name='events', blank=True, null=True)
    age_groups  = models.ManyToManyField(AgeGroup, verbose_name=_('age groups'), related_name='events', blank=True)
    leaders     = models.ManyToManyField(Leader, verbose_name=_('leaders'), related_name='events', blank=True)
    price       = PriceField(_('price'))
    public      = models.BooleanField(_('public'), default=False)
    reg_active  = models.BooleanField(_('active registration'), default=False)
    photo       = FilerImageField(verbose_name=_('photo'), related_name='+', blank=True, null=True)
    page        = PageField(verbose_name=_('page'), related_name='+', blank=True, null=True)
    min_count   = models.IntegerField(_('minimal count'), blank=True, null=True)
    max_count   = models.IntegerField(_('maximal count'), blank=True, null=True)
    risks       = HTMLField(_('risks'), blank=True)
    plan        = HTMLField(_('plan'), blank=True)
    evaluation  = HTMLField(_('evaluation'), blank=True)
    note        = models.CharField(_('note'), max_length=300, blank=True, default='')
    questions   = models.ManyToManyField(Question, verbose_name=_('additional questions'),
                    blank=True,
                    help_text=_('Add additional questions to be asked in the registration form.'))

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('start_date', 'start_time')
        verbose_name        = _('event')
        verbose_name_plural = _('events')

    def __str__(self):
        return '{} {}'.format(self.school_year, self.name)

    @cached_property
    def all_groups(self):
        return list(self.groups.all())

    @cached_property
    def all_age_groups(self):
        return list(self.age_groups.all())

    @cached_property
    def all_leaders(self):
        return list(self.leaders.all())

    @cached_property
    def all_questions(self):
        return list(self.questions.all())

    @cached_property
    def all_attachments(self):
        return list(self.attachments.all())

    @cached_property
    def all_registrations(self):
        return list(self.registrations.all())

    def get_absolute_url(self):
        return reverse('leprikon:event_detail', args=(self.event_type.slug, self.id))

    def get_public_registration_url(self):
        return reverse('leprikon:event_registration_public', args=(self.id,))

    def get_registration_url(self, participant):
        return reverse('leprikon:event_registration_form', kwargs={'event': self.id, 'participant': participant.id})

    def get_edit_url(self):
        return reverse('admin:leprikon_event_change', args=(self.id,))

    def get_groups_list(self):
        return comma_separated(self.all_groups)
    get_groups_list.short_description = _('groups list')

    def get_leaders_list(self):
        return comma_separated(self.all_leaders)
    get_leaders_list.short_description = _('leaders list')



@python_2_unicode_compatible
class EventAttachment(models.Model):
    event   = models.ForeignKey(Event, verbose_name=_('event'), related_name='attachments')
    file    = FilerFileField(related_name='+')
    order   = models.IntegerField(_('order'), blank=True, default=0)

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('order',)
        verbose_name        = _('attachment')
        verbose_name_plural = _('attachments')

    def __str__(self):
        return force_text(self.file)



@python_2_unicode_compatible
class EventRegistration(models.Model):
    slug            = models.SlugField(editable=False)
    created         = models.DateTimeField(_('time of registration'), editable=False, auto_now_add=True)
    event           = models.ForeignKey(Event, verbose_name=_('event'), related_name='registrations')
    participant     = models.ForeignKey(Participant, verbose_name=_('participant'), related_name='event_registrations')
    age_group       = models.ForeignKey(AgeGroup, verbose_name=_('age group'), related_name='+')
    citizenship     = models.CharField(_('citizenship'),  max_length=50)
    insurance       = models.CharField(_('insurance'),    max_length=50)
    school          = models.ForeignKey(School, verbose_name=_('school'), related_name='event_registrations', blank=True, null=True)
    school_other    = models.CharField(_('other school'), max_length=150, blank=True, default='')
    school_class    = models.CharField(_('class'),        max_length=30,  blank=True, default='')
    health          = models.TextField(_('health'), blank=True, default='')
    answers         = models.TextField(_('additional answers'), blank=True, default='{}', editable=False)
    cancel_request  = models.BooleanField(_('cancel request'), default=False)
    canceled        = models.DateField(_('date of cancellation'), blank=True, null=True)
    discount        = PriceField(_('discount'), default=0)
    explanation     = models.TextField(_('discount explanation'), blank=True, default='')

    class Meta:
        app_label           = 'leprikon'
        verbose_name        = _('event registration')
        verbose_name_plural = _('event registrations')
        unique_together     = (('event', 'participant'),)

    def __str__(self):
        return _('{participant} - {subject}').format(
            participant = self.participant,
            subject     = self.event,
        )

    def get_answers(self):
        return loads(self.answers)

    @property
    def subject(self):
        return self.event

    @cached_property
    def all_payments(self):
        return list(self.payments.all())

    @cached_property
    def school_name(self):
        return self.school and smart_text(self.school) or self.school_other

    @cached_property
    def school_and_class(self):
        if self.school_name and self.school_class:
            return '{}, {}'.format(self.school_name, self.school_class)
        else:
            return self.school_name or self.school_class or ''

    @cached_property
    def all_recipients(self):
        recipients = set()
        if self.participant.user.email:
            recipients.add(self.participant.user.email)
        for parent in self.participant.all_parents:
            if parent.email:
                recipients.add(parent.email)
        return recipients

    def get_payments(self, d=None):
        if d:
            return filter(lambda p: p.date <= d, self.all_payments)
        else:
            return self.all_payments

    def get_paid(self, d=None):
        return sum(p.amount for p in self.get_payments(d))

    @cached_property
    def payment_status(self):
        return self.get_payment_status()

    def get_payment_status(self, d=None):
        return PaymentStatus(
            price       = self.event.price,
            discount    = self.discount,
            paid        = self.get_paid(d),
        )

    def get_absolute_url(self):
        return reverse('leprikon:event_registration_pdf', kwargs={'slug':self.slug})

    def send_mail(self):
        EventRegistrationMailer().send_mail(self)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(smart_text(self))
        if self.canceled:
            self.cancel_request = False
        super(EventRegistration, self).save(*args, **kwargs)



@python_2_unicode_compatible
class EventPayment(models.Model):
    registration    = models.ForeignKey(EventRegistration, verbose_name=_('registration'), related_name='payments', on_delete=models.PROTECT)
    date            = models.DateField(_('payment date'))
    amount          = PriceField(_('amount'))

    class Meta:
        app_label           = 'leprikon'
        verbose_name        = _('event payment')
        verbose_name_plural = _('event payments')

    def __str__(self):
        return '{registration}, {amount}'.format(
            registration    = self.registration,
            amount          = currency(self.amount),
        )



class LeprikonEventListPlugin(CMSPlugin):
    school_year = models.ForeignKey(SchoolYear, verbose_name=_('school year'),
                    blank=True, null=True)
    event_type  = models.ForeignKey(EventType, verbose_name=_('event type'))
    age_groups  = models.ManyToManyField(AgeGroup, verbose_name=_('age groups'),
                    blank=True,
                    help_text=_('Keep empty to skip filtering by age groups.'))
    groups      = models.ManyToManyField(EventGroup, verbose_name=_('event groups'),
                    blank=True,
                    help_text=_('Keep empty to skip filtering by groups.'))
    leaders     = models.ManyToManyField(Leader, verbose_name=_('leaders'),
                    blank=True,
                    help_text=_('Keep empty to skip filtering by leaders.'))
    template    = models.CharField(_('template'), max_length=100,
                    choices=settings.LEPRIKON_EVENTLIST_TEMPLATES,
                    default=settings.LEPRIKON_EVENTLIST_TEMPLATES[0][0],
                    help_text=_('The template used to render plugin.'))

    class Meta:
        app_label = 'leprikon'

    def copy_relations(self, oldinstance):
        self.groups     = oldinstance.groups.all()
        self.age_groups = oldinstance.age_groups.all()
        self.leaders    = oldinstance.leaders.all()



class LeprikonFilteredEventListPlugin(CMSPlugin):
    school_year = models.ForeignKey(SchoolYear, verbose_name=_('school year'),
                    blank=True, null=True)
    event_type  = models.ForeignKey(EventType, verbose_name=_('event type'))

    class Meta:
        app_label = 'leprikon'


