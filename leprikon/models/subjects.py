from __future__ import unicode_literals

import colorsys
from collections import OrderedDict
from io import BytesIO
from json import loads

import trml2pdf
from cms.models.fields import PageField
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.urlresolvers import reverse_lazy as reverse
from django.db import models
from django.template.loader import select_template
from django.utils import timezone
from django.utils.encoding import (
    force_text, python_2_unicode_compatible, smart_text,
)
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _
from django_countries.fields import CountryField
from djangocms_text_ckeditor.fields import HTMLField
from filer.fields.file import FilerFileField
from filer.fields.image import FilerImageField
from PyPDF2 import PdfFileReader, PdfFileWriter

from ..conf import settings
from ..utils import comma_separated, currency
from .agegroup import AgeGroup
from .fields import BirthNumberField, ColorField, PostalCodeField, PriceField
from .insurance import Insurance
from .leprikonsite import LeprikonSite
from .place import Place
from .printsetup import PrintSetup
from .question import Question
from .roles import Leader
from .school import School
from .schoolyear import SchoolYear


@python_2_unicode_compatible
class SubjectType(models.Model):
    COURSE = 'course'
    EVENT = 'event'
    subject_type_labels = OrderedDict([
        (COURSE, _('course')),
        (EVENT, _('event')),
    ])
    subject_type_type_labels = OrderedDict([
        (COURSE, _('course type')),
        (EVENT, _('event type')),
    ])
    subject_type    = models.CharField(_('subjects'), max_length=10, choices=subject_type_labels.items())
    name            = models.CharField(_('name'), max_length=150)
    name_genitiv    = models.CharField(_('name (genitiv)'), max_length=150, blank=True)
    name_akuzativ   = models.CharField(_('name (akuzativ)'), max_length=150, blank=True)
    plural          = models.CharField(_('name (plural)'), max_length=150)
    slug            = models.SlugField()
    order           = models.IntegerField(_('order'), blank=True, default=0)
    questions       = models.ManyToManyField(
        Question, verbose_name=_('additional questions'), blank=True, related_name='+',
        help_text=_('Add additional questions to be asked in the registration form.'),
    )
    agreement       = models.TextField(_('registration agreement'), blank=True, null=True)
    reg_print_setup = models.ForeignKey(PrintSetup, on_delete=models.SET_NULL, related_name='+',
                                        verbose_name=_('registration print setup'), blank=True, null=True)

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('order',)
        verbose_name        = _('subject type')
        verbose_name_plural = _('subject types')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.name_genitiv is None:
            self.name_genitiv = self.name
        if self.name_akuzativ is None:
            self.name_akuzativ = self.name
        super(SubjectType, self).save(*args, **kwargs)

    @cached_property
    def all_questions(self):
        return list(self.questions.all())

    @cached_property
    def all_attachments(self):
        return list(self.attachments.all())



@python_2_unicode_compatible
class SubjectTypeAttachment(models.Model):
    subject_type    = models.ForeignKey(SubjectType, verbose_name=_('subject type'), related_name='attachments')
    file            = FilerFileField(related_name='+')
    order           = models.IntegerField(_('order'), blank=True, default=0)

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('order',)
        verbose_name        = _('attachment')
        verbose_name_plural = _('attachments')

    def __str__(self):
        return force_text(self.file)



@python_2_unicode_compatible
class SubjectGroup(models.Model):
    name    = models.CharField(_('name'), max_length=150)
    plural  = models.CharField(_('plural'), max_length=150)
    color   = ColorField(_('color'))
    order   = models.IntegerField(_('order'), blank=True, default=0)
    subject_types = models.ManyToManyField(SubjectType, verbose_name=_('subject type'), related_name='groups')

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('order',)
        verbose_name        = _('subject group')
        verbose_name_plural = _('subject groups')

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
            int(r * 255),
            int(g * 255),
            int(b * 255),
        )



@python_2_unicode_compatible
class Subject(models.Model):
    school_year = models.ForeignKey(SchoolYear, verbose_name=_('school year'), related_name='subjects')
    subject_type = models.ForeignKey(SubjectType, verbose_name=_('subject type'),
                                     related_name='subjects', on_delete=models.PROTECT)
    name        = models.CharField(_('name'), max_length=150)
    description = HTMLField(_('description'), blank=True, default='')
    groups      = models.ManyToManyField(SubjectGroup, verbose_name=_('groups'), related_name='subjects', blank=True)
    place       = models.ForeignKey(Place, verbose_name=_('place'), blank=True, null=True,
                                    related_name='subjects', on_delete=models.SET_NULL)
    age_groups  = models.ManyToManyField(AgeGroup, verbose_name=_('age groups'), related_name='subjects', blank=True)
    leaders     = models.ManyToManyField(Leader, verbose_name=_('leaders'), related_name='subjects', blank=True)
    price       = PriceField(_('price'), blank=True, null=True)
    public      = models.BooleanField(_('public'), default=False)
    reg_from    = models.DateTimeField(_('registration active from'), blank=True, null=True)
    reg_to      = models.DateTimeField(_('registration active to'), blank=True, null=True)
    photo       = FilerImageField(verbose_name=_('photo'), blank=True, null=True,
                                  related_name='+', on_delete=models.SET_NULL)
    page        = PageField(verbose_name=_('page'), blank=True, null=True,
                            related_name='+', on_delete=models.SET_NULL)
    min_count   = models.IntegerField(_('minimal count'), blank=True, null=True)
    max_count   = models.IntegerField(_('maximal count'), blank=True, null=True)
    risks       = HTMLField(_('risks'), blank=True)
    plan        = HTMLField(_('plan'), blank=True)
    evaluation  = HTMLField(_('evaluation'), blank=True)
    note        = models.CharField(_('note'), max_length=300, blank=True, default='')
    questions   = models.ManyToManyField(Question, verbose_name=_('additional questions'),
                                         related_name='+', blank=True,
                                         help_text=_('Add additional questions to be asked in the registration form.'))
    agreement       = models.TextField(_('registration agreement'), blank=True, null=True)
    reg_print_setup = models.ForeignKey(PrintSetup, on_delete=models.SET_NULL, related_name='+',
                                        verbose_name=_('registration print setup'), blank=True, null=True)


    class Meta:
        app_label           = 'leprikon'
        ordering            = ('name',)
        verbose_name        = _('subject')
        verbose_name_plural = _('subjects')

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
        return set(self.subject_type.all_questions + list(self.questions.all()))

    @cached_property
    def all_attachments(self):
        return list(self.attachments.all())

    @cached_property
    def all_registrations(self):
        return list(self.registrations.all())

    @property
    def registration_allowed(self):
        now = timezone.now()
        return (
            self.price is not None and
            self.reg_from is not None and
            self.reg_from <= now and
            (self.reg_to is None or self.reg_to > now)
        )

    @property
    def full(self):
        return self.max_count and self.active_registrations.count() >= self.max_count

    def get_absolute_url(self):
        return reverse('leprikon:subject_detail', args=(self.subject_type.slug, self.id))

    def get_registration_url(self):
        return reverse('leprikon:subject_registration_form',
                       kwargs={'subject_type': self.subject_type.slug, 'pk': self.id})

    def get_edit_url(self):
        return reverse('admin:leprikon_subject_change', args=(self.subject_type.slug, self.id))

    def get_groups_list(self):
        return comma_separated(self.all_groups)
    get_groups_list.short_description = _('groups list')

    def get_leaders_list(self):
        return comma_separated(self.all_leaders)
    get_leaders_list.short_description = _('leaders list')

    @property
    def active_registrations(self):
        return self.registrations.filter(canceled=None)

    def get_agreement(self):
        return (
            self.agreement or
            self.subject_type.agreement or
            LeprikonSite.objects.get_current().agreement or
            _('I confirm that I have read, understood and agree with the Terms and Conditions. '
              'The terms and conditions are available on the web.')
        )



@python_2_unicode_compatible
class SubjectAttachment(models.Model):
    subject = models.ForeignKey(Subject, verbose_name=_('subject'), related_name='attachments')
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
class SubjectRegistration(models.Model):
    slug            = models.SlugField(editable=False)
    created         = models.DateTimeField(_('time of registration'), editable=False, auto_now_add=True)
    user            = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user'),
                                        related_name='leprikon_registrations', on_delete=models.PROTECT)
    subject         = models.ForeignKey(Subject, verbose_name=_('subject'),
                                        related_name='registrations', on_delete=models.PROTECT)
    price           = PriceField(_('price'), editable=False)
    answers         = models.TextField(_('additional answers'), blank=True, default='{}', editable=False)

    approved        = models.DateTimeField(_('time of approval'), editable=False, null=True)
    canceled        = models.DateTimeField(_('time of cancellation'), editable=False, null=True)
    cancel_request  = models.BooleanField(_('cancel request'), default=False)

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
        app_label           = 'leprikon'
        verbose_name        = _('registration')
        verbose_name_plural = _('registrations')
        unique_together     = (('subject', 'participant_birth_num'),)

    def __str__(self):
        return _('{participant} ({birth_num})').format(
            participant = self.participant,
            birth_num   = self.participant_birth_num,
        )

    def validate_unique(self, exclude=None):
        try:
            # perform the all unique checks, do not exclude anything
            super(SubjectRegistration, self).validate_unique(None)
        except ValidationError:
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
        return self.Person(self, 'participant')
    participant.short_description = _('participant')

    @cached_property
    def parents(self):
        return list(p for p in [self.parent1, self.parent2] if p is not None)

    @cached_property
    def parent1(self):
        if self.has_parent1:
            return self.Person(self, 'parent1')
        else:
            return None
    parent1.short_description = _('first parent')

    @cached_property
    def parent2(self):
        if self.has_parent2:
            return self.Person(self, 'parent2')
        else:
            return None
    parent2.short_description = _('second parent')

    @cached_property
    def all_attachments(self):
        return self.subject.all_attachments + self.subject.subject_type.all_attachments

    @cached_property
    def all_recipients(self):
        recipients = set()
        if self.user.email:
            recipients.add(self.user.email)
        for parent in self.parents:
            if parent.email:
                recipients.add(parent.email)
        return recipients

    @cached_property
    def all_discounts(self):
        return list(self.discounts.all())

    @cached_property
    def all_payments(self):
        return list(self.payments.all())

    def get_discounts(self, d):
        if d:
            return list(filter(lambda p: p.created.date() <= d, self.all_discounts))
        else:
            return self.all_discounts

    def get_payments(self, d):
        if d:
            return list(filter(lambda p: p.created.date() <= d, self.all_payments))
        else:
            return self.all_payments

    def get_discounted(self, d=None):
        return sum(p.amount for p in self.get_discounts(d))

    def get_paid(self, d=None):
        return sum(p.amount for p in self.get_payments(d))

    def get_absolute_url(self):
        return reverse('leprikon:registration_pdf', kwargs={'slug': self.slug})

    def approve(self):
        if self.approved is None:
            self.approved = timezone.now()
            self.save()

    def cancel(self):
        if self.canceled is None:
            self.canceled = timezone.now()
            self.save()

    def save(self, *args, **kwargs):
        self.participant_gender = self.participant_birth_num[2:4] > '50' and self.FEMALE or self.MALE
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
        super(SubjectRegistration, self).save(*args, **kwargs)

    def send_mail(self):
        # get plain pdf from rml
        template_txt = select_template([
            'leprikon/registration-mail/{}.txt'.format(self.subject.subject_type.slug),
            'leprikon/registration-mail/{}.txt'.format(self.subject.subject_type.subject_type),
            'leprikon/registration-mail/subject.txt',
        ])
        template_html = select_template([
            'leprikon/registration-mail/{}.html'.format(self.subject.subject_type.slug),
            'leprikon/registration-mail/{}.html'.format(self.subject.subject_type.subject_type),
            'leprikon/registration-mail/subject.html',
        ])
        context = {
            'object': self,
            'site': LeprikonSite.objects.get_current(),
        }
        content_txt = template_txt.render(context)
        content_html = template_html.render(context)
        msg = EmailMultiAlternatives(
            subject = _('Registration for {subject_type} accepted').format(
                subject_type=self.subject.subject_type.name_akuzativ
            ),
            body        = content_txt,
            from_email  = settings.SERVER_EMAIL,
            to          = self.all_recipients,
            headers     = {'X-Mailer': 'Leprikon (http://leprikon.cz/)'},
        )
        msg.attach_alternative(content_html, 'text/html')
        msg.attach(self.pdf_filename, self.get_pdf(), 'application/pdf')
        for attachment in self.all_attachments:
            msg.attach_file(attachment.file.file.path)
        msg.send()

    @cached_property
    def agreement(self):
        return self.subject.get_agreement()

    @cached_property
    def print_setup(self):
        return (
            self.subject.reg_print_setup or
            self.subject.subject_type.reg_print_setup or
            LeprikonSite.objects.get_current().reg_print_setup or
            PrintSetup()
        )

    @cached_property
    def pdf_filename(self):
        return self.slug + '.pdf'

    def get_pdf(self):
        output = BytesIO()
        self.write_pdf(output)
        output.seek(0)
        return output.read()

    def write_pdf(self, output):
        # get plain pdf from rml
        template = select_template([
            'leprikon/registration/{}.rml'.format(self.subject.subject_type.slug),
            'leprikon/registration/{}.rml'.format(self.subject.subject_type.subject_type),
            'leprikon/registration/subject.rml',
        ])
        rml_content = template.render({'object': self})
        pdf_content = trml2pdf.parseString(rml_content.encode('utf-8'))

        # merge with background
        if self.print_setup.background:
            template_pdf = PdfFileReader(self.print_setup.background.file)
            registration_pdf = PdfFileReader(BytesIO(pdf_content))
            writer = PdfFileWriter()
            # merge pages from both template and registration
            for i in range(registration_pdf.getNumPages()):
                if i < template_pdf.getNumPages():
                    page = template_pdf.getPage(i)
                    page.mergePage(registration_pdf.getPage(i))
                else:
                    page = registration_pdf.getPage(i)
                writer.addPage(page)
            # write result to output
            writer.write(output)
        else:
            # write basic pdf registration to response
            output.write(pdf_content)
        return output

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
class SubjectDiscount(models.Model):
    created     = models.DateTimeField(_('time of discount'), editable=False, auto_now_add=True)
    amount      = PriceField(_('discount'), default=0)
    explanation = models.CharField(_('discount explanation'), max_length=250, blank=True, default='')

    class Meta:
        abstract            = True
        app_label           = 'leprikon'
        verbose_name        = _('discount')
        verbose_name_plural = _('discounts')
        ordering            = ('created',)

    def __str__(self):
        return currency(self.amount)



@python_2_unicode_compatible
class SubjectPayment(models.Model):
    PAYMENT_CASH = 'PAYMENT_CASH'
    PAYMENT_BANK = 'PAYMENT_BANK'
    PAYMENT_ONLINE = 'PAYMENT_ONLINE'
    PAYMENT_TRANSFER = 'PAYMENT_TRANSFER'
    RETURN_CASH = 'RETURN_CASH'
    RETURN_BANK = 'RETURN_BANK'
    RETURN_TRANSFER = 'RETURN_TRANSFER'
    payment_type_labels = OrderedDict([
        (PAYMENT_CASH, _('payment - cash')),
        (PAYMENT_BANK, _('payment - bank')),
        (PAYMENT_ONLINE, _('payment - online')),
        (PAYMENT_TRANSFER, _('payment - transfer from return')),
        (RETURN_CASH, _('return - cash')),
        (RETURN_BANK, _('return - bank')),
        (RETURN_TRANSFER, _('return - transfer to payment')),
    ])
    registration    = models.ForeignKey(SubjectRegistration, verbose_name=_('registration'),
                                        related_name='payments', on_delete=models.PROTECT)
    created         = models.DateTimeField(_('payment time'), editable=False, auto_now_add=True)
    payment_type    = models.CharField(_('payment type'), max_length=30, choices=payment_type_labels.items())
    amount          = PriceField(_('amount'), help_text=_('positive value for payment, negative value for return'))
    note            = models.CharField(_('note'), max_length=300, blank=True, default='')
    related_payment = models.ForeignKey('self', verbose_name=_('related payment'), blank=True, null=True,
                                        related_name='related_payments', on_delete=models.PROTECT)

    payments = frozenset({PAYMENT_CASH, PAYMENT_BANK, PAYMENT_ONLINE, PAYMENT_TRANSFER})
    returns = frozenset({RETURN_CASH, RETURN_BANK, RETURN_TRANSFER})

    class Meta:
        app_label           = 'leprikon'
        verbose_name        = _('payment')
        verbose_name_plural = _('payments')
        ordering            = ('created',)

    def __str__(self):
        return '{registration}, {payment_type} {amount}'.format(
            registration    = self.registration,
            payment_type    = self.payment_type_label,
            amount          = currency(abs(self.amount)),
        )

    @cached_property
    def payment_type_label(self):
        return self.payment_type_labels.get(self.payment_type, '-')
    payment_type_label.short_description = _('payment type')

    def validate(self):
        if self.amount == 0:
            raise ValidationError({
                'amount': [_('Amount can not be zero.')]
            })
        if self.payment_type:
            if self.amount > 0 and self.payment_type not in self.payments:
                raise ValidationError({
                    'payment_type': [_('Select one of the payments or use negative amount.')],
                })
            if self.amount < 0 and self.payment_type not in self.returns:
                raise ValidationError({
                    'payment_type': [_('Select one of the returns or use positive amount.')],
                })

    def clean_fields(self, exclude=None):
        super(SubjectPayment, self).clean_fields(exclude)
        self.validate()

    def save(self, *args, **kwargs):
        self.validate()
        super(SubjectPayment, self).save(*args, **kwargs)
