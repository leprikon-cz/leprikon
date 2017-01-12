from __future__ import unicode_literals

import colorsys
from datetime import date
from json import loads

from cms.models import CMSPlugin
from cms.models.fields import PageField
from django.core.urlresolvers import reverse_lazy as reverse
from django.db import models
from django.utils.encoding import force_text, python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from djangocms_text_ckeditor.fields import HTMLField
from filer.fields.file import FilerFileField
from filer.fields.image import FilerImageField

from ..conf import settings
from ..mailers import EventRegistrationMailer
from ..utils import comma_separated, currency
from .agegroup import AgeGroup
from .fields import ColorField, PriceField
from .place import Place
from .question import Question
from .registrations import Registration
from .roles import Leader
from .schoolyear import SchoolYear
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
    place       = models.ForeignKey(Place, verbose_name=_('place'), related_name='events', blank=True, null=True, on_delete=models.SET_NULL)
    age_groups  = models.ManyToManyField(AgeGroup, verbose_name=_('age groups'), related_name='events', blank=True)
    leaders     = models.ManyToManyField(Leader, verbose_name=_('leaders'), related_name='events', blank=True)
    price       = PriceField(_('price'), blank=True, null=True)
    public      = models.BooleanField(_('public'), default=False)
    reg_active  = models.BooleanField(_('active registration'), default=False)
    photo       = FilerImageField(verbose_name=_('photo'), related_name='+', blank=True, null=True)
    page        = PageField(verbose_name=_('page'), related_name='+', blank=True, null=True, on_delete=models.SET_NULL)
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

    def save(self, *args, **kwargs):
        if self.price is None:
            self.reg_active = False
        super(Event, self).save(*args, **kwargs)

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
        return set(self.event_type.all_questions + list(self.questions.all()))

    @cached_property
    def all_attachments(self):
        return list(self.attachments.all())

    @cached_property
    def all_registrations(self):
        return list(self.registrations.all())

    def get_absolute_url(self):
        return reverse('leprikon:event_detail', args=(self.event_type.slug, self.id))

    def get_registration_url(self):
        return reverse('leprikon:event_registration_form', kwargs={'event_type': self.event_type.slug, 'pk': self.id})

    def get_edit_url(self):
        return reverse('admin:leprikon_event_change', args=(self.id,))

    def get_groups_list(self):
        return comma_separated(self.all_groups)
    get_groups_list.short_description = _('groups list')

    def get_leaders_list(self):
        return comma_separated(self.all_leaders)
    get_leaders_list.short_description = _('leaders list')

    @property
    def active_registrations(self):
        return self.registrations.filter(canceled=None)

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



class EventRegistration(Registration):
    event           = models.ForeignKey(Event, verbose_name=_('event'), related_name='registrations')
    discount        = PriceField(_('discount'), default=0)
    explanation     = models.TextField(_('discount explanation'), blank=True, default='')

    class Meta:
        app_label           = 'leprikon'
        verbose_name        = _('event registration')
        verbose_name_plural = _('event registrations')
        unique_together     = (('event', 'participant_birth_num'),)

    def get_answers(self):
        return loads(self.answers)

    @property
    def subject(self):
        return self.event

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

    def send_mail(self):
        EventRegistrationMailer().send_mail(self)



@python_2_unicode_compatible
class EventRegistrationRequest(models.Model):
    user    = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user'), related_name='event_registration_requests', blank=True, null=True)
    event   = models.ForeignKey(Event, verbose_name=_('event'), related_name='registration_requests')
    created = models.DateTimeField(_('time of request'), editable=False, auto_now_add=True)
    contact = models.CharField(_('contact'), max_length=150, help_text=_('Enter phone number, e-mail address or other contact.'))

    class Meta:
        app_label           = 'leprikon'
        verbose_name        = _('event registration request')
        verbose_name_plural = _('event registration requests')
        ordering            = ('created',)
        unique_together     = (('user', 'event'),)

    def __str__(self):
        return '{user}, {event}'.format(
            user    = self.user,
            event   = self.event,
        )



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



class EventPlugin(CMSPlugin):
    event       = models.ForeignKey(Event, verbose_name=_('event'))
    template    = models.CharField(_('template'), max_length=100,
                    choices=settings.LEPRIKON_EVENT_TEMPLATES,
                    default=settings.LEPRIKON_EVENT_TEMPLATES[0][0],
                    help_text=_('The template used to render plugin.'))

    class Meta:
        app_label = 'leprikon'



class EventListPlugin(CMSPlugin):
    school_year = models.ForeignKey(SchoolYear, verbose_name=_('school year'),
                    blank=True, null=True)
    event_type  = models.ForeignKey(EventType, verbose_name=_('event type'))
    age_groups  = models.ManyToManyField(AgeGroup, verbose_name=_('age groups'),
                    blank=True,
                    help_text=_('Keep empty to skip searching by age groups.'))
    groups      = models.ManyToManyField(EventGroup, verbose_name=_('event groups'),
                    blank=True,
                    help_text=_('Keep empty to skip searching by groups.'))
    leaders     = models.ManyToManyField(Leader, verbose_name=_('leaders'),
                    blank=True,
                    help_text=_('Keep empty to skip searching by leaders.'))
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



class FilteredEventListPlugin(CMSPlugin):
    school_year = models.ForeignKey(SchoolYear, verbose_name=_('school year'),
                    blank=True, null=True)
    event_types = models.ManyToManyField(EventType, verbose_name=_('event type'))

    class Meta:
        app_label = 'leprikon'

    def copy_relations(self, oldinstance):
        self.event_types = oldinstance.event_types.all()

