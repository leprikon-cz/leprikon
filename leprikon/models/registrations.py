from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.encoding import smart_text
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _
from django_countries.fields import CountryField
from json import loads

from ..conf import settings
from ..utils import reverse

from .agegroup import AgeGroup
from .insurance import Insurance
from .fields import BirthNumberField, PostalCodeField
from .roles import Parent, Participant
from .school import School


@python_2_unicode_compatible
class Person:
    def __init__(self, registration, role):
        self._registration = registration
        self._role = role

    def __getattr__(self, attr):
        return getattr(self._registration, '{}_{}'.format(self._role, attr))

    def __str__(self):
        return self.full_name

    @cached_property
    def full_name(self):
        return '{} {}'.format(self.first_name, self.last_name)

    @cached_property
    def address(self):
        return '{}, {}, {}'.format(self.street, self.city, self.postal_code)

    @cached_property
    def contact(self):
        if self.email and self.phone:
            return '{}, {}'.format(self.phone, self.email)
        else:
            return self.email or self.phone or ''

    # this is participant specific
    @cached_property
    def school_name(self):
        return self.school and smart_text(self.school) or self.school_other

    @cached_property
    def school_and_class(self):
        if self.school_name and self.school_class:
            return '{}, {}'.format(self.school_name, self.school_class)
        else:
            return self.school_name or self.school_class or ''



@python_2_unicode_compatible
class Registration(models.Model):
    slug            = models.SlugField(editable=False)
    created         = models.DateTimeField(_('time of registration'), auto_now_add=True)
    user            = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user'),
                        related_name='leprikon_%(class)ss', on_delete=models.PROTECT)
    answers         = models.TextField(_('additional answers'), blank=True, default='{}', editable=False)

    cancel_request  = models.BooleanField(_('cancel request'), default=False)
    canceled        = models.DateField(_('date of cancellation'), blank=True, null=True)

    MALE = 'm'
    FEMALE = 'f'
    participant_gender      = models.CharField(_('gender'), max_length=1, editable=False,
                                choices=((MALE, _('male')), (FEMALE, _('female'))))
    participant_first_name  = models.CharField(_('first name'),   max_length=30)
    participant_last_name   = models.CharField(_('last name'),    max_length=30)
    participant_birth_num   = BirthNumberField(_('birth number'))
    participant_age_group   = models.ForeignKey(AgeGroup, verbose_name=_('age group'),
                                related_name='+', on_delete=models.PROTECT)
    participant_street      = models.CharField(_('street'),       max_length=150)
    participant_city        = models.CharField(_('city'),         max_length=150)
    participant_postal_code = PostalCodeField(_('postal code'))
    participant_citizenship = CountryField(_('citizenship'))
    participant_insurance   = models.ForeignKey(Insurance, verbose_name=_('insurance'), null=True,
                                related_name='+', on_delete=models.PROTECT)
    participant_phone       = models.CharField(_('phone'),        max_length=30, blank=True, default='')
    participant_email       = models.EmailField(_('email address'),              blank=True, default='')

    participant_school          = models.ForeignKey(School, verbose_name=_('school'), blank=True, null=True,
                                    related_name='+', on_delete=models.PROTECT)
    participant_school_other    = models.CharField(_('other school'), max_length=150, blank=True, default='')
    participant_school_class    = models.CharField(_('class'),        max_length=30,  blank=True, default='')
    participant_health          = models.TextField(_('health'), blank=True, default='')

    has_parent1         = models.BooleanField(_('first parent'), default=False)
    parent1_first_name  = models.CharField(_('first name'),   max_length=30,  blank=True, null=True)
    parent1_last_name   = models.CharField(_('last name'),    max_length=30,  blank=True, null=True)
    parent1_street      = models.CharField(_('street'),       max_length=150, blank=True, null=True)
    parent1_city        = models.CharField(_('city'),         max_length=150, blank=True, null=True)
    parent1_postal_code = PostalCodeField(_('postal code'),                   blank=True, null=True)
    parent1_phone       = models.CharField(_('phone'),        max_length=30,  blank=True, null=True)
    parent1_email       = models.EmailField(_('email address'),               blank=True, null=True)

    has_parent2         = models.BooleanField(_('second parent'), default=False)
    parent2_first_name  = models.CharField(_('first name'),   max_length=30,  blank=True, null=True)
    parent2_last_name   = models.CharField(_('last name'),    max_length=30,  blank=True, null=True)
    parent2_street      = models.CharField(_('street'),       max_length=150, blank=True, null=True)
    parent2_city        = models.CharField(_('city'),         max_length=150, blank=True, null=True)
    parent2_postal_code = PostalCodeField(_('postal code'),                   blank=True, null=True)
    parent2_phone       = models.CharField(_('phone'),        max_length=30,  blank=True, null=True)
    parent2_email       = models.EmailField(_('email address'),               blank=True, null=True)

    class Meta:
        abstract            = True
        app_label           = 'leprikon'
        unique_together     = (('subject', 'birth_num'),)

    def __str__(self):
        return _('{participant} - {subject}').format(
            participant = self.participant,
            subject     = self.subject,
        )

    def validate_unique(self, exclude=None):
        try:
            # perform the all unique checks, do not exclude anything
            super(Registration, self).validate_unique(None)
        except ValidationError as e:
            # The only unique constraint is on birth_num and user.
            # Let's use nice birth_num related message instead of the default one.
            raise ValidationError(
                message={'participant_birth_num': _('Participant with this birth number has already been registered.')},
            )

    def get_answers(self):
        return loads(self.answers)

    def get_questions_and_answers(self):
        answers = self.get_answers()
        for q in self.subject.all_questions:
            yield {
                'question': q.question,
                'answer': answers.get(q.name, ''),
            }

    @cached_property
    def participant(self):
        return Person(self, 'participant')
    participant.short_description = _('participant')

    @cached_property
    def parents(self):
        return list(p for p in [self.parent1, self.parent2] if p is not None)

    @cached_property
    def parent1(self):
        if self.has_parent1:
            return Person(self, 'parent1')
        else:
            return None
    parent1.short_description = _('first parent')

    @cached_property
    def parent2(self):
        if self.has_parent2:
            return Person(self, 'parent2')
        else:
            return None
    parent2.short_description = _('second parent')

    @cached_property
    def all_payments(self):
        return list(self.payments.all())

    @cached_property
    def all_recipients(self):
        recipients = set()
        if self.user.email:
            recipients.add(self.user.email)
        for parent in self.parents:
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

    def get_absolute_url(self):
        return reverse('leprikon:{}_registration_pdf'.format(self.subject._meta.model_name), kwargs={'slug':self.slug})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify('{}-{}-{}'.format(self.participant.birth_num, self.subject.id, self.subject.name))[:50]
        if self.canceled:
            self.cancel_request = False
        if not self.has_parent1:
            if self.has_parent2:
                self.parent1_first_name  = self.parent2_first_name
                self.parent1_last_name   = self.parent2_last_name
                self.parent1_street      = self.parent2_street
                self.parent1_city        = self.parent2_city
                self.parent1_postal_code = self.parent2_postal_code
                self.parent1_phone       = self.parent2_phone
                self.parent1_email       = self.parent2_email
                self.has_parent1 = True
                self.has_parent2 = False
            else:
                self.parent1_first_name  = None
                self.parent1_last_name   = None
                self.parent1_street      = None
                self.parent1_city        = None
                self.parent1_postal_code = None
                self.parent1_phone       = None
                self.parent1_email       = None
        if not self.has_parent2:
            self.parent2_first_name  = None
            self.parent2_last_name   = None
            self.parent2_street      = None
            self.parent2_city        = None
            self.parent2_postal_code = None
            self.parent2_phone       = None
            self.parent2_email       = None
        super(Registration, self).save(*args, **kwargs)

