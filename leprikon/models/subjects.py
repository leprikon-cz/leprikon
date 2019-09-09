import colorsys
import logging
from collections import OrderedDict, namedtuple
from email.mime.image import MIMEImage
from io import BytesIO
from itertools import chain
from json import loads

import qrcode
import trml2pdf
from bankreader.models import Transaction as BankreaderTransaction
from cms.models.fields import PageField
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.urlresolvers import reverse_lazy as reverse
from django.db import models, transaction
from django.dispatch import receiver
from django.template.loader import select_template
from django.utils import formats, timezone
from django.utils.encoding import force_text, smart_text
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _
from django_pays import payment_url as pays_payment_url
from django_pays.models import Payment as PaysPayment
from djangocms_text_ckeditor.fields import HTMLField
from filer.fields.file import FilerFileField
from filer.fields.image import FilerImageField
from PyPDF2 import PdfFileReader, PdfFileWriter

from ..conf import settings
from ..utils import (
    comma_separated, currency, get_birth_date, localeconv, spayd,
)
from .agegroup import AgeGroup
from .agreements import Agreement, AgreementOption
from .citizenship import Citizenship
from .department import Department
from .fields import (
    BirthNumberField, ColorField, EmailField, PostalCodeField, PriceField,
)
from .leprikonsite import LeprikonSite
from .place import Place
from .printsetup import PrintSetup
from .question import Question
from .roles import Leader
from .school import School
from .schoolyear import SchoolYear
from .targetgroup import TargetGroup
from .utils import generate_variable_symbol

logger = logging.getLogger(__name__)


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
    subject_type = models.CharField(_('subjects'), max_length=10, choices=subject_type_labels.items())
    name = models.CharField(_('name (singular)'), max_length=150)
    name_genitiv = models.CharField(_('name (genitiv)'), max_length=150, blank=True)
    name_akuzativ = models.CharField(_('name (akuzativ)'), max_length=150, blank=True)
    plural = models.CharField(_('name (plural)'), max_length=150)
    slug = models.SlugField()
    order = models.IntegerField(_('order'), blank=True, default=0)
    questions = models.ManyToManyField(
        Question, verbose_name=_('additional questions'), blank=True, related_name='+',
        help_text=_('Add additional questions to be asked in the registration form.'),
    )
    registration_agreements = models.ManyToManyField(
        Agreement, verbose_name=_('additional legal agreements'), blank=True, related_name='+',
        help_text=_('Add additional legal agreements specific to this subject type.'),
    )
    reg_print_setup = models.ForeignKey(PrintSetup, on_delete=models.SET_NULL, related_name='+',
                                        verbose_name=_('registration print setup'), blank=True, null=True)
    bill_print_setup = models.ForeignKey(PrintSetup, on_delete=models.SET_NULL, related_name='+',
                                         verbose_name=_('payment print setup'), blank=True, null=True)

    class Meta:
        app_label = 'leprikon'
        ordering = ('order',)
        verbose_name = _('subject type')
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


class SubjectTypeAttachment(models.Model):
    subject_type = models.ForeignKey(SubjectType, verbose_name=_('subject type'), related_name='attachments')
    file = FilerFileField(related_name='+')
    order = models.IntegerField(_('order'), blank=True, default=0)

    class Meta:
        app_label = 'leprikon'
        ordering = ('order',)
        verbose_name = _('attachment')
        verbose_name_plural = _('attachments')

    def __str__(self):
        return force_text(self.file)


class SubjectGroup(models.Model):
    name = models.CharField(_('name'), max_length=150)
    plural = models.CharField(_('plural'), max_length=150)
    color = ColorField(_('color'))
    order = models.IntegerField(_('order'), blank=True, default=0)
    subject_types = models.ManyToManyField(SubjectType, verbose_name=_('subject type'), related_name='groups')

    class Meta:
        app_label = 'leprikon'
        ordering = ('order',)
        verbose_name = _('subject group')
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


class Subject(models.Model):
    school_year = models.ForeignKey(SchoolYear, verbose_name=_('school year'), related_name='subjects', editable=False)
    subject_type = models.ForeignKey(SubjectType, verbose_name=_('subject type'),
                                     related_name='subjects', on_delete=models.PROTECT)
    code = models.PositiveSmallIntegerField(_('accounting code'), blank=True, default=0)
    name = models.CharField(_('name'), max_length=150)
    description = HTMLField(_('description'), blank=True, default='')
    department = models.ForeignKey(Department, verbose_name=_('department'), blank=True, null=True,
                                   related_name='subjects', on_delete=models.SET_NULL)
    groups = models.ManyToManyField(SubjectGroup, verbose_name=_('groups'), related_name='subjects', blank=True)
    place = models.ForeignKey(Place, verbose_name=_('place'), blank=True, null=True,
                              related_name='subjects', on_delete=models.SET_NULL)
    age_groups = models.ManyToManyField(AgeGroup, blank=True, verbose_name=_('age groups'), related_name='subjects')
    target_groups = models.ManyToManyField(TargetGroup, blank=True,
                                           verbose_name=_('target groups'), related_name='subjects')
    leaders = models.ManyToManyField(Leader, verbose_name=_('leaders'), related_name='subjects', blank=True)
    price = PriceField(_('price'), blank=True, null=True)
    public = models.BooleanField(_('public'), default=False)
    reg_from = models.DateTimeField(_('registration active from'), blank=True, null=True)
    reg_to = models.DateTimeField(_('registration active to'), blank=True, null=True)
    photo = FilerImageField(verbose_name=_('photo'), blank=True, null=True,
                            related_name='+', on_delete=models.SET_NULL)
    page = PageField(verbose_name=_('page'), blank=True, null=True,
                     related_name='+', on_delete=models.SET_NULL)
    min_participants_count = models.PositiveIntegerField(
        _('minimal participants count per registration'),
        default=1,
        help_text=_('Participant details include birth number (birth day), age group, contacts, parent, etc.'),
    )
    max_participants_count = models.PositiveIntegerField(
        _('maximal participants count per registration'),
        default=1,
        help_text=_('Participant details include birth number (birth day), age group, contacts, parent, etc.'),
    )
    min_group_members_count = models.PositiveIntegerField(
        _('minimal group members count per registration'),
        default=0,
        help_text=_('Group member details only include name and note.'),
    )
    max_group_members_count = models.PositiveIntegerField(
        _('maximal group members count per registration'),
        default=0,
        help_text=_('Group member details only include name and note.'),
    )
    min_registrations_count = models.PositiveIntegerField(_('minimal registrations count'), blank=True, null=True)
    max_registrations_count = models.PositiveIntegerField(_('maximal registrations count'), blank=True, null=True)
    risks = HTMLField(_('risks'), blank=True)
    plan = HTMLField(_('plan'), blank=True)
    evaluation = HTMLField(_('evaluation'), blank=True)
    note = models.CharField(_('note'), max_length=300, blank=True, default='')
    questions = models.ManyToManyField(Question, verbose_name=_('additional questions'),
                                       related_name='+', blank=True,
                                       help_text=_('Add additional questions to be asked in the registration form.'))
    registration_agreements = models.ManyToManyField(
        Agreement, verbose_name=_('additional legal agreements'), blank=True, related_name='+',
        help_text=_('Add additional legal agreements specific for this subject.'),
    )
    reg_print_setup = models.ForeignKey(PrintSetup, on_delete=models.SET_NULL, related_name='+',
                                        verbose_name=_('registration print setup'), blank=True, null=True)
    bill_print_setup = models.ForeignKey(PrintSetup, on_delete=models.SET_NULL, related_name='+',
                                         verbose_name=_('payment print setup'), blank=True, null=True)

    class Meta:
        app_label = 'leprikon'
        ordering = ('code', 'name')
        verbose_name = _('subject')
        verbose_name_plural = _('subjects')

    def __str__(self):
        return '{} {}'.format(self.school_year, self.display_name)

    @cached_property
    def subject(self):
        if self.subject_type.subject_type == self.subject_type.COURSE:
            return self.course
        else:
            return self.event

    @cached_property
    def display_name(self):
        if settings.LEPRIKON_SHOW_SUBJECT_CODE and self.code:
            return '{} – {}'.format(self.code, self.name)
        else:
            return self.name

    @cached_property
    def all_variants(self):
        return list(self.variants.all())

    @cached_property
    def all_groups(self):
        return list(self.groups.all())

    @cached_property
    def all_age_groups(self):
        return list(self.age_groups.all())

    @cached_property
    def all_target_groups(self):
        return list(self.target_groups.all())

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
        return self.max_registrations_count and self.active_registrations_count >= self.max_registrations_count

    def get_absolute_url(self):
        return reverse(self.subject_type.slug + ':subject_detail', args=(self.id,))

    def get_registration_url(self):
        return reverse(self.subject_type.slug + ':subject_registration_form', args=(self.id,))

    def get_edit_url(self):
        return reverse('admin:leprikon_{}_change'.format(self.subject._meta.model_name), args=(self.id,))

    def get_groups_list(self):
        return comma_separated(self.all_groups)
    get_groups_list.short_description = _('groups list')

    def get_leaders_list(self):
        return comma_separated(self.all_leaders)
    get_leaders_list.short_description = _('leaders list')

    @property
    def active_registrations(self):
        return self.registrations.filter(canceled=None)

    @cached_property
    def active_registrations_count(self):
        return self.active_registrations.count()

    @property
    def approved_registrations(self):
        return self.active_registrations.exclude(approved=None)

    @cached_property
    def approved_registrations_count(self):
        return self.approved_registrations.count()

    @cached_property
    def all_approved_registrations(self):
        return list(self.approved_registrations.all())

    @cached_property
    def all_journal_periods(self):
        if self.subject_type.subject_type == self.subject_type.COURSE:
            return [JournalPeriod(self.course, period) for period in self.course.all_periods]
        else:
            return [JournalPeriod(self.event)]

    @property
    def unapproved_registrations(self):
        return self.active_registrations.filter(approved=None)

    @cached_property
    def unapproved_registrations_count(self):
        return self.unapproved_registrations.count()

    @cached_property
    def all_unapproved_registrations(self):
        return list(self.unapproved_registrations.all())

    @cached_property
    def inactive_registrations_count(self):
        return self.inactive_registrations.count()

    @cached_property
    def all_inactive_registrations(self):
        return list(self.inactive_registrations.all())

    @cached_property
    def all_registration_agreements(self):
        return sorted(
            chain(
                self.registration_agreements.all(),
                self.subject_type.registration_agreements.all(),
                LeprikonSite.objects.get_current().registration_agreements.all(),
            ),
            key=lambda agreement: agreement.order
        )


class JournalPeriod:
    def __init__(self, subject, period=None):
        self.subject = subject
        self.period = period

    @property
    def all_journal_entries(self):
        qs = self.subject.journal_entries.all()
        if self.period:
            qs = qs.filter(date__gte=self.period.start, date__lte=self.period.end)
        return list(qs)

    @cached_property
    def all_registrations(self):
        if self.period:  # course
            qs = self.subject.registrations_history_registrations.filter(created__lt=self.period.end)
        else:  # event
            qs = self.subject.registrations.all()
        return list(qs)

    @cached_property
    def all_alternates(self):
        alternates = set()
        for entry in self.all_journal_entries:
            for alternate in entry.all_alternates:
                alternates.add(alternate)
        return list(alternates)

    PresenceRecord = namedtuple('PresenceRecord', ('name', 'presences'))

    def get_participant_presences(self):
        return [
            self.PresenceRecord(
                participant,
                [
                    participant.id in entry.all_participants_idset
                    for entry in self.all_journal_entries
                ]
            )
            for reg in self.all_registrations
            for participant in reg.all_participants
        ]

    def get_leader_presences(self):
        return [
            self.PresenceRecord(
                leader,
                [
                    entry.all_leader_entries_by_leader.get(leader, None)
                    for entry in self.all_journal_entries
                ]
            ) for leader in self.subject.all_leaders
        ]

    def get_alternate_presences(self):
        return [
            self.PresenceRecord(
                alternate,
                [
                    entry.all_leader_entries_by_leader.get(alternate, None)
                    for entry in self.all_journal_entries
                ]
            ) for alternate in self.all_alternates
        ]


class SubjectVariant(models.Model):
    subject = models.ForeignKey(Subject, verbose_name=_('subject'), related_name='variants')
    name = models.CharField(_('variant name'), max_length=150)
    description = HTMLField(_('variant description'), blank=True, default='')
    price = PriceField(_('price'), blank=True, null=True)
    order = models.IntegerField(_('order'), blank=True, default=0)

    class Meta:
        app_label = 'leprikon'
        ordering = ('order',)
        verbose_name = _('variant')
        verbose_name_plural = _('variants')

    def __str__(self):
        return self.name


class SubjectAttachment(models.Model):
    subject = models.ForeignKey(Subject, verbose_name=_('subject'), related_name='attachments')
    file = FilerFileField(related_name='+')
    order = models.IntegerField(_('order'), blank=True, default=0)

    class Meta:
        app_label = 'leprikon'
        ordering = ('order',)
        verbose_name = _('attachment')
        verbose_name_plural = _('attachments')

    def __str__(self):
        return force_text(self.file)


class PdfExportAndMailMixin(object):
    all_attachments = []

    def get_absolute_url(self):
        return reverse('leprikon:{}_pdf'.format(self.object_name), kwargs={'pk': self.pk, 'slug': self.slug})

    def select_template(self, event, suffix):
        return select_template([
            'leprikon/{}_{}/{}.{}'.format(self.object_name, event, param, suffix) for param in (
                self.subject.subject_type.slug,
                self.subject.subject_type.subject_type,
                'subject',
            )
        ])

    def get_context(self):
        return {
            'object': self,
            'site': LeprikonSite.objects.get_current(),
        }

    def get_mail_subject(self, event):
        return self.mail_subject_patterns[event].format(
            subject_type=self.subject.subject_type.name_akuzativ,
            subject=self.subject.name,
        )

    def get_attachments(self, event):
        return None

    def send_mail(self, event='received'):
        template_txt = self.select_template(event, 'txt')
        template_html = self.select_template(event, 'html')
        context = self.get_context()
        content_txt = template_txt.render(context)
        content_html = template_html.render(context)
        EmailMultiAlternatives(
            subject=self.get_mail_subject(event),
            body=content_txt,
            from_email=settings.SERVER_EMAIL,
            to=self.all_recipients,
            headers={'X-Mailer': 'Leprikon (http://leprikon.cz/)'},
            alternatives=[(content_html, 'text/html')],
            attachments=self.get_attachments(event),
        ).send()

    @cached_property
    def pdf_filename(self):
        return self.slug + '.pdf'

    @cached_property
    def pdf_attachment(self):
        return (self.pdf_filename, self.get_pdf(), 'application/pdf')

    def get_pdf(self):
        output = BytesIO()
        self.write_pdf(output)
        output.seek(0)
        return output.read()

    def write_pdf(self, output):
        # get plain pdf from rml
        template = self.select_template('pdf', 'rml')
        rml_content = template.render(self.get_context())
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


class SubjectRegistration(PdfExportAndMailMixin, models.Model):
    object_name = 'registration'

    slug = models.SlugField(editable=False)
    created = models.DateTimeField(_('time of registration'), editable=False, auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user'),
                             related_name='leprikon_registrations', on_delete=models.PROTECT)
    subject = models.ForeignKey(Subject, verbose_name=_('subject'),
                                related_name='registrations', on_delete=models.PROTECT)
    subject_variant = models.ForeignKey(SubjectVariant, null=True, verbose_name=_('variant'),
                                        related_name='registrations', on_delete=models.PROTECT)
    price = PriceField(_('price'), editable=False)

    target_group = models.ForeignKey(TargetGroup, verbose_name=_('target group'), blank=True, null=True,
                                     related_name='+', on_delete=models.PROTECT)
    group_name = models.CharField(_('group name'), max_length=150, blank=True, default='')
    group_leader_first_name = models.CharField(_('first name'), max_length=30, blank=True, default='')
    group_leader_last_name = models.CharField(_('last name'), max_length=30, blank=True, default='')
    group_leader_street = models.CharField(_('street'), max_length=150, blank=True, default='')
    group_leader_city = models.CharField(_('city'), max_length=150, blank=True, default='')
    group_leader_postal_code = PostalCodeField(_('postal code'), blank=True, default='')
    group_leader_phone = models.CharField(_('phone'), max_length=30, blank=True, default='')
    group_leader_email = EmailField(_('email address'), blank=True, default='')
    group_school = models.ForeignKey(School, verbose_name=_('school'), blank=True, null=True,
                                     related_name='+', on_delete=models.PROTECT)
    group_school_other = models.CharField(_('other school'), max_length=150, blank=True, default='')
    group_school_class = models.CharField(_('class'), max_length=30,  blank=True, default='')

    approved = models.DateTimeField(_('time of approval'), editable=False, null=True)
    payment_requested = models.DateTimeField(_('payment request time'), editable=False, null=True)
    canceled = models.DateTimeField(_('time of cancellation'), editable=False, null=True)
    cancel_request = models.BooleanField(_('cancel request'), default=False)
    note = models.CharField(_('note'), max_length=300, blank=True, default='')

    questions = models.ManyToManyField(Question, editable=False, related_name='registrations')
    agreements = models.ManyToManyField(Agreement, editable=False, related_name='registrations')
    agreement_options = models.ManyToManyField(AgreementOption, blank=True, verbose_name=_('legal agreements'))

    variable_symbol = models.BigIntegerField(_('variable symbol'), db_index=True, editable=False, null=True)

    class Meta:
        app_label = 'leprikon'
        verbose_name = _('registration')
        verbose_name_plural = _('registrations')

    def __str__(self):
        return '{} - {}'.format(
            self.subject,
            self.group_name or comma_separated([p.participant.full_name for p in self.all_participants]),
        )

    def get_edit_url(self):
        return reverse('admin:leprikon_{}_change'.format(self.subjectregistration._meta.model_name), args=(self.id,))

    @cached_property
    def subjectregistration(self):
        if self.subject.subject_type.subject_type == self.subject.subject_type.COURSE:
            return self.courseregistration
        else:
            return self.eventregistration

    @cached_property
    def all_participants(self):
        return list(self.participants.all())

    def participants_list(self):
        return '\n'.join(map(str, self.all_participants))
    participants_list.short_description = _('participants')

    def participants_list_html(self):
        return mark_safe('<br/>'.join(map(str, self.all_participants)))
    participants_list_html.short_description = _('participants')

    @cached_property
    def group_leader_full_name(self):
        return '{} {}'.format(self.group_leader_first_name, self.group_leader_last_name)

    @cached_property
    def group_leader_address(self):
        return '{}, {}, {}'.format(self.group_leader_street, self.group_leader_city, self.group_leader_postal_code)

    @cached_property
    def group_leader_contact(self):
        if self.group_leader_email and self.group_leader_phone:
            return '{}, {}'.format(self.group_leader_phone, self.group_leader_email)
        else:
            return self.group_leader_email or self.group_leader_phone

    @cached_property
    def group_school_name(self):
        return self.group_school and smart_text(self.group_school) or self.group_school_other

    @cached_property
    def group_school_and_class(self):
        return '{}, {}'.format(self.school_name, self.school_class)

    @cached_property
    def all_group_members(self):
        return list(self.group_members.all())

    def group_members_list(self):
        return '\n'.join(map(str, self.all_group_members))
    group_members_list.short_description = _('group members')

    def group_members_list_html(self):
        return mark_safe('<br/>'.join(map(str, self.all_group_members)))
    group_members_list_html.short_description = _('group members')

    @cached_property
    def all_questions(self):
        return list(self.questions.all())

    @cached_property
    def all_agreements(self):
        return list(self.agreements.all())

    @cached_property
    def all_agreement_options(self):
        return list(self.agreement_options.all())

    def agreement_options_list(self):
        lines = []
        for agreement in self.all_agreements:
            lines.append(agreement.name + ':')
            for option in agreement.all_options:
                lines.append('{checkbox} {option_name}'.format(
                    checkbox=('☑' if option.required or option in self.all_agreement_options else '☐'),
                    option_name=option.name,
                ))
        return '\n'.join(lines)
    agreement_options_list.short_description = _('agreement options')

    @cached_property
    def all_attachments(self):
        return self.subject.all_attachments + self.subject.subject_type.all_attachments

    @cached_property
    def all_recipients(self):
        recipients = set()
        if self.user.email:
            recipients.add(self.user.email)
        for participant in self.all_participants:
            recipients.update(participant.all_recipients)
        return recipients

    @cached_property
    def all_discounts(self):
        return list(self.discounts.all())

    @cached_property
    def all_payments(self):
        return list(self.payments.all())

    @cached_property
    def current_receivable(self):
        return self.subjectregistration.current_receivable

    @cached_property
    def spayd(self):
        leprikon_site = LeprikonSite.objects.get_current()
        return spayd(
            ('ACC', ('%s+%s' % (leprikon_site.iban, leprikon_site.bic)) if leprikon_site.bic else leprikon_site.iban),
            ('AM', self.current_receivable),
            ('CC', localeconv['int_curr_symbol'].strip()),
            ('MSG', '%s, %s' % (self.subject.name[:29], str(self)[:29])),
            ('RN', slugify(leprikon_site.company_name).replace('*', '')[:35]),
            ('X-VS', self.variable_symbol),
        )

    @cached_property
    def payment_url(self):
        leprikon_site = LeprikonSite.objects.get_current()
        return pays_payment_url(
            gateway=leprikon_site.payment_gateway,
            order_id=self.variable_symbol,
            amount=self.current_receivable,
            email=self.user.email,
        )

    def get_discounts(self, d):
        if d:
            return [p for p in self.all_discounts if p.accounted.date() <= d]
        else:
            return self.all_discounts

    def get_payments(self, d):
        if d:
            return [p for p in self.all_payments if p.accounted.date() <= d]
        else:
            return self.all_payments

    def get_discounted(self, d=None):
        return sum(p.amount for p in self.get_discounts(d))

    def get_paid(self, d=None):
        return sum(p.amount for p in self.get_payments(d))

    def get_qr_code(self):
        output = BytesIO()
        qrcode.make(self.spayd, border=1).save(output)
        output.seek(0)
        return output.read()

    mail_subject_patterns = {
        'received': _('Registration for {subject_type} {subject}'),
        'payment_request': _('Registration for {subject_type} {subject} - payment request'),
        'approved': _('Registration for {subject_type} {subject} was approved'),
        'refused': _('Registration for {subject_type} {subject} was refused'),
        'canceled': _('Registration for {subject_type} {subject} was canceled'),
    }

    def approve(self):
        with transaction.atomic():
            if self.approved is None:
                self.approved = timezone.now()
                self.save()
                self.send_mail('approved')
                if self.payment_requested is None:
                    self.request_payment()

    def request_payment(self):
        with transaction.atomic():
            if self.payment_requested is None:
                self.payment_requested = timezone.now()
                self.save()
                if self.current_receivable:
                    self.send_mail('payment_request')

    def refuse(self):
        with transaction.atomic():
            if self.canceled is None:
                self.canceled = timezone.now()
                self.save()
                self.send_mail('refused')

    def cancel(self):
        with transaction.atomic():
            if self.canceled is None:
                self.canceled = timezone.now()
                self.save()
                self.send_mail('canceled')

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify('{}-{}'.format(self.subject.name, self))[:50]
        if self.canceled:
            self.cancel_request = False
        with transaction.atomic():
            super(SubjectRegistration, self).save(*args, **kwargs)
            if not self.variable_symbol:
                self.variable_symbol = generate_variable_symbol(self)
                super(SubjectRegistration, self).save(*args, **kwargs)

    @cached_property
    def print_setup(self):
        return (
            self.subject.reg_print_setup or
            self.subject.subject_type.reg_print_setup or
            LeprikonSite.objects.get_current().reg_print_setup or
            PrintSetup()
        )

    def get_attachments(self, event):
        if event == 'received':
            return [self.pdf_attachment] + [
                (attachment.file.file.path,) for attachment in self.all_attachments
            ]
        elif event == 'payment_request':
            leprikon_site = LeprikonSite.objects.get_current()
            if leprikon_site.bank_account:
                qr_code = MIMEImage(self.get_qr_code())
                qr_code.add_header('Content-ID', '<qr_code>')
                return [qr_code]
        return None


class SubjectRegistrationParticipant(models.Model):
    registration = models.ForeignKey(SubjectRegistration, verbose_name=_('registration'),
                                     related_name='participants', on_delete=models.CASCADE)
    MALE = 'm'
    FEMALE = 'f'
    participant_gender = models.CharField(_('gender'), max_length=1, editable=False,
                                          choices=((MALE, _('male')), (FEMALE, _('female'))))
    participant_first_name = models.CharField(_('first name'), max_length=30)
    participant_last_name = models.CharField(_('last name'), max_length=30)
    participant_birth_num = BirthNumberField(_('birth number'))
    participant_age_group = models.ForeignKey(AgeGroup, verbose_name=_('age group'),
                                              related_name='+', on_delete=models.PROTECT)
    participant_street = models.CharField(_('street'), max_length=150)
    participant_city = models.CharField(_('city'), max_length=150)
    participant_postal_code = PostalCodeField(_('postal code'))
    participant_citizenship = models.ForeignKey(Citizenship, verbose_name=_('citizenship'),
                                                related_name='+', on_delete=models.PROTECT)
    participant_phone = models.CharField(_('phone'), max_length=30, blank=True, default='')
    participant_email = EmailField(_('email address'), blank=True, default='')

    participant_school = models.ForeignKey(School, verbose_name=_('school'), blank=True, null=True,
                                           related_name='+', on_delete=models.PROTECT)
    participant_school_other = models.CharField(_('other school'), max_length=150, blank=True, default='')
    participant_school_class = models.CharField(_('class'), max_length=30,  blank=True, default='')
    participant_health = models.TextField(_('health'), blank=True, default='')

    has_parent1 = models.BooleanField(_('first parent'), default=False)
    parent1_first_name = models.CharField(_('first name'), max_length=30,  blank=True, null=True)
    parent1_last_name = models.CharField(_('last name'), max_length=30,  blank=True, null=True)
    parent1_street = models.CharField(_('street'), max_length=150, blank=True, null=True)
    parent1_city = models.CharField(_('city'), max_length=150, blank=True, null=True)
    parent1_postal_code = PostalCodeField(_('postal code'), blank=True, null=True)
    parent1_phone = models.CharField(_('phone'), max_length=30,  blank=True, null=True)
    parent1_email = EmailField(_('email address'), blank=True, null=True)

    has_parent2 = models.BooleanField(_('second parent'), default=False)
    parent2_first_name = models.CharField(_('first name'), max_length=30,  blank=True, null=True)
    parent2_last_name = models.CharField(_('last name'), max_length=30,  blank=True, null=True)
    parent2_street = models.CharField(_('street'), max_length=150, blank=True, null=True)
    parent2_city = models.CharField(_('city'), max_length=150, blank=True, null=True)
    parent2_postal_code = PostalCodeField(_('postal code'), blank=True, null=True)
    parent2_phone = models.CharField(_('phone'), max_length=30,  blank=True, null=True)
    parent2_email = EmailField(_('email address'), blank=True, null=True)

    answers = models.TextField(_('additional answers'), blank=True, default='{}', editable=False)

    class Meta:
        app_label = 'leprikon'
        verbose_name = _('participant')
        verbose_name_plural = _('participants')

    def __str__(self):
        return '{full_name} ({birth_date})'.format(
            full_name=self.participant.full_name,
            birth_date=self.participant.birth_date,
        )

    def get_answers(self):
        return loads(self.answers)

    def get_questions_and_answers(self):
        answers = self.get_answers()
        for q in self.registration.all_questions:
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
    def all_recipients(self):
        recipients = set(parent.email for parent in self.parents if parent.email)
        if self.participant.email:
            recipients.add(self.participant.email)
        return recipients

    def save(self, *args, **kwargs):
        self.participant_gender = self.participant_birth_num[2:4] > '50' and self.FEMALE or self.MALE
        if not self.has_parent1:
            if self.has_parent2:
                self.parent1_first_name = self.parent2_first_name
                self.parent1_last_name = self.parent2_last_name
                self.parent1_street = self.parent2_street
                self.parent1_city = self.parent2_city
                self.parent1_postal_code = self.parent2_postal_code
                self.parent1_phone = self.parent2_phone
                self.parent1_email = self.parent2_email
                self.has_parent1 = True
                self.has_parent2 = False
            else:
                self.parent1_first_name = None
                self.parent1_last_name = None
                self.parent1_street = None
                self.parent1_city = None
                self.parent1_postal_code = None
                self.parent1_phone = None
                self.parent1_email = None
        if not self.has_parent2:
            self.parent2_first_name = None
            self.parent2_last_name = None
            self.parent2_street = None
            self.parent2_city = None
            self.parent2_postal_code = None
            self.parent2_phone = None
            self.parent2_email = None
        super(SubjectRegistrationParticipant, self).save(*args, **kwargs)

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
        def birth_date(self):
            return get_birth_date(self.birth_num)

        @cached_property
        def school_name(self):
            return self.school and smart_text(self.school) or self.school_other

        @cached_property
        def school_and_class(self):
            return '{}, {}'.format(self.school_name, self.school_class)


class SubjectRegistrationGroupMember(models.Model):
    registration = models.ForeignKey(SubjectRegistration, verbose_name=_('registration'),
                                     related_name='group_members', on_delete=models.CASCADE)
    first_name = models.CharField(_('first name'), max_length=30)
    last_name = models.CharField(_('last name'), max_length=30)
    note = models.CharField(_('note'), max_length=150, blank=True, default='')

    class Meta:
        app_label = 'leprikon'
        verbose_name = _('group member')
        verbose_name_plural = _('group members')

    def __str__(self):
        return '{full_name} ({note})'.format(
            full_name=self.full_name,
            note=self.note,
        ) if self.note else self.full_name

    @cached_property
    def full_name(self):
        return '{} {}'.format(self.first_name, self.last_name)


class TransactionMixin(object):

    def save(self, *args, **kwargs):
        self.clean()
        super(TransactionMixin, self).save(*args, **kwargs)

    def clean(self):
        errors = {}
        if self.amount == 0:
            errors['amount'] = [_('Amount can not be zero.')]
        if self.accounted:
            max_closure_date = LeprikonSite.objects.get_current().max_closure_date
            if max_closure_date and self.accounted.date() <= max_closure_date:
                errors['accounted'] = [
                    _('Date must be after the last account closure ({}).').format(
                        formats.date_format(max_closure_date)
                    )
                ]
        if errors:
            raise ValidationError(errors)


class SubjectDiscount(TransactionMixin, models.Model):
    accounted = models.DateTimeField(_('accounted time'), default=timezone.now)
    amount = PriceField(_('discount'), default=0)
    explanation = models.CharField(_('discount explanation'), max_length=250, blank=True, default='')

    class Meta:
        abstract = True
        app_label = 'leprikon'
        verbose_name = _('discount')
        verbose_name_plural = _('discounts')
        ordering = ('accounted',)

    def __str__(self):
        return currency(self.amount)


class SubjectPayment(PdfExportAndMailMixin, TransactionMixin, models.Model):
    object_name = 'payment'

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
    payments = frozenset({PAYMENT_CASH, PAYMENT_BANK, PAYMENT_ONLINE, PAYMENT_TRANSFER})
    returns = frozenset({RETURN_CASH, RETURN_BANK, RETURN_TRANSFER})

    registration = models.ForeignKey(SubjectRegistration, verbose_name=_('registration'),
                                     related_name='payments', on_delete=models.PROTECT)
    accounted = models.DateTimeField(_('accounted time'), default=timezone.now)
    payment_type = models.CharField(_('payment type'), max_length=30, choices=payment_type_labels.items())
    amount = PriceField(_('amount'), help_text=_('positive value for payment, negative value for return'))
    note = models.CharField(_('note'), max_length=300, blank=True, default='')
    related_payment = models.OneToOneField('self', verbose_name=_('related payment'), blank=True, null=True,
                                           limit_choices_to={'payment_type__in': (PAYMENT_TRANSFER, RETURN_TRANSFER)},
                                           related_name='related_payments', on_delete=models.PROTECT)
    bankreader_transaction = models.OneToOneField(BankreaderTransaction, verbose_name=_('bank account transaction'),
                                                  blank=True, null=True, on_delete=models.PROTECT)
    pays_payment = models.OneToOneField(PaysPayment, editable=False, verbose_name=_('online payment'),
                                        limit_choices_to={'status': PaysPayment.REALIZED},
                                        blank=True, null=True, on_delete=models.PROTECT)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, verbose_name=_('received by'),
                                    related_name='+', on_delete=models.PROTECT)

    class Meta:
        app_label = 'leprikon'
        verbose_name = _('payment')
        verbose_name_plural = _('payments')
        ordering = ('accounted',)

    def __str__(self):
        return '{registration}, {payment_type} {amount}'.format(
            registration = self.registration,
            payment_type = self.payment_type_label,
            amount = currency(abs(self.amount)),
        )

    @cached_property
    def payment_type_label(self):
        return self.payment_type_labels.get(self.payment_type, '-')
    payment_type_label.short_description = _('payment type')

    @cached_property
    def slug(self):
        return '{}-{}'.format(self.registration.slug, self.id)

    @cached_property
    def print_setup(self):
        return (
            self.registration.subject.bill_print_setup or
            self.registration.subject.subject_type.bill_print_setup or
            LeprikonSite.objects.get_current().bill_print_setup or
            PrintSetup()
        )

    @cached_property
    def subject(self):
        return self.registration.subject

    mail_subject_patterns = {
        'received': _('Registration for {subject_type} {subject} - payment confirmation'),
    }

    def get_attachments(self, event):
        if event == 'received':
            return [self.pdf_attachment]
        return None

    @cached_property
    def all_recipients(self):
        return self.registration.all_recipients

    def clean(self):
        errors = {}
        try:
            super(SubjectPayment, self).clean()
        except ValidationError as e:
            errors = e.update_error_dict(errors)

        # ensure at most one relation
        if [self.related_payment, self.bankreader_transaction, self.pays_payment].count(None) < 2:
            message = _('Payment can only have one relation.')
            if self.related_payment:
                errors['related_payment'] = message
            if self.bankreader_transaction:
                errors['bankreader_transaction'] = message
        else:
            if self.related_payment:
                valid_payment_type = (
                    SubjectPayment.PAYMENT_TRANSFER
                    if self.related_payment.payment_type == SubjectPayment.RETURN_TRANSFER
                    else SubjectPayment.RETURN_TRANSFER
                )
                valid_amount = -self.related_payment.amount
            if self.bankreader_transaction:
                valid_payment_type = (
                    SubjectPayment.PAYMENT_BANK
                    if self.bankreader_transaction.amount > 0
                    else SubjectPayment.RETURN_BANK
                )
                valid_amount = self.bankreader_transaction.amount
            if self.related_payment or self.bankreader_transaction:
                if self.payment_type != valid_payment_type:
                    errors.setdefault('payment_type', []).append(
                        _('Payment type must be {valid_payment_type}.').format(
                            valid_payment_type=self.payment_type_labels[valid_payment_type],
                        )
                    )
                if self.amount != valid_amount:
                    errors.setdefault('amount', []).append(
                        _('Amount must be {valid_amount}.').format(valid_amount=valid_amount)
                    )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.id:
            super(SubjectPayment, self).save(*args, **kwargs)
        else:
            with transaction.atomic():
                super(SubjectPayment, self).save(*args, **kwargs)
                self.send_mail()


@receiver(models.signals.post_save, sender=PaysPayment)
def payment_create_subject_payment(instance, **kwargs):
    payment = instance
    # check realized payment
    if payment.status != PaysPayment.REALIZED:
        return
    # check registration
    try:
        registration = SubjectRegistration.objects.get(variable_symbol=int(payment.order_id))
    except (ValueError, SubjectRegistration.DoesNotExist):
        return
    # create payment
    SubjectPayment.objects.create(
        registration=registration,
        accounted=payment.created,
        payment_type=SubjectPayment.PAYMENT_ONLINE,
        amount=payment.amount / payment.base_units,
        note=_('received online payment'),
        pays_payment=payment,
    )


@receiver(models.signals.post_save, sender=BankreaderTransaction)
def transaction_create_subject_payment(instance, **kwargs):
    transaction = instance
    # check variable symbol
    if not transaction.variable_symbol:
        return
    # check closure date (use closure date from cached leprikon site)
    max_closure_date = LeprikonSite.objects.get_current().max_closure_date
    if max_closure_date and transaction.accounted_date <= max_closure_date:
        return
    # check registration
    registration = SubjectRegistration.objects.filter(variable_symbol=transaction.variable_symbol).first()
    if not registration:
        return
    # create payment
    SubjectPayment.objects.create(
        registration=registration,
        accounted=transaction.accounted_date,
        payment_type=SubjectPayment.PAYMENT_BANK if transaction.amount >= 0 else SubjectPayment.RETURN_BANK,
        amount=transaction.amount,
        note=_('imported from account statement'),
        bankreader_transaction=transaction,
    )
