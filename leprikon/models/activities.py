import colorsys
import logging
from collections import namedtuple
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from email.mime.image import MIMEImage
from io import BytesIO
from itertools import chain
from json import dumps, loads
from os.path import basename
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, List, Set, Union
from urllib.parse import urlencode

import segno
from bankreader.models import Transaction as BankreaderTransaction
from cms.models.fields import PageField
from cms.models.pagemodel import Page
from cms.signals.apphook import set_restart_trigger
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _, ngettext
from django_pays import payment_url as pays_payment_url
from django_pays.models import Payment as PaysPayment
from djangocms_text_ckeditor.fields import HTMLField
from filer.fields.file import FilerFileField
from filer.fields.image import FilerImageField
from multiselectfield import MultiSelectField

from ..conf import settings
from ..utils import FEMALE, MALE, attributes, comma_separated, currency, lazy_paragraph as paragraph, localeconv, spayd
from ..utils.calendar import (
    SimpleEvent,
    TimeSlot,
    TimeSlots,
    WeeklyTimes,
    apply_preparation_and_recovery_times,
    get_conflicting_timeslots,
    get_reverse_time_slots,
    get_time_slots_by_weekly_times,
)
from .agegroup import AgeGroup
from .agreements import Agreement, AgreementOption
from .calendar import CalendarEvent, Resource, ResourceGroup
from .citizenship import Citizenship
from .department import Department
from .fields import BirthNumberField, ColorField, EmailField, PostalCodeField, PriceField, UniquePageField
from .leprikonsite import LeprikonSite
from .organizations import Organization
from .pdfmail import PdfExportAndMailMixin
from .place import Place
from .printsetup import PrintSetup
from .question import Question
from .roles import Leader
from .school import School
from .schoolyear import SchoolYear, SchoolYearDivision
from .targetgroup import TargetGroup
from .times import AbstractTime, TimesMixin
from .transaction import AbstractTransaction, Transaction
from .utils import (
    BankAccount,
    PaymentStatus,
    generate_variable_symbol,
    lazy_help_text_with_html_default,
)

if TYPE_CHECKING:
    from .courses import CourseRegistration
    from .events import EventRegistration
    from .orderables import OrderableRegistration

logger = logging.getLogger(__name__)

DEFAULT_TEXTS = {
    "text_registration_received": paragraph(
        _("Hello,\nthank You for submitting the registration.\nWe will inform you about its further processing.")
    ),
    "text_registration_approved": paragraph(
        _(
            "Hello,\nwe are pleased to inform You, that Your registration was approved.\n"
            "We are looking forward to see You."
        )
    ),
    "text_registration_refused": paragraph(
        _("Hello,\nwe are sorry to inform You, that Your registration was refused.")
    ),
    "text_registration_payment_request": paragraph(
        _(
            "Hello,\nwe'd like to ask You to pay for Your registration.\n"
            "If You have already made the payment recently, please ignore this message."
        )
    ),
    "text_registration_refund_offer": paragraph(
        _("Hello,\nYour registration has been overpaid.\nPlease, tell us how you wish us to refund.")
    ),
    "text_registration_canceled": paragraph(_("Hello,\nYour registration was canceled.")),
    "text_discount_granted": paragraph(_("Hello,\nwe have just grated a discount for Your registration.")),
    "text_payment_received": paragraph(
        _("Hello,\nwe have just received Your payment. Thank You.\nPlease see the recipe attached.")
    ),
    "text_payment_returned": paragraph(
        _("Hello,\nwe have just returned Your payment. Thank You.\nPlease see the recipe attached.")
    ),
}


class ActivityModel(models.TextChoices):
    COURSE = "course", _("course")
    EVENT = "event", _("fixed time event")
    ORDERABLE = "orderable", _("orderable event")


class ActivityType(models.Model):
    model = models.CharField(_("data model"), max_length=10, choices=ActivityModel.choices)
    name = models.CharField(_("name (singular)"), max_length=150)
    name_genitiv = models.CharField(_("name (genitiv)"), max_length=150, blank=True)
    name_akuzativ = models.CharField(_("name (akuzativ)"), max_length=150, blank=True)
    plural = models.CharField(_("name (plural)"), max_length=150)
    slug = models.SlugField(unique=True)
    page = UniquePageField(
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="leprikon_activity_type",
        verbose_name=_("page"),
        help_text=_(
            "Select page, where the activities will be listed. New activity type requires a new page. "
            "If You assign an existing page, the current content of the page will be replaced "
            "with the new list of activities."
        ),
    )
    order = models.IntegerField(_("order"), blank=True, default=0)
    questions = models.ManyToManyField(
        Question,
        blank=True,
        related_name="+",
        verbose_name=_("additional questions"),
        help_text=_("Add additional questions to be asked in the registration form."),
    )
    registration_agreements = models.ManyToManyField(
        Agreement,
        blank=True,
        related_name="+",
        verbose_name=_("additional legal agreements"),
        help_text=_("Add additional legal agreements specific to this activity type."),
    )
    reg_print_setup = models.ForeignKey(
        PrintSetup,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("registration print setup"),
    )
    decision_print_setup = models.ForeignKey(
        PrintSetup,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("decision print setup"),
    )
    pr_print_setup = models.ForeignKey(
        PrintSetup,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("payment request print setup"),
    )
    bill_print_setup = models.ForeignKey(
        PrintSetup,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("payment print setup"),
    )
    organization = models.ForeignKey(
        Organization, blank=True, null=True, on_delete=models.SET_NULL, related_name="+", verbose_name=_("organization")
    )
    text_registration_received = HTMLField(
        _("text: registration received"),
        blank=True,
        default="",
        help_text=lazy_help_text_with_html_default("", DEFAULT_TEXTS["text_registration_received"]),
    )
    text_registration_approved = HTMLField(
        _("text: registration approved"),
        blank=True,
        default="",
        help_text=lazy_help_text_with_html_default("", DEFAULT_TEXTS["text_registration_approved"]),
    )
    text_registration_refused = HTMLField(
        _("text: registration refused"),
        blank=True,
        default="",
        help_text=lazy_help_text_with_html_default("", DEFAULT_TEXTS["text_registration_refused"]),
    )
    text_registration_payment_request = HTMLField(
        _("text: registration payment request"),
        blank=True,
        default="",
        help_text=lazy_help_text_with_html_default("", DEFAULT_TEXTS["text_registration_payment_request"]),
    )
    text_registration_refund_offer = HTMLField(
        _("text: registration refund offer"),
        blank=True,
        default="",
        help_text=lazy_help_text_with_html_default("", DEFAULT_TEXTS["text_registration_refund_offer"]),
    )
    text_registration_canceled = HTMLField(
        _("text: registration canceled"),
        blank=True,
        default="",
        help_text=lazy_help_text_with_html_default("", DEFAULT_TEXTS["text_registration_canceled"]),
    )
    text_discount_granted = HTMLField(
        _("text: discount granted"),
        blank=True,
        default="",
        help_text=lazy_help_text_with_html_default("", DEFAULT_TEXTS["text_discount_granted"]),
    )
    text_payment_received = HTMLField(
        _("text: payment received"),
        blank=True,
        default="",
        help_text=lazy_help_text_with_html_default("", DEFAULT_TEXTS["text_payment_received"]),
    )
    text_payment_returned = HTMLField(
        _("text: payment returned"),
        blank=True,
        default="",
        help_text=lazy_help_text_with_html_default("", DEFAULT_TEXTS["text_payment_returned"]),
    )

    class Meta:
        app_label = "leprikon"
        ordering = ("order",)
        verbose_name = _("activity type")
        verbose_name_plural = _("activity types")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.name_genitiv is None:
            self.name_genitiv = self.name
        if self.name_akuzativ is None:
            self.name_akuzativ = self.name
        super().save(*args, **kwargs)

    @cached_property
    def all_questions(self):
        return list(self.questions.all())

    @cached_property
    def all_attachments(self):
        return list(self.attachments.all())

    def get_absolute_url(self):
        return reverse(self.slug + ":activity_list")

    def get_journals_url(self):
        change_list = reverse("admin:leprikon_journal_changelist")
        return f"{change_list}?activity__activity_type__id__exact={self.id}"

    def get_activities_url(self):
        change_list = reverse(f"admin:leprikon_{self.model}_changelist")
        return f"{change_list}?activity_type__id__exact={self.id}"

    def get_activity_variants_url(self):
        change_list = reverse("admin:leprikon_activityvariant_changelist")
        return f"{change_list}?activity__activity_type__id__exact={self.id}"

    def get_registrations_url(self):
        change_list = reverse(f"admin:leprikon_{self.model}registration_changelist")
        return f"{change_list}?activity__activity_type__id__exact={self.id}"

    def get_discounts_url(self):
        change_list = reverse(f"admin:leprikon_{self.model}discount_changelist")
        return f"{change_list}?registration__activity__activity_type__id__exact={self.id}"

    def get_received_payments_url(self):
        change_list = reverse("admin:leprikon_receivedpayment_changelist")
        return f"{change_list}?target_registration__activity__activity_type__id__exact={self.id}"

    def get_returned_payments_url(self):
        change_list = reverse("admin:leprikon_returnedpayment_changelist")
        return f"{change_list}?source_registration__activity__activity_type__id__exact={self.id}"


class ActivityTypeTexts(ActivityType):
    class Meta:
        app_label = "leprikon"
        proxy = True
        verbose_name = _("texts")
        verbose_name_plural = _("texts")


class ActivityTypePrintSetups(ActivityType):
    class Meta:
        app_label = "leprikon"
        proxy = True
        verbose_name = _("print setups")
        verbose_name_plural = _("print setups")


class BaseAttachment(models.Model):
    file = FilerFileField(on_delete=models.CASCADE, related_name="+")
    public = models.BooleanField(
        _("public"), default=True, help_text=_("The attachment will be available before registration.")
    )
    events = MultiSelectField(
        _("send when"),
        blank=True,
        choices=(
            ("registration_received", _("registration received")),
            ("registration_approved", _("registration approved")),
            ("registration_refused", _("registration refused")),
            ("registration_payment_request", _("payment requested")),
            ("registration_refund_offer", _("payment requested")),
            ("registration_canceled", _("registration canceled")),
            ("discount_granted", _("discount granted")),
            ("payment_received", _("payment received")),
            ("payment_returned", _("payment returned")),
        ),
        max_length=250,
        default=[],
        help_text=_("The attachment will be sent with notification on selected events."),
    )
    order = models.IntegerField(_("order"), blank=True, default=0)

    class Meta:
        abstract = True
        app_label = "leprikon"
        ordering = ("order",)
        verbose_name = _("attachment")
        verbose_name_plural = _("attachments")

    def __str__(self):
        return str(self.file)


class ActivityTypeAttachment(BaseAttachment):
    activity_type = models.ForeignKey(
        ActivityType, on_delete=models.CASCADE, related_name="attachments", verbose_name=_("activity type")
    )


class ActivityGroup(models.Model):
    name = models.CharField(_("name"), max_length=150)
    plural = models.CharField(_("plural"), max_length=150)
    color = ColorField(_("color"))
    order = models.IntegerField(_("order"), blank=True, default=0)
    activity_types = models.ManyToManyField(ActivityType, related_name="groups", verbose_name=_("activity type"))

    class Meta:
        app_label = "leprikon"
        ordering = ("order",)
        verbose_name = _("activity group")
        verbose_name_plural = _("activity groups")

    def __str__(self):
        return self.name

    @cached_property
    def font_color(self):
        (h, s, v) = colorsys.rgb_to_hsv(
            int(self.color[1:3], 16) / 255.0,
            int(self.color[3:5], 16) / 255.0,
            int(self.color[5:6], 16) / 255.0,
        )
        if v > 0.5:
            v = 0
        else:
            v = 1
        if s > 0.5:
            s = 0
        else:
            s = 1
        (r, g, b) = colorsys.hsv_to_rgb(h, s, v)
        return "#{:02x}{:02x}{:02x}".format(
            int(r * 255),
            int(g * 255),
            int(b * 255),
        )


class Activity(TimesMixin, models.Model):
    PARTICIPANTS = "P"
    GROUPS = "G"
    REGISTRATION_TYPE_CHOICES = [
        (PARTICIPANTS, _("participants")),
        (GROUPS, _("groups")),
    ]
    REGISTRATION_TYPES = dict(REGISTRATION_TYPE_CHOICES)

    school_year = models.ForeignKey(
        SchoolYear, editable=False, on_delete=models.CASCADE, related_name="activities", verbose_name=_("school year")
    )
    activity_type = models.ForeignKey(
        ActivityType, on_delete=models.PROTECT, related_name="activities", verbose_name=_("activity type")
    )
    registration_type = models.CharField(
        _("registration type"),
        choices=REGISTRATION_TYPE_CHOICES,
        max_length=1,
        help_text=_(
            "Participant details include birth number (birth day), age group, contacts, parent, etc. "
            "Group member details only include name and note."
        ),
    )
    code = models.PositiveSmallIntegerField(_("accounting code"), blank=True, default=0)
    name = models.CharField(_("name"), max_length=150)
    description = HTMLField(_("description"), blank=True, default="")
    department = models.ForeignKey(
        Department,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="activities",
        verbose_name=_("department"),
    )
    groups = models.ManyToManyField(ActivityGroup, verbose_name=_("groups"), related_name="activities", blank=True)
    place = models.ForeignKey(
        Place, blank=True, null=True, on_delete=models.SET_NULL, related_name="activities", verbose_name=_("place")
    )
    age_groups = models.ManyToManyField(AgeGroup, related_name="activities", verbose_name=_("age groups"))
    target_groups = models.ManyToManyField(TargetGroup, related_name="activities", verbose_name=_("target groups"))
    leaders = models.ManyToManyField(Leader, blank=True, related_name="activities", verbose_name=_("leaders"))
    public = models.BooleanField(_("public"), default=False)
    photo = FilerImageField(verbose_name=_("photo"), blank=True, null=True, related_name="+", on_delete=models.SET_NULL)
    page = PageField(blank=True, null=True, on_delete=models.SET_NULL, related_name="+", verbose_name=_("page"))
    min_registrations_count = models.PositiveIntegerField(_("minimal registrations count"), blank=True, null=True)
    max_registrations_count = models.PositiveIntegerField(_("maximal registrations count"), blank=True, null=True)
    note = models.CharField(_("note"), max_length=300, blank=True, default="")
    questions = models.ManyToManyField(
        Question,
        verbose_name=_("additional questions"),
        related_name="+",
        blank=True,
        help_text=_("Add additional questions to be asked in the registration form."),
    )
    registration_agreements = models.ManyToManyField(
        Agreement,
        blank=True,
        related_name="+",
        verbose_name=_("additional legal agreements"),
        help_text=_("Add additional legal agreements specific for this activity."),
    )
    reg_print_setup = models.ForeignKey(
        PrintSetup,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("registration print setup"),
        help_text=_("Only use to set value specific for this activity."),
    )
    decision_print_setup = models.ForeignKey(
        PrintSetup,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("registration print setup"),
        help_text=_("Only use to set value specific for this activity."),
    )
    pr_print_setup = models.ForeignKey(
        PrintSetup,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("payment request print setup"),
        help_text=_("Only use to set value specific for this activity."),
    )
    bill_print_setup = models.ForeignKey(
        PrintSetup,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("payment print setup"),
        help_text=_("Only use to set value specific for this activity."),
    )
    organization = models.ForeignKey(
        Organization,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("organization"),
        help_text=_("Only use to set value specific for this activity."),
    )
    text_registration_received = HTMLField(_("text: registration received"), blank=True, default="")
    text_registration_approved = HTMLField(_("text: registration approved"), blank=True, default="")
    text_registration_refused = HTMLField(_("text: registration refused"), blank=True, default="")
    text_registration_payment_request = HTMLField(_("text: registration payment request"), blank=True, default="")
    text_registration_refund_offer = HTMLField(_("text: registration refund offer"), blank=True, default="")
    text_registration_canceled = HTMLField(_("text: registration canceled"), blank=True, default="")
    text_discount_granted = HTMLField(_("text: discount granted"), blank=True, default="")
    text_payment_received = HTMLField(_("text: payment received"), blank=True, default="")
    text_payment_returned = HTMLField(_("text: payment returned"), blank=True, default="")

    class Meta:
        app_label = "leprikon"
        ordering = ("code", "name")
        verbose_name = _("activity")
        verbose_name_plural = _("activities")

    def __str__(self):
        return "{} {}".format(self.school_year, self.display_name)

    def save(self, *args, **kwargs):
        # For some reason django doesn't set the default value for code,
        # which leads to database error.
        self.code = self.code or 0
        super().save(*args, **kwargs)

    @cached_property
    def price_text(self) -> str:
        return " | ".join(set(v.price_text for v in self.all_variants))

    @cached_property
    def registration_type_participants(self):
        return self.registration_type == self.PARTICIPANTS

    @cached_property
    def registration_type_groups(self):
        return self.registration_type == self.GROUPS

    @cached_property
    def activity(self):
        if self.activity_type.model == ActivityModel.COURSE:
            return self.course
        else:
            return self.event

    @cached_property
    def display_name(self):
        if settings.LEPRIKON_SHOW_ACTIVITY_CODE and self.code:
            return f"{self.code} – {self.name}"
        else:
            return self.name

    @cached_property
    def all_variants(self) -> List["ActivityVariant"]:
        return list(self.variants.all())

    @cached_property
    def all_available_variants(self) -> List["ActivityVariant"]:
        return [variant for variant in self.all_variants if variant.registration_allowed]

    @cached_property
    def all_groups(self) -> List["ActivityGroup"]:
        return list(self.groups.all())

    @cached_property
    def all_age_groups(self) -> List["AgeGroup"]:
        return list(self.age_groups.all())

    @cached_property
    def all_target_groups(self) -> List["TargetGroup"]:
        return list(self.target_groups.all())

    @cached_property
    def all_leaders(self) -> List[Leader]:
        return list(self.leaders.all())

    @cached_property
    def all_questions(self) -> Set["Question"]:
        return set(self.activity_type.all_questions + list(self.questions.all()))

    @cached_property
    def all_attachments(self) -> List["ActivityAttachment"]:
        return list(self.attachments.all())

    @cached_property
    def public_attachments(self):
        return [
            attachment
            for attachment in (self.activity_type.all_attachments + self.all_attachments)
            if attachment.public
        ]

    @cached_property
    def all_registrations(self) -> List["Registration"]:
        return list(self.registrations.all())

    @cached_property
    def reg_from(self):
        now = timezone.now()
        if any(variant.reg_to and variant.reg_to > now and variant.reg_from is None for variant in self.all_variants):
            return None
        try:
            return min(
                variant.reg_from
                for variant in self.all_variants
                if variant.reg_from and (variant.reg_to is None or variant.reg_to > now)
            )
        except ValueError:
            return None

    @cached_property
    def reg_to(self):
        now = timezone.now()
        if any(
            variant.reg_from and variant.reg_from <= now and variant.reg_to is None for variant in self.all_variants
        ):
            return None
        try:
            return max(
                variant.reg_to
                for variant in self.all_variants
                if variant.reg_to and (variant.reg_from is None or variant.reg_from <= now)
            )
        except ValueError:
            return None

    @cached_property
    def registration_allowed(self):
        return any(variant.registration_allowed for variant in self.all_variants)

    @property
    def registration_not_allowed_message(self):
        now = timezone.now()
        if self.reg_from > now:
            return _("Registering will start on {}.").format(self.reg_from)
        if self.reg_to < now:
            return _("Registering ended on {}").format(self.reg_to)

    @property
    def full(self):
        return self.max_registrations_count and self.active_registrations_count >= self.max_registrations_count

    @property
    def over_capapcity(self):
        return self.max_registrations_count and self.active_registrations_count > self.max_registrations_count

    def get_absolute_url(self):
        return reverse(self.activity_type.slug + ":activity_detail", args=(self.id,))

    def get_registration_url(self):
        return reverse(self.activity_type.slug + ":registration_form", args=(self.id,))

    def get_edit_url(self):
        return reverse("admin:leprikon_{}_change".format(self.activity._meta.model_name), args=(self.id,))

    @attributes(short_description=_("age groups list"))
    def get_age_groups_list(self):
        return comma_separated(self.all_age_groups)

    @attributes(short_description=_("groups list"))
    def get_groups_list(self):
        return comma_separated(self.all_groups)

    @attributes(short_description=_("leaders list"))
    def get_leaders_list(self):
        return comma_separated(self.all_leaders)

    @attributes(short_description=_("target groups list"))
    def get_target_groups_list(self):
        return comma_separated(self.all_target_groups)

    def get_print_setup(self, event):
        return PrintSetup()

    def get_template_variants(self):
        return (
            self.activity_type.slug,
            self.activity_type.model,
            "activity",
        )

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

    @property
    def unapproved_registrations(self):
        return self.active_registrations.filter(approved=None)

    @cached_property
    def unapproved_registrations_count(self):
        return self.unapproved_registrations.count()

    @cached_property
    def all_unapproved_registrations(self):
        return list(self.unapproved_registrations.all())

    @property
    def inactive_registrations(self):
        return self.registrations.filter(canceled__isnull=False)

    @cached_property
    def all_inactive_registrations(self):
        return list(self.inactive_registrations.all())

    @cached_property
    def all_journals(self):
        return list(self.journals.all())

    @cached_property
    def all_registration_agreements(self):
        return sorted(
            chain(
                self.registration_agreements.all(),
                self.activity_type.registration_agreements.all(),
                LeprikonSite.objects.get_current().registration_agreements.all(),
            ),
            key=lambda agreement: agreement.order,
        )


class ActivityTime(AbstractTime):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name="times", verbose_name=_("course"))

    class Meta:
        app_label = "leprikon"
        ordering = ("start_date", "days_of_week", "start_time")
        verbose_name = _("time")
        verbose_name_plural = _("times")


class ActivityVariant(models.Model):
    activity = models.ForeignKey(
        Activity, on_delete=models.CASCADE, related_name="variants", verbose_name=_("activity")
    )
    name = models.CharField(_("variant name"), max_length=150, blank=True, default="")
    description = HTMLField(_("variant description"), blank=True, default="")
    reg_from = models.DateTimeField(_("registration active from"), blank=True, null=True)
    reg_to = models.DateTimeField(_("registration active to"), blank=True, null=True)
    age_groups = models.ManyToManyField(AgeGroup, related_name="activity_variants", verbose_name=_("age groups"))
    target_groups = models.ManyToManyField(
        TargetGroup, related_name="activity_variants", verbose_name=_("target groups")
    )
    require_group_members_list = models.BooleanField(
        _("require group members list"),
        default=False,
        help_text=_(
            "Require group members list to be filled in registration form. "
            "If not set, only the number of group members is required."
        ),
    )
    min_participants_count = models.PositiveIntegerField(
        _("minimal participants / group members count per registration"), default=1
    )
    max_participants_count = models.PositiveIntegerField(
        _("maximal participants / group members count per registration"), default=1
    )
    registration_price = PriceField(_("price per registration"), default=0)
    participant_price = PriceField(_("price per participant"), default=0)
    school_year_division = models.ForeignKey(
        SchoolYearDivision,
        null=True,
        on_delete=models.PROTECT,
        related_name="variants",
        verbose_name=_("school year division"),
    )
    allow_period_selection = models.BooleanField(
        _("allow period selection"),
        default=False,
        help_text=_("allow user to choose school year periods on registration form"),
    )
    required_resources = models.ManyToManyField(
        Resource,
        blank=True,
        related_name="activity_variants",
        verbose_name=_("required resources"),
    )
    required_resource_groups = models.ManyToManyField(
        ResourceGroup,
        blank=True,
        related_name="activity_variants",
        verbose_name=_("required resource groups"),
    )

    order = models.IntegerField(_("order"), blank=True, default=0)

    class Meta:
        app_label = "leprikon"
        ordering = ("activity", "order")
        verbose_name = _("price and registering variant")
        verbose_name_plural = _("price and registering variants")

    def __str__(self):
        return f"{self.activity.display_name} / {self.name}" if self.name else self.activity.display_name

    @cached_property
    def price_text(self) -> str:
        if self.registration_price:
            if self.participant_price:
                price = _("{registration_price} + {participant_price} / participant").format(
                    registration_price=currency(self.registration_price),
                    participant_price=currency(self.participant_price),
                )
            else:
                price = currency(self.registration_price)
        elif self.participant_price:
            price = _("{participant_price} / participant").format(
                participant_price=currency(self.participant_price),
            )
        else:
            return str(_("free"))
        if self.school_year_division:
            return f"{price} / {self.school_year_division.price_unit_name}"
        return price

    def get_price(self, participants_count: int) -> Decimal:
        return self.registration_price + (participants_count * self.participant_price)

    def get_registration_url(self):
        return reverse(self.activity.activity_type.slug + ":registration_form", args=(self.activity_id, self.id))

    @property
    def registration_allowed(self):
        now = timezone.now()
        return (
            (self.reg_from or self.reg_to)
            and (self.reg_from is None or self.reg_from <= now)
            and (self.reg_to is None or self.reg_to > now)
        )

    @property
    def active_registrations(self):
        return self.registrations.filter(canceled=None)

    @property
    def approved_registrations(self):
        return self.active_registrations.exclude(approved=None)

    @property
    def unapproved_registrations(self):
        return self.active_registrations.filter(approved=None)

    def get_conflicting_timeslots(self, start_date: date, end_date: date) -> TimeSlots:
        if start_date > end_date:
            return TimeSlots()
        if self.min_start_date > end_date or (self.max_end_date is not None and self.max_end_date < start_date):
            return TimeSlots.from_date_range(start_date, end_date)
        all_day_conflicting_timeslots = TimeSlots()
        if self.min_start_date > start_date:
            all_day_conflicting_timeslots |= TimeSlots.from_date_range(
                start_date, self.min_start_date - timedelta(days=1)
            )
            start_date = self.min_start_date
        if self.max_end_date is not None and self.max_end_date < end_date:
            all_day_conflicting_timeslots |= TimeSlots.from_date_range(self.max_end_date + timedelta(days=1), end_date)
            end_date = self.max_end_date
        # if max_end_date is lower than min_start_date (today)
        if start_date > end_date:
            return all_day_conflicting_timeslots

        required_resource_groups = list(
            chain(
                ({r.id} for r in self.required_resources.all()),
                (set(r.id for r in rg.resources.all()) for rg in self.required_resource_groups.all()),
            )
        )
        relevant_resource_ids: set[int] = set(chain.from_iterable(required_resource_groups))
        relevant_resources = Resource.objects.filter(id__in=relevant_resource_ids).prefetch_related("availabilities")
        relevant_calendar_events_by_timeslot = CalendarEvent.objects.filter(
            start_date__lte=end_date,
            end_date__gte=start_date,
            is_canceled=False,
        )
        blocking_events = relevant_calendar_events_by_timeslot.filter(blocks_all_resources=True)
        relevant_calendar_events = relevant_calendar_events_by_timeslot.filter(blocks_all_resources=False).filter(
            models.Q(resources__in=relevant_resource_ids)
            | models.Q(resource_groups__resources__in=relevant_resource_ids)
        )

        events: list[SimpleEvent] = [
            SimpleEvent(
                TimeSlot(
                    start=datetime.combine(start_date, time(0)),
                    end=datetime.combine(end_date, time(0)) + timedelta(days=1),
                ),
                required_resource_groups,
            )
        ]

        # unavailable times for each relevant resource
        for resource in relevant_resources:
            available_timeslots = get_time_slots_by_weekly_times(resource.weekly_times, start_date, end_date)
            events.extend(
                SimpleEvent(time_slot, [{resource.id}])
                for time_slot in get_reverse_time_slots(available_timeslots, start_date, end_date)
            )

        # calendar events
        events.extend(event.simple_event for event in relevant_calendar_events)

        conflicting_timeslots = (
            TimeSlots(get_conflicting_timeslots(events))
            | TimeSlots(event.timeslot for event in blocking_events)
            | all_day_conflicting_timeslots
        )

        return apply_preparation_and_recovery_times(
            conflicting_timeslots,
            self.activity.orderable.preparation_time,
            self.activity.orderable.recovery_time,
        )

    def get_available_timeslots(self, start_date: date, end_date: date) -> TimeSlots:
        return get_reverse_time_slots(self.get_conflicting_timeslots(start_date, end_date), start_date, end_date)

    @cached_property
    def weekly_times(self) -> WeeklyTimes:
        return WeeklyTimes(at.weekly_time for at in self.activity.times.all())

    @cached_property
    def min_start_date(self) -> date:
        start_dates = [wt.start_date for wt in self.weekly_times if wt.start_date]
        return max(min(start_dates) if start_dates else date.today(), date.today())

    @cached_property
    def max_end_date(self) -> date | None:
        end_dates = [wt.end_date for wt in self.weekly_times if wt.end_date]
        return max(end_dates) if end_dates else None

    @property
    def full_calendar_setup(self):
        return dumps(
            {
                "businessHours": [
                    {
                        "daysOfWeek": [d.isoweekday() % 7 for d in wt.days_of_week],
                        "startTime": wt.start_time.strftime("%H:%M"),
                        "endTime": "24:00" if wt.end_time == time(0) else wt.end_time.strftime("%H:%M"),
                    }
                    for wt in self.weekly_times or WeeklyTimes.unlimited()
                ],
                "minStartDate": self.min_start_date.strftime("%Y-%m-%d"),
                "maxEndDate": self.max_end_date.strftime("%Y-%m-%d") if self.max_end_date else None,
                "duration": self.activity.orderable.duration.seconds,
                "locale": settings.LANGUAGE_CODE,
                "buttonText": {
                    "today": str(_("today")),
                    "month": str(_("month")),
                    "week": str(_("week")),
                    "day": str(_("day")),
                    "list": str(_("list")),
                },
                "unavailableDatesUrl": reverse("api:activity-unavailable-dates", args=(self.id,)),
                "businessHoursUrl": reverse("api:activity-business-hours", args=(self.id,)),
                "selectedEventTimeLabel": str(_("selected event time")),
            }
        )


class ActivityAttachment(BaseAttachment):
    activity = models.ForeignKey(
        Activity, on_delete=models.CASCADE, related_name="attachments", verbose_name=_("activity")
    )


class Registration(PdfExportAndMailMixin, models.Model):
    object_name = "registration"
    slug = models.SlugField(editable=False, max_length=250, null=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="leprikon_registrations",
        verbose_name=_("user"),
    )
    activity: Activity = models.ForeignKey(
        Activity, on_delete=models.PROTECT, related_name="registrations", verbose_name=_("activity")
    )
    activity_variant: ActivityVariant = models.ForeignKey(
        ActivityVariant, on_delete=models.PROTECT, related_name="registrations", verbose_name=_("variant")
    )
    calendar_event: CalendarEvent | None = models.OneToOneField(
        CalendarEvent,
        on_delete=models.PROTECT,
        related_name="registration",
        verbose_name=_("calendar event"),
        blank=True,
        null=True,
    )

    participants_count = models.PositiveIntegerField(_("participants count"))
    price = PriceField(_("price"), editable=False)

    created = models.DateTimeField(_("time of registration"), editable=False, auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        editable=False,
        null=True,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name=_("created by"),
    )
    approved = models.DateTimeField(_("time of approval"), editable=False, null=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        editable=False,
        null=True,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name=_("approved by"),
    )
    payment_requested = models.DateTimeField(_("payment request time"), editable=False, null=True)
    payment_requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        editable=False,
        null=True,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name=_("payment requested by"),
    )
    refund_offered = models.DateTimeField(_("payment request time"), editable=False, null=True)
    refund_offered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        editable=False,
        null=True,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name=_("payment requested by"),
    )
    cancelation_requested = models.DateTimeField(_("time of cancellation request"), editable=False, null=True)
    cancelation_requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        editable=False,
        null=True,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name=_("cancelation requested by"),
    )
    canceled = models.DateTimeField(_("time of cancellation"), editable=False, null=True)
    canceled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        editable=False,
        null=True,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name=_("canceled by"),
    )
    note = models.CharField(_("note"), max_length=300, blank=True, default="")

    questions = models.ManyToManyField(Question, editable=False, related_name="registrations")
    agreements = models.ManyToManyField(Agreement, editable=False, related_name="registrations")
    agreement_options = models.ManyToManyField(AgreementOption, blank=True, verbose_name=_("legal agreements"))

    variable_symbol = models.BigIntegerField(_("variable symbol"), db_index=True, editable=False, null=True)

    registration_link = models.ForeignKey(
        "leprikon.RegistrationLink",
        editable=False,
        null=True,
        on_delete=models.SET_NULL,
        related_name="registrations",
        verbose_name=_("registration link"),
    )

    cached_balance = PriceField(_("payments balance"), default=0, editable=False)

    class Meta:
        app_label = "leprikon"
        verbose_name = _("registration")
        verbose_name_plural = _("registrations")

    def __str__(self):
        return "{} - {}".format(
            self.activity,
            (
                self.group
                if self.activity.registration_type_groups
                else comma_separated([p.full_name for p in self.all_participants])
            ),
        )

    def get_changelist_url(self):
        url = reverse(f"admin:leprikon_{self.activityregistration._meta.model_name}_changelist")
        query = {"id": self.id}
        if self.canceled:
            query["canceled"] = "yes"
        return f"{url}?{urlencode(query)}"

    def get_edit_url(self):
        return reverse(f"admin:leprikon_{self.activityregistration._meta.model_name}_change", args=(self.id,))

    def get_payment_request_url(self):
        return reverse("leprikon:registration_payment_request", args=(self.id, self.variable_symbol))

    @cached_property
    def activityregistration(self) -> Union["CourseRegistration", "EventRegistration", "OrderableRegistration"]:
        if self.activity.activity_type.model == ActivityModel.COURSE:
            return self.courseregistration
        elif self.activity.activity_type.model == ActivityModel.EVENT:
            return self.eventregistration
        elif self.activity.activity_type.model == ActivityModel.ORDERABLE:
            return self.orderableregistration
        raise NotImplementedError()

    @cached_property
    def all_participants(self) -> List["RegistrationParticipant"]:
        return list(self.participants.all())

    @attributes(short_description=_("participants"))
    def participants_list(self):
        return "\n".join(map(str, self.all_participants))

    @attributes(short_description=_("participants"))
    def participants_list_html(self):
        if self.all_participants:
            participant_links = []
            for participant in self.all_participants:
                if participant.birth_num:
                    query = dict(participants__birth_num=participant.birth_num)
                else:
                    query = dict(
                        participants__birth_date=participant.birth_date,
                        participants__first_name=participant.first_name,
                        participants__last_name=participant.last_name,
                    )
                url = "?" + urlencode(query)
                count = (
                    type(self)
                    .objects.filter(
                        activity__school_year_id=self.activity.school_year_id,
                        canceled__isnull=not self.canceled,
                        **query,
                    )
                    .count()
                    - 1
                )
                if count:
                    title = ngettext("%d other registration", "%d other registrations", count) % count
                else:
                    title = _("no other registration")
                participant_links.append(f"""<a href="{url}" title="{title}">{participant}""")
            return mark_safe("<br/>".join(participant_links))
        return self.group_members_list_html()

    @cached_property
    def all_group_members(self):
        return list(self.group_members.all())

    @attributes(short_description=_("group members"))
    def group_members_list(self):
        return "\n".join(map(str, self.all_group_members))

    @attributes(short_description=_("group members"))
    def group_members_list_html(self):
        if self.activity_variant.require_group_members_list:
            return mark_safe("<br/>".join(map(str, self.all_group_members)))
        return str(self.participants_count)

    @cached_property
    def all_questions(self):
        return list(self.questions.all())

    @cached_property
    def all_agreements(self) -> List[Agreement]:
        return list(self.agreements.all())

    @cached_property
    def all_agreement_options(self):
        return list(self.agreement_options.all())

    @attributes(short_description=_("agreement options"))
    def agreement_options_list(self):
        lines = []
        for agreement in self.all_agreements:
            lines.append(agreement.name + ":")
            for option in agreement.all_options:
                lines.append(
                    "{checkbox} {option_name}".format(
                        checkbox=("☑" if option.required or option in self.all_agreement_options else "☐"),
                        option_name=option.name,
                    )
                )
        return "\n".join(lines)

    @cached_property
    def all_attachments(self):
        return self.activity.all_attachments + self.activity.activity_type.all_attachments

    @cached_property
    def all_recipients(self):
        recipients = set()
        if self.user.email:
            recipients.add(self.user.email)
        for participant in self.all_participants:
            recipients.update(participant.all_recipients)
        return recipients

    @cached_property
    def all_discounts(self) -> List["ActivityDiscount"]:
        return list(self.discounts.all())

    @cached_property
    def all_received_payments(self) -> List["ReceivedPayment"]:
        return list(self.received_payments.all())

    @cached_property
    def all_returned_payments(self) -> List["ReturnedPayment"]:
        return list(self.returned_payments.all())

    @cached_property
    def payment_status(self) -> PaymentStatus:
        return self.get_payment_status()

    def get_payment_status(self, d=None) -> PaymentStatus:
        return self.activityregistration.get_payment_status(d)

    @cached_property
    def organization(self) -> Organization:
        return (
            self.activity.organization
            or self.activity.activity_type.organization
            or LeprikonSite.objects.get_current().organization
            or Organization()
        )

    @cached_property
    def spayd(self):
        org = self.organization
        return spayd(
            ("ACC", ("%s+%s" % (org.iban, org.bic)) if org.bic else org.iban),
            ("AM", self.payment_status.amount_due),
            ("CC", localeconv["int_curr_symbol"].strip()),
            ("MSG", "%s, %s" % (self.activity.name[:29], str(self)[:29])),
            ("RN", slugify(self.organization.name).replace("*", "")[:35]),
            ("X-VS", self.variable_symbol),
        )

    @cached_property
    def payment_url(self):
        leprikon_site = LeprikonSite.objects.get_current()
        return pays_payment_url(
            gateway=leprikon_site.payment_gateway,
            order_id=self.variable_symbol,
            amount=self.payment_status.amount_due,
            email=self.user.email,
        )

    @cached_property
    def price_text(self) -> str:
        price = currency(self.price)
        if self.activity_variant.school_year_division_id:
            return f"{price} / {self.activity_variant.school_year_division.price_unit_name}"
        return price

    @cached_property
    def text_registration_received(self):
        return (
            self.activity.text_registration_received
            or self.activity.activity_type.text_registration_received
            or DEFAULT_TEXTS["text_registration_received"]
        )

    @cached_property
    def text_registration_approved(self):
        return (
            self.activity.text_registration_approved
            or self.activity.activity_type.text_registration_approved
            or DEFAULT_TEXTS["text_registration_approved"]
        )

    @cached_property
    def text_registration_refused(self):
        return (
            self.activity.text_registration_refused
            or self.activity.activity_type.text_registration_refused
            or DEFAULT_TEXTS["text_registration_refused"]
        )

    @cached_property
    def text_registration_payment_request(self):
        return (
            self.activity.text_registration_payment_request
            or self.activity.activity_type.text_registration_payment_request
            or DEFAULT_TEXTS["text_registration_payment_request"]
        )

    @cached_property
    def text_registration_refund_offer(self):
        return (
            self.activity.text_registration_refund_offer
            or self.activity.activity_type.text_registration_refund_offer
            or DEFAULT_TEXTS["text_registration_refund_offer"]
        )

    @cached_property
    def text_registration_canceled(self):
        return (
            self.activity.text_registration_canceled
            or self.activity.activity_type.text_registration_canceled
            or DEFAULT_TEXTS["text_registration_canceled"]
        )

    @cached_property
    def text_discount_granted(self):
        return (
            self.activity.text_discount_granted
            or self.activity.activity_type.text_discount_granted
            or DEFAULT_TEXTS["text_discount_granted"]
        )

    @cached_property
    def text_payment_received(self):
        return (
            self.activity.text_payment_received
            or self.activity.activity_type.text_payment_received
            or DEFAULT_TEXTS["text_payment_received"]
        )

    @cached_property
    def text_payment_returned(self):
        return (
            self.activity.text_payment_returned
            or self.activity.activity_type.text_payment_returned
            or DEFAULT_TEXTS["text_payment_returned"]
        )

    def get_discounts(self, d):
        if d:
            return [p for p in self.all_discounts if p.accounted.date() <= d]
        else:
            return self.all_discounts

    def get_received_payments(self, d):
        if d:
            return [p for p in self.all_received_payments if p.accounted.date() <= d]
        else:
            return self.all_received_payments

    def get_returned_payments(self, d):
        if d:
            return [r for r in self.all_returned_payments if r.accounted.date() <= d]
        else:
            return self.all_returned_payments

    def get_pdf_filename(self, event):
        if event == "payment_request":
            return basename(self.get_payment_request_url())
        if event == "pdf":
            return f"{self.slug}.pdf"
        return f"{self.slug}-{event}.pdf"

    def get_discounted(self, d=None):
        return sum(p.amount for p in self.get_discounts(d))

    def get_received(self, d=None):
        return sum(p.amount for p in self.get_received_payments(d))

    def get_returned(self, d=None):
        return sum(r.amount for r in self.get_returned_payments(d))

    def get_qr_code(self):
        output = BytesIO()
        self.write_qr_code(output)
        output.seek(0)
        return output.read()

    def write_qr_code(self, output):
        segno.make(self.spayd).save(output, kind="PNG")

    def write_pdf(self, event, output):
        if event == "payment_request":
            with NamedTemporaryFile(buffering=0, suffix=".png") as qr_code_file:
                self.write_qr_code(qr_code_file)
                qr_code_file.flush()
                self.qr_code_filename = qr_code_file.name
                return super().write_pdf(event, output)
        else:
            return super().write_pdf(event, output)

    @transaction.atomic
    def approve(self, approved_by):
        if self.approved is None:
            self.canceled = None
            self.canceled_by = None
            self.approved = timezone.now()
            self.approved_by = approved_by
            self.save()
            self.send_mail("approved")
            if not self.payment_requested:
                self.request_payment(approved_by)
            if len(self.activity.all_journals) == 1:
                journal = self.activity.all_journals[0]
                for participant in self.all_participants:
                    journal.participants.add(participant)
        else:
            raise ValidationError(
                (
                    _("Unfortunately, it is not possible to restore canceled registration {r}. Please create new one.")
                    if self.canceled
                    else _("The registration {r} has already been approved.")
                ).format(r=self)
            )

    @transaction.atomic
    def request_payment(self, payment_requested_by):
        if not self.payment_requested:
            self.payment_requested = timezone.now()
            self.payment_requested_by = payment_requested_by
            self.save()
            # refresh all cached statuses
            self = type(self).objects.get(id=self.id)
        if self.payment_status.amount_due:
            self.send_mail("payment_request")

    @transaction.atomic
    def offer_refund(self, refund_offered_by):
        if self.payment_status.overpaid:
            self.refund_offered = timezone.now()
            self.refund_offered_by = refund_offered_by
            self.save()
            self.send_mail("refund_offer")

    @transaction.atomic
    def generate_refund_request(self, generated_by):
        from .refundrequest import RefundRequest

        if not self.payment_status.overpaid:
            return
        remote_accounts = set(
            account
            for account in self.received_payments.annotate(
                account=models.F("bankreader_transaction__remote_account_number")
            ).values_list("account", flat=True)
            if account
        )
        if len(remote_accounts) == 1:
            RefundRequest.objects.create(
                registration=self,
                requested_by=generated_by,
                bank_account=BankAccount(remote_accounts.pop()),
            )

    def refuse(self, refused_by):
        if self.approved is None:
            if self.canceled is None:
                with transaction.atomic():
                    self.canceled = timezone.now()
                    self.canceled_by = refused_by
                    self.save()
                    if self.calendar_event:
                        self.calendar_event.is_canceled = True
                        self.calendar_event.save()
                    self.send_mail("refused")
            else:
                raise ValidationError(_("The registration {r} has already been refued.").format(r=self))
        else:
            raise ValidationError(
                _(
                    "Unfortunately, it is not possible to refuse the registration {r}. However, You may cancel it."
                ).format(r=self)
            )

    def cancel(self, canceled_by):
        if self.approved:
            if self.canceled is None:
                with transaction.atomic():
                    self.canceled = timezone.now()
                    self.canceled_by = canceled_by
                    self.save()
                    if self.calendar_event:
                        self.calendar_event.is_canceled = True
                        self.calendar_event.save()
                    self.send_mail("canceled")
            else:
                raise ValidationError(_("The registration {r} has already been canceled.").format(r=self))
        else:
            raise ValidationError(
                _(
                    "Unfortunately, it is not possible to cancel the registration {r}. However, You may refuse it."
                ).format(r=self)
            )

    def generate_variable_symbol_and_slug(self):
        self.variable_symbol = generate_variable_symbol(self)
        self.slug = "{}-{}".format(
            slugify(
                "{}-{}".format(
                    self.activity.name[:100],
                    (
                        self.group
                        if self.activity.registration_type_groups
                        else comma_separated([p.full_name for p in self.all_participants])
                    ),
                )
            )[:200],
            self.variable_symbol,
        )
        self.save()

    def get_print_setup(self, event):
        if event == "payment_request":
            return (
                self.activity.pr_print_setup
                or self.activity.activity_type.pr_print_setup
                or LeprikonSite.objects.get_current().pr_print_setup
                or PrintSetup()
            )
        if event == "decision":
            return (
                self.activity.decision_print_setup
                or self.activity.activity_type.decision_print_setup
                or LeprikonSite.objects.get_current().decision_print_setup
                or PrintSetup()
            )
        return (
            self.activity.reg_print_setup
            or self.activity.activity_type.reg_print_setup
            or LeprikonSite.objects.get_current().reg_print_setup
            or PrintSetup()
        )

    def get_template_variants(self):
        return (
            self.activity.activity_type.slug,
            self.activity.activity_type.model,
            "activity",
        )

    def get_attachments(self, event):
        attachments = []

        if event == "payment_request":
            if self.organization.iban:
                qr_code = MIMEImage(self.get_qr_code())
                qr_code.add_header("Content-ID", "<qr_code>")
                attachments.append(qr_code)
            attachments.append(self.get_pdf_attachment(event))

        attachments += [
            (basename(attachment.file.file.path), open(attachment.file.file.path, "rb").read())
            for attachment in self.all_attachments
            if f"registration_{event}" in attachment.events
        ]
        return attachments or None


class QuestionsMixin:
    def get_answers(self):
        return loads(self.answers)

    def get_questions_and_answers(self):
        answers = self.get_answers()
        for q in self.registration.all_questions:
            yield {
                "question": q.question,
                "answer": answers.get(q.slug, ""),
            }


class PersonMixin:
    @cached_property
    def full_name(self):
        return "{} {}".format(self.first_name, self.last_name)

    @cached_property
    def address(self):
        return "{}, {}, {}".format(self.street, self.city, self.postal_code)

    @cached_property
    def contact(self):
        if self.email and self.phone:
            return "{}, {}".format(self.phone, self.email)
        else:
            return self.email or self.phone or ""


class SchoolMixin:
    @cached_property
    def school_name(self) -> str:
        return self.school and str(self.school) or self.school_other

    @cached_property
    def school_and_class(self) -> str:
        return "{}, {}".format(self.school_name, self.school_class)


class RegistrationParticipant(SchoolMixin, PersonMixin, QuestionsMixin, models.Model):
    registration = models.ForeignKey(
        Registration, on_delete=models.CASCADE, related_name="participants", verbose_name=_("registration")
    )
    first_name = models.CharField(_("first name"), max_length=30)
    last_name = models.CharField(_("last name"), max_length=30)
    citizenship = models.ForeignKey(
        Citizenship, on_delete=models.PROTECT, related_name="+", verbose_name=_("citizenship")
    )
    birth_num = BirthNumberField(_("birth number"), blank=True, null=True)
    birth_date = models.DateField(_("birth date"))
    gender = models.CharField(
        _("gender"), max_length=1, choices=((MALE, _("male / boy")), (FEMALE, _("female / girl")))
    )
    age_group = models.ForeignKey(AgeGroup, on_delete=models.PROTECT, related_name="+", verbose_name=_("age group"))
    street = models.CharField(_("street"), max_length=150)
    city = models.CharField(_("city"), max_length=150)
    postal_code = PostalCodeField(_("postal code"))
    phone = models.CharField(_("phone"), max_length=30, blank=True, default="")
    email = EmailField(_("email address"), blank=True, default="")

    school = models.ForeignKey(
        School, blank=True, null=True, on_delete=models.PROTECT, related_name="+", verbose_name=_("school")
    )
    school_other = models.CharField(_("other school"), max_length=150, blank=True, default="")
    school_class = models.CharField(_("class"), max_length=30, blank=True, default="")
    health = models.TextField(_("health"), blank=True, default="")

    has_parent1 = models.BooleanField(_("first parent"), default=False)
    parent1_first_name = models.CharField(_("first name"), max_length=30, blank=True, null=True)
    parent1_last_name = models.CharField(_("last name"), max_length=30, blank=True, null=True)
    parent1_street = models.CharField(_("street"), max_length=150, blank=True, null=True)
    parent1_city = models.CharField(_("city"), max_length=150, blank=True, null=True)
    parent1_postal_code = PostalCodeField(_("postal code"), blank=True, null=True)
    parent1_phone = models.CharField(_("phone"), max_length=30, blank=True, null=True)
    parent1_email = EmailField(_("email address"), blank=True, null=True)

    has_parent2 = models.BooleanField(_("second parent"), default=False)
    parent2_first_name = models.CharField(_("first name"), max_length=30, blank=True, null=True)
    parent2_last_name = models.CharField(_("last name"), max_length=30, blank=True, null=True)
    parent2_street = models.CharField(_("street"), max_length=150, blank=True, null=True)
    parent2_city = models.CharField(_("city"), max_length=150, blank=True, null=True)
    parent2_postal_code = PostalCodeField(_("postal code"), blank=True, null=True)
    parent2_phone = models.CharField(_("phone"), max_length=30, blank=True, null=True)
    parent2_email = EmailField(_("email address"), blank=True, null=True)

    answers = models.TextField(_("additional answers"), blank=True, default="{}", editable=False)

    class Meta:
        app_label = "leprikon"
        ordering = ("last_name", "first_name")
        verbose_name = _("participant")
        verbose_name_plural = _("participants")

    def __str__(self):
        return "{full_name} ({birth_year})".format(
            full_name=self.full_name,
            birth_year=self.birth_date.year,
        )

    label = cached_property(__str__)

    @cached_property
    def key(self):
        return (self.first_name.lower(), self.last_name.lower(), self.birth_date)

    @cached_property
    def parents(self):
        return list(p for p in [self.parent1, self.parent2] if p is not None)

    @attributes(short_description=_("first parent"))
    @cached_property
    def parent1(self):
        if self.has_parent1:
            return self.Parent(self, "parent1")
        else:
            return None

    @attributes(short_description=_("second parent"))
    @cached_property
    def parent2(self):
        if self.has_parent2:
            return self.Parent(self, "parent2")
        else:
            return None

    @cached_property
    def all_recipients(self):
        # don't use unverified emails
        # TODO: implement verification process
        return set()
        # recipients = set(parent.email for parent in self.parents if parent.email)
        # if self.email:
        #     recipients.add(self.email)
        # return recipients

    PresenceRecord = namedtuple("PresenceRecord", ("entry", "present"))

    @property
    def presences(self):
        from .journals import JournalEntry

        present_entry_ids = set(self.journal_entries.values_list("id", flat=True))

        return [
            self.PresenceRecord(entry, entry.id in present_entry_ids)
            for entry in JournalEntry.objects.filter(journal__participants=self)
        ]

    def save(self, *args, **kwargs):
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
        super().save(*args, **kwargs)

    class Parent(PersonMixin):
        def __init__(self, registration, role):
            self._registration = registration
            self._role = role

        def __getattr__(self, attr):
            return getattr(self._registration, "{}_{}".format(self._role, attr))

        def __str__(self):
            return self.full_name


class RegistrationGroup(SchoolMixin, PersonMixin, QuestionsMixin, models.Model):
    registration = models.OneToOneField(
        Registration, on_delete=models.CASCADE, related_name="group", verbose_name=_("registration")
    )
    target_group = models.ForeignKey(
        TargetGroup, on_delete=models.PROTECT, related_name="+", verbose_name=_("target group")
    )
    name = models.CharField(_("group name"), blank=True, default="", max_length=150)
    first_name = models.CharField(_("first name"), max_length=30)
    last_name = models.CharField(_("last name"), max_length=30)
    street = models.CharField(_("street"), max_length=150)
    city = models.CharField(_("city"), max_length=150)
    postal_code = PostalCodeField(_("postal code"))
    phone = models.CharField(_("phone"), max_length=30)
    email = EmailField(_("email address"))
    school = models.ForeignKey(
        School, blank=True, null=True, on_delete=models.PROTECT, related_name="+", verbose_name=_("school")
    )
    school_other = models.CharField(_("other school"), max_length=150, blank=True, default="")
    school_class = models.CharField(_("class"), max_length=30, blank=True, default="")

    answers = models.TextField(_("additional answers"), blank=True, default="{}", editable=False)

    class Meta:
        app_label = "leprikon"
        verbose_name = _("registered group")
        verbose_name_plural = _("registered groups")

    def __str__(self):
        return self.name or self.full_name


class RegistrationGroupMember(models.Model):
    registration = models.ForeignKey(
        Registration, on_delete=models.CASCADE, related_name="group_members", verbose_name=_("registration")
    )
    first_name = models.CharField(_("first name"), max_length=30)
    last_name = models.CharField(_("last name"), max_length=30)
    note = models.CharField(_("note"), max_length=150, blank=True, default="")

    class Meta:
        app_label = "leprikon"
        verbose_name = _("group member")
        verbose_name_plural = _("group members")

    def __str__(self):
        return (
            "{full_name} ({note})".format(
                full_name=self.full_name,
                note=self.note,
            )
            if self.note
            else self.full_name
        )

    @cached_property
    def full_name(self):
        return "{} {}".format(self.first_name, self.last_name)


class RegistrationBillingInfo(models.Model):
    registration = models.OneToOneField(
        Registration, on_delete=models.CASCADE, related_name="billing_info", verbose_name=_("registration")
    )
    name = models.CharField(_("name"), max_length=150)
    street = models.CharField(_("street"), max_length=150, blank=True, default="")
    city = models.CharField(_("city"), max_length=150, blank=True, default="")
    postal_code = PostalCodeField(_("postal code"), blank=True, default="")
    company_num = models.CharField(_("company number"), max_length=8, blank=True, default="")
    vat_number = models.CharField(_("VAT number"), max_length=12, blank=True, default="")
    contact_person = models.CharField(_("contact person"), max_length=60, blank=True, default="")
    phone = models.CharField(_("phone"), max_length=30, blank=True, default="")
    email = EmailField(_("email address"), blank=True, default="")
    employee = models.CharField(_("employee ID"), max_length=150, blank=True, default="")

    class Meta:
        app_label = "leprikon"
        verbose_name = _("billing information")
        verbose_name_plural = _("billing information")

    def __str__(self):
        return self.name

    @attributes(short_description=_("address"))
    @cached_property
    def address(self):
        return ", ".join(filter(bool, (self.street, self.city, self.postal_code)))


class ActivityDiscount(AbstractTransaction):
    amount = PriceField(_("discount"), default=0)
    explanation = models.CharField(_("discount explanation"), max_length=250, blank=True, default="")

    class Meta:
        abstract = True
        app_label = "leprikon"
        verbose_name = _("discount")
        verbose_name_plural = _("discounts")
        ordering = ("accounted",)

    def __str__(self):
        return currency(self.amount)


class PaymentMixin:
    @cached_property
    def activity_organization(self):
        return (
            self.registration.activity.organization
            or self.registration.activity.activity_type.organization
            or LeprikonSite.objects.get_current().organization
            or Organization()
        )

    @cached_property
    def slug(self):
        return f"{self.registration.slug}-{self.id}"

    def get_print_setup(self, event):
        return (
            self.registration.activity.bill_print_setup
            or self.registration.activity.activity_type.bill_print_setup
            or LeprikonSite.objects.get_current().bill_print_setup
            or PrintSetup()
        )

    def get_template_variants(self):
        return (
            self.registration.activity.activity_type.slug,
            self.registration.activity.activity_type.model,
            "activity",
        )

    def get_attachments(self, event):
        attachments = []

        if event == "received":
            attachments.append(self.get_pdf_attachment("pdf"))

        attachments += [
            (basename(attachment.file.file.path), open(attachment.file.file.path, "rb").read())
            for attachment in self.registration.all_attachments
            if f"{self.object_name}_{event}" in attachment.events
        ]
        return attachments or None

    @cached_property
    def all_recipients(self):
        return self.registration.all_recipients


class Payment(Transaction):
    object_name = "payment"
    transaction_types = Transaction.ACTIVITIES

    class Meta:
        proxy = True
        verbose_name = _("payment")
        verbose_name_plural = _("payments")

    @cached_property
    def sub_payments(self):
        sub_payments = []
        if self.target_registration:
            sub_payments.append(
                ReceivedPayment(**{key: value for key, value in self.__dict__.items() if key[0] != "_"})
            )
        if self.source_registration:
            sub_payments.append(
                ReturnedPayment(**{key: value for key, value in self.__dict__.items() if key[0] != "_"})
            )
        return sub_payments


class ReceivedPayment(PaymentMixin, Transaction):
    object_name = "received_payment"
    transaction_types = Transaction.PAYMENTS

    class Meta:
        proxy = True
        verbose_name = _("received payment")
        verbose_name_plural = _("received payments")

    @property
    def real_amount(self):
        return self.amount

    @attributes(short_description=_("target registration"))
    @cached_property
    def registration(self):
        return self.target_registration


class ReturnedPayment(PaymentMixin, Transaction):
    object_name = "returned_payment"
    transaction_types = Transaction.RETURNS

    class Meta:
        proxy = True
        verbose_name = _("returned payment")
        verbose_name_plural = _("returned payments")

    @property
    def real_amount(self):
        return -self.amount

    @attributes(short_description=_("source registration"))
    @cached_property
    def registration(self):
        return self.source_registration


@receiver(models.signals.post_save, sender=PaysPayment)
def payment_create_payment(instance, **kwargs):
    payment = instance
    # check realized payment
    if payment.status != PaysPayment.REALIZED:
        return
    # check registration
    try:
        registration = Registration.objects.get(variable_symbol=int(payment.order_id))
    except (ValueError, Registration.DoesNotExist):
        return
    # create payment
    Transaction.objects.create(
        transaction_type=Transaction.PAYMENT_ONLINE,
        target_registration=registration,
        accounted=payment.created,
        amount=payment.amount / payment.base_units,
        note=_("received online payment"),
        pays_payment=payment,
    )


@receiver(models.signals.post_save, sender=ActivityType)
def activity_type_update_page(instance, **kwargs):
    activity_type = instance
    if activity_type.page_id:
        updated = Page.objects.filter(
            application_urls="LeprikonActivityTypeApp",
            application_namespace=activity_type.slug,
        ).exclude(models.Q(id=activity_type.page_id) | models.Q(publisher_draft=activity_type.page_id)).update(
            application_urls=None,
            application_namespace=None,
        ) + Page.objects.filter(
            models.Q(id=activity_type.page_id) | models.Q(publisher_draft=activity_type.page_id)
        ).update(
            application_urls="LeprikonActivityTypeApp",
            application_namespace=activity_type.slug,
        )
    else:
        updated = Page.objects.filter(
            application_urls="LeprikonActivityTypeApp",
            application_namespace=activity_type.slug,
        ).update(
            application_urls=None,
            application_namespace=None,
        )
    if updated:
        set_restart_trigger()


@receiver(models.signals.post_save, sender=Page)
def page_update_activity_type(instance, **kwargs):
    page = instance
    if not page.publisher_is_draft:
        return
    if page.application_urls != "LeprikonActivityTypeApp":
        ActivityType.objects.filter(page=page).update(page=None)
        return
    activity_type = ActivityType.objects.filter(slug=page.application_namespace).first()
    if activity_type is None:
        Page.objects.filter(id=page.id).update(
            application_urls=None,
            application_namespace=None,
        )
        set_restart_trigger()
        return
    ActivityType.objects.filter(page=page).exclude(id=activity_type.id).update(page=None)
    if activity_type.page_id != page.id:
        ActivityType.objects.filter(id=activity_type.id).update(page=page)


@receiver(models.signals.post_save, sender=BankreaderTransaction)
def transaction_create_payment(instance, **kwargs):
    transaction = instance
    # check variable symbol
    if not transaction.variable_symbol:
        return
    # check closure date (use closure date from cached leprikon site)
    max_closure_date = LeprikonSite.objects.get_current().max_closure_date
    if max_closure_date and transaction.accounted_date <= max_closure_date:
        return
    # check registration
    registration = Registration.objects.filter(variable_symbol=transaction.variable_symbol).first()
    if not registration:
        return
    # create payment
    if transaction.amount < 0:
        kwargs = {
            "transaction_type": Transaction.RETURN_BANK,
            "source_registration": registration,
            "amount": -transaction.amount,
        }
    else:
        kwargs = {
            "transaction_type": Transaction.PAYMENT_BANK,
            "target_registration": registration,
            "amount": transaction.amount,
        }
    Transaction.objects.create(
        accounted=timezone.make_aware(datetime.combine(transaction.accounted_date, time(12))),
        note=_("imported from account statement"),
        bankreader_transaction=transaction,
        **kwargs,
    )
