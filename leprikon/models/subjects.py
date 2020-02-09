import colorsys
import logging
from collections import OrderedDict, namedtuple
from datetime import datetime, time
from email.mime.image import MIMEImage
from io import BytesIO
from itertools import chain
from json import loads
from os.path import basename

import qrcode
import trml2pdf
from bankreader.models import Transaction as BankreaderTransaction
from cms.models.fields import PageField
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.db import models, transaction
from django.dispatch import receiver
from django.template.loader import select_template
from django.urls import reverse_lazy as reverse
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
    comma_separated, currency, get_birth_date, lazy_paragraph as paragraph,
    localeconv, spayd,
)
from .agegroup import AgeGroup
from .agreements import Agreement, AgreementOption
from .citizenship import Citizenship
from .department import Department
from .fields import (
    BirthNumberField, ColorField, EmailField, PostalCodeField, PriceField,
)
from .leprikonsite import LeprikonSite
from .organizations import Organization
from .place import Place
from .printsetup import PrintSetup
from .question import Question
from .roles import Leader
from .school import School
from .schoolyear import SchoolYear
from .targetgroup import TargetGroup
from .utils import generate_variable_symbol, lazy_help_text_with_html_default

logger = logging.getLogger(__name__)

DEFAULT_TEXTS = {
    'text_registration_received': paragraph(_(
        'Hello,\n'
        'thank You for submitting the registration.\n'
        'We will inform you about its further processing.'
    )),

    'text_registration_approved': paragraph(_(
        'Hello,\n'
        'we are pleased to inform You, that Your registration was approved.\n'
        'We are looking forward to see You.'
    )),

    'text_registration_refused': paragraph(_(
        'Hello,\n'
        'we are sorry to inform You, that Your registration was refused.'
    )),

    'text_registration_payment_request': paragraph(_(
        'Hello,\n'
        'we\'d like to ask You to pay for Your registration.\n'
        'If You have already made the payment recently, please ignore this message.'
    )),

    'text_registration_canceled': paragraph(_(
        'Hello,\n'
        'Your registration was canceled.'
    )),

    'text_discount_granted': paragraph(_(
        'Hello,\n'
        'we have just grated a discount for Your registration.'
    )),

    'text_payment_received': paragraph(_(
        'Hello,\n'
        'we have just received Your payment. Thank You.\n'
        'Please see the recipe attached.'
    )),
}

CHAT_GROUP_BROADCAST = 'B'
CHAT_GROUP_CHAT = 'C'
CHAT_GROUP_TYPE_LABELS = OrderedDict([
    (CHAT_GROUP_BROADCAST, _('broadcast group')),
    (CHAT_GROUP_CHAT, _('chat group')),
])

CHAT_GROUP_TYPE_HELP_TEXT = _(
    'Only the leader can write to broadcast group. Users may reply to the sender with direct messages.\n'
    'Chat group allows all members to chat with each other.'
)


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
        Question, blank=True, related_name='+', verbose_name=_('additional questions'),
        help_text=_('Add additional questions to be asked in the registration form.'),
    )
    registration_agreements = models.ManyToManyField(
        Agreement, blank=True, related_name='+', verbose_name=_('additional legal agreements'),
        help_text=_('Add additional legal agreements specific to this subject type.'),
    )
    reg_print_setup = models.ForeignKey(PrintSetup, blank=True, null=True, on_delete=models.SET_NULL,
                                        related_name='+', verbose_name=_('registration print setup'))
    bill_print_setup = models.ForeignKey(PrintSetup, blank=True, null=True, on_delete=models.SET_NULL,
                                         related_name='+', verbose_name=_('payment print setup'))
    organization = models.ForeignKey(Organization, blank=True, null=True, on_delete=models.SET_NULL,
                                     related_name='+', verbose_name=_('organization'))
    chat_group_type = models.CharField(
        _('default chat group type'), max_length=1, choices=CHAT_GROUP_TYPE_LABELS.items(),
        default=CHAT_GROUP_BROADCAST, help_text=CHAT_GROUP_TYPE_HELP_TEXT,
    )
    text_registration_received = HTMLField(
        _('text: registration received'), blank=True, default='',
        help_text=lazy_help_text_with_html_default('', DEFAULT_TEXTS['text_registration_received']),
    )
    text_registration_approved = HTMLField(
        _('text: registration approved'), blank=True, default='',
        help_text=lazy_help_text_with_html_default('', DEFAULT_TEXTS['text_registration_approved']),
    )
    text_registration_refused = HTMLField(
        _('text: registration refused'), blank=True, default='',
        help_text=lazy_help_text_with_html_default('', DEFAULT_TEXTS['text_registration_refused']),
    )
    text_registration_payment_request = HTMLField(
        _('text: registration payment request'), blank=True, default='',
        help_text=lazy_help_text_with_html_default('', DEFAULT_TEXTS['text_registration_payment_request']),
    )
    text_registration_canceled = HTMLField(
        _('text: registration canceled'), blank=True, default='',
        help_text=lazy_help_text_with_html_default('', DEFAULT_TEXTS['text_registration_canceled']),
    )
    text_discount_granted = HTMLField(
        _('text: discount granted'), blank=True, default='',
        help_text=lazy_help_text_with_html_default('', DEFAULT_TEXTS['text_discount_granted']),
    )
    text_payment_received = HTMLField(
        _('text: payment received'), blank=True, default='',
        help_text=lazy_help_text_with_html_default('', DEFAULT_TEXTS['text_payment_received']),
    )

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

    def get_absolute_url(self):
        return reverse(self.slug + ':subject_list')


class SubjectTypeAttachment(models.Model):
    subject_type = models.ForeignKey(SubjectType, on_delete=models.CASCADE,
                                     related_name='attachments', verbose_name=_('subject type'))
    file = FilerFileField(on_delete=models.CASCADE, related_name='+')
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
    subject_types = models.ManyToManyField(SubjectType, related_name='groups', verbose_name=_('subject type'))

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
    PARTICIPANTS = 'P'
    GROUPS = 'G'
    REGISTRATION_TYPE_CHOICES = [
        (PARTICIPANTS, _('participants')),
        (GROUPS, _('groups')),
    ]
    REGISTRATION_TYPES = dict(REGISTRATION_TYPE_CHOICES)

    school_year = models.ForeignKey(SchoolYear, editable=False, on_delete=models.CASCADE,
                                    related_name='subjects', verbose_name=_('school year'))
    subject_type = models.ForeignKey(SubjectType, on_delete=models.PROTECT,
                                     related_name='subjects', verbose_name=_('subject type'))
    registration_type = models.CharField(_('registration type'), choices=REGISTRATION_TYPE_CHOICES, max_length=1)
    code = models.PositiveSmallIntegerField(_('accounting code'), blank=True, default=0)
    name = models.CharField(_('name'), max_length=150)
    description = HTMLField(_('description'), blank=True, default='')
    department = models.ForeignKey(Department, blank=True, null=True, on_delete=models.SET_NULL,
                                   related_name='subjects', verbose_name=_('department'))
    groups = models.ManyToManyField(SubjectGroup, verbose_name=_('groups'), related_name='subjects', blank=True)
    place = models.ForeignKey(Place, blank=True, null=True, on_delete=models.SET_NULL,
                              related_name='subjects', verbose_name=_('place'))
    age_groups = models.ManyToManyField(AgeGroup, related_name='subjects', verbose_name=_('age groups'))
    target_groups = models.ManyToManyField(TargetGroup, related_name='subjects', verbose_name=_('target groups'))
    leaders = models.ManyToManyField(Leader, blank=True, related_name='subjects', verbose_name=_('leaders'))
    price = PriceField(_('price'), blank=True, null=True)
    public = models.BooleanField(_('public'), default=False)
    reg_from = models.DateTimeField(_('registration active from'), blank=True, null=True)
    reg_to = models.DateTimeField(_('registration active to'), blank=True, null=True)
    photo = FilerImageField(verbose_name=_('photo'), blank=True, null=True,
                            related_name='+', on_delete=models.SET_NULL)
    page = PageField(blank=True, null=True, on_delete=models.SET_NULL,
                     related_name='+', verbose_name=_('page'))
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
        help_text=_('Group member details only include name and note.'),
    )
    max_group_members_count = models.PositiveIntegerField(
        _('maximal group members count per registration'),
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
        Agreement, blank=True, related_name='+', verbose_name=_('additional legal agreements'),
        help_text=_('Add additional legal agreements specific for this subject.'),
    )
    reg_print_setup = models.ForeignKey(PrintSetup, blank=True, null=True, on_delete=models.SET_NULL,
                                        related_name='+', verbose_name=_('registration print setup'),
                                        help_text=_('Only use to set value specific for this subject.'))
    bill_print_setup = models.ForeignKey(PrintSetup, blank=True, null=True, on_delete=models.SET_NULL,
                                         related_name='+', verbose_name=_('payment print setup'),
                                         help_text=_('Only use to set value specific for this subject.'))
    organization = models.ForeignKey(Organization, blank=True, null=True, on_delete=models.SET_NULL,
                                     related_name='+', verbose_name=_('organization'),
                                     help_text=_('Only use to set value specific for this subject.'))
    chat_group_type = models.CharField(
        _('chat group type'), blank=True, max_length=1, null=True, choices=CHAT_GROUP_TYPE_LABELS.items(),
        help_text=CHAT_GROUP_TYPE_HELP_TEXT,
    )
    text_registration_received = HTMLField(_('text: registration received'), blank=True, default='')
    text_registration_approved = HTMLField(_('text: registration approved'), blank=True, default='')
    text_registration_refused = HTMLField(_('text: registration refused'), blank=True, default='')
    text_registration_payment_request = HTMLField(_('text: registration payment request'), blank=True, default='')
    text_registration_canceled = HTMLField(_('text: registration canceled'), blank=True, default='')
    text_discount_granted = HTMLField(_('text: discount granted'), blank=True, default='')
    text_payment_received = HTMLField(_('text: payment received'), blank=True, default='')

    class Meta:
        app_label = 'leprikon'
        ordering = ('code', 'name')
        verbose_name = _('subject')
        verbose_name_plural = _('subjects')

    def __str__(self):
        return '{} {}'.format(self.school_year, self.display_name)

    def save(self, *args, **kwargs):
        if self.registration_type_participants:
            self.min_group_members_count = 0
            self.max_group_members_count = 0
        elif self.registration_type_groups:
            self.min_participants_count = 0
            self.max_participants_count = 0
        super().save(*args, **kwargs)

    @cached_property
    def registration_type_participants(self):
        return self.registration_type == self.PARTICIPANTS

    @cached_property
    def registration_type_groups(self):
        return self.registration_type == self.GROUPS

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

    def get_valid_participants(self, d):
        qs = SubjectRegistrationParticipant.objects
        if self.subject_type.subject_type == SubjectType.COURSE:
            qs = qs.filter(
                models.Q(registration__courseregistration__course_history__course_id=self.id) &
                (
                    models.Q(registration__courseregistration__course_history__end__isnull=True) |
                    models.Q(registration__courseregistration__course_history__end__gte=d)
                )
            )
        else:  # self.subject_type.subject_type == SubjectType.EVENT:
            qs = qs.filter(
                registration__subject_id=self.id,
                registration__approved__isnull=False,
            )
        return qs.exclude(registration__canceled__date__lt=d)

    @cached_property
    def all_approved_participants(self):
        qs = SubjectRegistrationParticipant.objects
        if self.subject_type.subject_type == SubjectType.COURSE:
            qs = qs.filter(
                registration__courseregistration__course_history__course_id=self.id,
            ).annotate(
                approved=models.F('registration__approved'),
                canceled=models.F('registration__canceled'),
            )
        else:  # self.subject_type.subject_type == SubjectType.EVENT:
            qs = qs.filter(
                registration__subject_id=self.id,
                registration__approved__isnull=False,
            )
        return list(qs)

    @property
    def registration_allowed(self):
        now = timezone.now()
        return (
            self.price is not None and
            (self.reg_from or self.reg_to) and
            (self.reg_from is None or self.reg_from <= now) and
            (self.reg_to is None or self.reg_to > now)
        )

    @property
    def registration_not_allowed_message(self):
        now = timezone.now()
        if self.price is not None:
            if self.reg_from > now:
                return _('Registering will start on {}.').format(self.reg_from)
            if self.reg_to < now:
                return _('Registering ended on {}').format(self.reg_to)
        return _('Registering is currently not allowed.')

    @property
    def full(self):
        return self.max_registrations_count and self.active_registrations_count >= self.max_registrations_count

    def get_absolute_url(self):
        return reverse(self.subject_type.slug + ':subject_detail', args=(self.id,))

    def get_registration_url(self):
        return reverse(self.subject_type.slug + ':subject_registration_form', args=(self.id,))

    def get_edit_url(self):
        return reverse('admin:leprikon_{}_change'.format(self.subject._meta.model_name), args=(self.id,))

    def get_age_groups_list(self):
        return comma_separated(self.all_age_groups)
    get_age_groups_list.short_description = _('age groups list')

    def get_groups_list(self):
        return comma_separated(self.all_groups)
    get_groups_list.short_description = _('groups list')

    def get_leaders_list(self):
        return comma_separated(self.all_leaders)
    get_leaders_list.short_description = _('leaders list')

    def get_target_groups_list(self):
        return comma_separated(self.all_target_groups)
    get_target_groups_list.short_description = _('target groups list')

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
            if self.period != self.subject.all_periods[0]:
                qs = qs.filter(date__gte=self.period.start)
            if self.period != self.subject.all_periods[-1]:
                qs = qs.filter(date__lte=self.period.end)
        return list(qs)

    @cached_property
    def all_approved_participants(self):
        if self.period:  # course
            return [
                participant
                for participant in self.subject.all_approved_participants
                if (
                    participant.approved.date() <= self.period.end and
                    (participant.canceled is None or participant.canceled.date() >= self.period.start)
                )
            ]
        else:  # event
            return self.subject.all_approved_participants

    @cached_property
    def all_alternates(self):
        alternates = set()
        for entry in self.all_journal_entries:
            for alternate in entry.all_alternates:
                alternates.add(alternate)
        return list(alternates)

    PresenceRecord = namedtuple('PresenceRecord', ('person', 'presences'))

    def get_participant_presences(self):
        return [
            self.PresenceRecord(
                participant,
                [
                    participant.id in entry.all_participants_idset
                    for entry in self.all_journal_entries
                ]
            )
            for participant in self.all_approved_participants
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
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='variants', verbose_name=_('subject'))
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
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE,
                                related_name='attachments', verbose_name=_('subject'))
    file = FilerFileField(on_delete=models.CASCADE, related_name='+')
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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                             related_name='leprikon_registrations', verbose_name=_('user'))
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT,
                                related_name='registrations', verbose_name=_('subject'))
    subject_variant = models.ForeignKey(SubjectVariant, null=True, on_delete=models.PROTECT,
                                        related_name='registrations', verbose_name=_('variant'))
    price = PriceField(_('price'), editable=False)

    approved = models.DateTimeField(_('time of approval'), editable=False, null=True)
    payment_requested = models.DateTimeField(_('payment request time'), editable=False, null=True)
    canceled = models.DateTimeField(_('time of cancellation'), editable=False, null=True)
    cancel_request = models.BooleanField(_('cancel request'), default=False)
    note = models.CharField(_('note'), max_length=300, blank=True, default='')

    questions = models.ManyToManyField(Question, editable=False, related_name='registrations')
    agreements = models.ManyToManyField(Agreement, editable=False, related_name='registrations')
    agreement_options = models.ManyToManyField(AgreementOption, blank=True, verbose_name=_('legal agreements'))

    variable_symbol = models.BigIntegerField(_('variable symbol'), db_index=True, editable=False, null=True)

    registration_link = models.ForeignKey(
        'leprikon.RegistrationLink', editable=False, null=True,
        on_delete=models.SET_NULL, related_name='registrations', verbose_name=_('registration link'),
    )

    class Meta:
        app_label = 'leprikon'
        verbose_name = _('registration')
        verbose_name_plural = _('registrations')

    def __str__(self):
        return '{} - {}'.format(
            self.subject,
            self.group if self.subject.registration_type_groups else comma_separated([
                p.full_name for p in self.all_participants
            ])
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
    def payment_status_sum(self):
        return sum(self.subjectregistration.payment_statuses)

    @cached_property
    def organization(self):
        return (
            self.subject.organization or
            self.subject.subject_type.organization or
            LeprikonSite.objects.get_current().organization or
            Organization()
        )

    @cached_property
    def spayd(self):
        org = self.organization
        return spayd(
            ('ACC', ('%s+%s' % (org.iban, org.bic)) if org.bic else org.iban),
            ('AM', self.payment_status_sum.amount_due),
            ('CC', localeconv['int_curr_symbol'].strip()),
            ('MSG', '%s, %s' % (self.subject.name[:29], str(self)[:29])),
            ('RN', slugify(self.organization.name).replace('*', '')[:35]),
            ('X-VS', self.variable_symbol),
        )

    @cached_property
    def payment_url(self):
        leprikon_site = LeprikonSite.objects.get_current()
        return pays_payment_url(
            gateway=leprikon_site.payment_gateway,
            order_id=self.variable_symbol,
            amount=self.payment_status_sum.amount_due,
            email=self.user.email,
        )

    @cached_property
    def text_registration_received(self):
        return (
            self.subject.text_registration_received or
            self.subject.subject_type.text_registration_received or
            DEFAULT_TEXTS['text_registration_received']
        )

    @cached_property
    def text_registration_approved(self):
        return (
            self.subject.text_registration_approved or
            self.subject.subject_type.text_registration_approved or
            DEFAULT_TEXTS['text_registration_approved']
        )

    @cached_property
    def text_registration_refused(self):
        return (
            self.subject.text_registration_refused or
            self.subject.subject_type.text_registration_refused or
            DEFAULT_TEXTS['text_registration_refused']
        )

    @cached_property
    def text_registration_payment_request(self):
        return (
            self.subject.text_registration_payment_request or
            self.subject.subject_type.text_registration_payment_request or
            DEFAULT_TEXTS['text_registration_payment_request']
        )

    @cached_property
    def text_registration_canceled(self):
        return (
            self.subject.text_registration_canceled or
            self.subject.subject_type.text_registration_canceled or
            DEFAULT_TEXTS['text_registration_canceled']
        )

    @cached_property
    def text_discount_granted(self):
        return (
            self.subject.text_discount_granted or
            self.subject.subject_type.text_discount_granted or
            DEFAULT_TEXTS['text_discount_granted']
        )

    @cached_property
    def text_payment_received(self):
        return (
            self.subject.text_payment_received or
            self.subject.subject_type.text_payment_received or
            DEFAULT_TEXTS['text_payment_received']
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
        if self.approved is None:
            with transaction.atomic():
                self.canceled = None
                self.approved = timezone.now()
                self.save()
                self.send_mail('approved')
                if self.payment_requested is None:
                    self.request_payment()
        else:
            raise ValidationError((
                _('Unfortunately, it is not possible to restore canceled registration {r}. Please create new one.')
                if self.canceled else
                _('The registration {r} has already been approved.')
            ).format(r=self))

    def request_payment(self):
        with transaction.atomic():
            if self.payment_requested is None:
                self.payment_requested = timezone.now()
                self.save()
            if self.payment_status_sum.amount_due:
                self.send_mail('payment_request')

    def refuse(self):
        if self.approved is None:
            if self.canceled is None:
                with transaction.atomic():
                    self.canceled = timezone.now()
                    self.save()
                    self.send_mail('refused')
            else:
                raise ValidationError(_('The registration {r} has already been refued.').format(r=self))
        else:
            raise ValidationError(_(
                'Unfortunately, it is not possible to refuse the registration {r}. However, You may cancel it.'
            ).format(r=self))

    def cancel(self):
        if self.approved:
            if self.canceled is None:
                with transaction.atomic():
                    self.canceled = timezone.now()
                    self.save()
                    self.send_mail('canceled')
            else:
                raise ValidationError(_('The registration {r} has already been canceled.').format(r=self))
        else:
            raise ValidationError(_(
                'Unfortunately, it is not possible to cancel the registration {r}. However, You may refuse it.'
            ).format(r=self))

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
            return [
                (basename(attachment.file.file.path), open(attachment.file.file.path, 'rb').read())
                for attachment in self.all_attachments
            ]
        elif event == 'payment_request':
            if self.organization.iban:
                qr_code = MIMEImage(self.get_qr_code())
                qr_code.add_header('Content-ID', '<qr_code>')
                return [qr_code]
        return None


class QuestionsMixin:
    def get_answers(self):
        return loads(self.answers)

    def get_questions_and_answers(self):
        answers = self.get_answers()
        for q in self.registration.all_questions:
            yield {
                'question': q.question,
                'answer': answers.get(q.name, ''),
            }


class PersonMixin:
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


class SchoolMixin:
    @cached_property
    def school_name(self):
        return self.school and smart_text(self.school) or self.school_other

    @cached_property
    def school_and_class(self):
        return '{}, {}'.format(self.school_name, self.school_class)


class SubjectRegistrationParticipant(SchoolMixin, PersonMixin, QuestionsMixin, models.Model):
    registration = models.ForeignKey(SubjectRegistration, on_delete=models.CASCADE,
                                     related_name='participants', verbose_name=_('registration'))
    MALE = 'm'
    FEMALE = 'f'
    gender = models.CharField(_('gender'), max_length=1, editable=False,
                              choices=((MALE, _('male')), (FEMALE, _('female'))))
    first_name = models.CharField(_('first name'), max_length=30)
    last_name = models.CharField(_('last name'), max_length=30)
    birth_num = BirthNumberField(_('birth number'))
    age_group = models.ForeignKey(AgeGroup, on_delete=models.PROTECT,
                                  related_name='+', verbose_name=_('age group'))
    street = models.CharField(_('street'), max_length=150)
    city = models.CharField(_('city'), max_length=150)
    postal_code = PostalCodeField(_('postal code'))
    citizenship = models.ForeignKey(Citizenship, on_delete=models.PROTECT,
                                    related_name='+', verbose_name=_('citizenship'))
    phone = models.CharField(_('phone'), max_length=30, blank=True, default='')
    email = EmailField(_('email address'), blank=True, default='')

    school = models.ForeignKey(School, blank=True, null=True, on_delete=models.PROTECT,
                               related_name='+', verbose_name=_('school'))
    school_other = models.CharField(_('other school'), max_length=150, blank=True, default='')
    school_class = models.CharField(_('class'), max_length=30, blank=True, default='')
    health = models.TextField(_('health'), blank=True, default='')

    has_parent1 = models.BooleanField(_('first parent'), default=False)
    parent1_first_name = models.CharField(_('first name'), max_length=30, blank=True, null=True)
    parent1_last_name = models.CharField(_('last name'), max_length=30, blank=True, null=True)
    parent1_street = models.CharField(_('street'), max_length=150, blank=True, null=True)
    parent1_city = models.CharField(_('city'), max_length=150, blank=True, null=True)
    parent1_postal_code = PostalCodeField(_('postal code'), blank=True, null=True)
    parent1_phone = models.CharField(_('phone'), max_length=30, blank=True, null=True)
    parent1_email = EmailField(_('email address'), blank=True, null=True)

    has_parent2 = models.BooleanField(_('second parent'), default=False)
    parent2_first_name = models.CharField(_('first name'), max_length=30, blank=True, null=True)
    parent2_last_name = models.CharField(_('last name'), max_length=30, blank=True, null=True)
    parent2_street = models.CharField(_('street'), max_length=150, blank=True, null=True)
    parent2_city = models.CharField(_('city'), max_length=150, blank=True, null=True)
    parent2_postal_code = PostalCodeField(_('postal code'), blank=True, null=True)
    parent2_phone = models.CharField(_('phone'), max_length=30, blank=True, null=True)
    parent2_email = EmailField(_('email address'), blank=True, null=True)

    answers = models.TextField(_('additional answers'), blank=True, default='{}', editable=False)

    class Meta:
        app_label = 'leprikon'
        ordering = ('last_name', 'first_name')
        verbose_name = _('participant')
        verbose_name_plural = _('participants')

    def __str__(self):
        return '{full_name} ({birth_year})'.format(
            full_name=self.full_name,
            birth_year=self.birth_date.year,
        )

    @cached_property
    def parents(self):
        return list(p for p in [self.parent1, self.parent2] if p is not None)

    @cached_property
    def parent1(self):
        if self.has_parent1:
            return self.Parent(self, 'parent1')
        else:
            return None
    parent1.short_description = _('first parent')

    @cached_property
    def parent2(self):
        if self.has_parent2:
            return self.Parent(self, 'parent2')
        else:
            return None
    parent2.short_description = _('second parent')

    @cached_property
    def all_recipients(self):
        recipients = set(parent.email for parent in self.parents if parent.email)
        if self.email:
            recipients.add(self.email)
        return recipients

    def save(self, *args, **kwargs):
        self.gender = self.birth_num[2:4] > '50' and self.FEMALE or self.MALE
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

    @cached_property
    def birth_date(self):
        return get_birth_date(self.birth_num)

    class Parent(PersonMixin):
        def __init__(self, registration, role):
            self._registration = registration
            self._role = role

        def __getattr__(self, attr):
            return getattr(self._registration, '{}_{}'.format(self._role, attr))

        def __str__(self):
            return self.full_name


class SubjectRegistrationGroup(SchoolMixin, PersonMixin, QuestionsMixin, models.Model):
    registration = models.OneToOneField(SubjectRegistration, on_delete=models.CASCADE,
                                        related_name='group', verbose_name=_('registration'))
    target_group = models.ForeignKey(TargetGroup, on_delete=models.PROTECT,
                                     related_name='+', verbose_name=_('target group'))
    name = models.CharField(_('group name'), blank=True, null=True, max_length=150)
    first_name = models.CharField(_('first name'), max_length=30)
    last_name = models.CharField(_('last name'), max_length=30)
    street = models.CharField(_('street'), max_length=150)
    city = models.CharField(_('city'), max_length=150)
    postal_code = PostalCodeField(_('postal code'))
    phone = models.CharField(_('phone'), max_length=30)
    email = EmailField(_('email address'))
    school = models.ForeignKey(School, blank=True, null=True, on_delete=models.PROTECT,
                               related_name='+', verbose_name=_('school'))
    school_other = models.CharField(_('other school'), max_length=150, blank=True, default='')
    school_class = models.CharField(_('class'), max_length=30, blank=True, default='')

    answers = models.TextField(_('additional answers'), blank=True, default='{}', editable=False)

    class Meta:
        app_label = 'leprikon'
        verbose_name = _('registered group')
        verbose_name_plural = _('registered groups')

    def __str__(self):
        return self.name or self.full_name


class SubjectRegistrationGroupMember(models.Model):
    registration = models.ForeignKey(SubjectRegistration, on_delete=models.CASCADE,
                                     related_name='group_members', verbose_name=_('registration'))
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


class SubjectRegistrationBillingInfo(models.Model):
    registration = models.OneToOneField(SubjectRegistration, on_delete=models.CASCADE,
                                        related_name='billing_info', verbose_name=_('registration'))
    name = models.CharField(_('name'), max_length=150)
    street = models.CharField(_('street'), max_length=150, blank=True, null=True)
    city = models.CharField(_('city'), max_length=150, blank=True, null=True)
    postal_code = PostalCodeField(_('postal code'), blank=True, null=True)
    company_num = models.CharField(_('company number'), max_length=8, blank=True, null=True)
    vat_number = models.CharField(_('VAT number'), max_length=10, blank=True, null=True)
    contact_person = models.CharField(_('contact person'), max_length=60, blank=True, null=True)
    phone = models.CharField(_('phone'), max_length=30, blank=True, default='')
    email = EmailField(_('email address'), blank=True, default='')
    employee = models.CharField(_('employee ID'), max_length=150, blank=True, default='')

    class Meta:
        app_label = 'leprikon'
        verbose_name = _('billing information')
        verbose_name_plural = _('billing information')

    def __str__(self):
        return self.name

    @cached_property
    def address(self):
        return ', '.join(filter(bool, (self.street, self.city, self.postal_code)))
    address.short_description = _('address')


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

    registration = models.ForeignKey(SubjectRegistration, on_delete=models.PROTECT,
                                     related_name='payments', verbose_name=_('registration'))
    accounted = models.DateTimeField(_('accounted time'), default=timezone.now)
    payment_type = models.CharField(_('payment type'), max_length=30, choices=payment_type_labels.items())
    amount = PriceField(_('amount'), help_text=_('positive value for payment, negative value for return'))
    note = models.CharField(_('note'), max_length=300, blank=True, default='')
    related_payment = models.OneToOneField('self', blank=True, limit_choices_to={
        'payment_type__in': (PAYMENT_TRANSFER, RETURN_TRANSFER)
    }, null=True, on_delete=models.PROTECT, related_name='related_payments', verbose_name=_('related payment'))
    bankreader_transaction = models.OneToOneField(BankreaderTransaction, blank=True, null=True,
                                                  on_delete=models.PROTECT, verbose_name=_('bank account transaction'))
    pays_payment = models.OneToOneField(PaysPayment, blank=True, editable=False,
                                        limit_choices_to={'status': PaysPayment.REALIZED},
                                        null=True, on_delete=models.PROTECT, verbose_name=_('online payment'))
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT,
                                    related_name='+', verbose_name=_('received by'))

    class Meta:
        app_label = 'leprikon'
        verbose_name = _('payment')
        verbose_name_plural = _('payments')
        ordering = ('accounted',)

    def __str__(self):
        return '{payment_type} {amount}'.format(
            payment_type=self.payment_type_label,
            amount=currency(abs(self.amount)),
        )

    @cached_property
    def organization(self):
        return (
            self.registration.subject.organization or
            self.registration.subject.subject_type.organization or
            LeprikonSite.objects.get_current().organization or
            Organization()
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
        accounted=timezone.make_aware(datetime.combine(transaction.accounted_date, time(12))),
        payment_type=SubjectPayment.PAYMENT_BANK if transaction.amount >= 0 else SubjectPayment.RETURN_BANK,
        amount=transaction.amount,
        note=_('imported from account statement'),
        bankreader_transaction=transaction,
    )
