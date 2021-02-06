from collections import namedtuple

from cms.models import CMSPlugin
from cms.models.fields import PageField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.encoding import smart_text
from django.utils.formats import date_format
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from djangocms_text_ckeditor.fields import HTMLField
from filer.fields.image import FilerImageField

from ..conf import settings
from ..forms.leaders import LeaderFilterForm
from .agegroup import AgeGroup
from .citizenship import Citizenship
from .fields import BirthNumberField, EmailField, PostalCodeField
from .school import School
from .schoolyear import SchoolYear


class Leader(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="leprikon_leader", verbose_name=_("user")
    )
    description = HTMLField(_("description"), blank=True, default="")
    photo = FilerImageField(verbose_name=_("photo"), blank=True, null=True, related_name="+", on_delete=models.SET_NULL)
    page = PageField(verbose_name=_("page"), blank=True, null=True, related_name="+", on_delete=models.SET_NULL)
    school_years = models.ManyToManyField(SchoolYear, related_name="leaders", verbose_name=_("school years"))

    class Meta:
        app_label = "leprikon"
        ordering = ("user__last_name", "user__first_name")
        verbose_name = _("leader")
        verbose_name_plural = _("leaders")

    def __str__(self):
        return self.full_name or self.user.username

    @cached_property
    def first_name(self):
        return self.user.first_name

    @cached_property
    def last_name(self):
        return self.user.last_name

    @cached_property
    def full_name(self):
        return "{} {}".format(self.first_name, self.last_name).strip()

    @cached_property
    def all_contacts(self):
        return list(self.contacts.all())

    @cached_property
    def all_public_contacts(self):
        return list(self.contacts.filter(public=True))

    @cached_property
    def all_school_years(self):
        return list(self.school_years.all())

    def get_alternate_leader_entries(self, school_year):
        from .journals import JournalLeaderEntry

        return JournalLeaderEntry.objects.filter(
            timesheet__leader=self,
            journal_entry__subject__school_year=school_year,
        ).exclude(journal_entry__subject__in=self.subjects.all())

    SubjectsGroup = namedtuple("SubjectsGroup", ("subject_type", "subjects"))

    def get_subjects_by_types(self):
        from .subjects import SubjectType

        return (
            self.SubjectsGroup(subject_type=subject_type, subjects=subject_type.subjects.filter(leaders=self))
            for subject_type in SubjectType.objects.all()
        )


class Contact(models.Model):
    leader = models.ForeignKey(Leader, on_delete=models.CASCADE, related_name="contacts", verbose_name=_("leader"))
    contact_type = models.CharField(_("contact type"), max_length=30, choices=settings.LEPRIKON_CONTACT_TYPES)
    contact = models.CharField(_("contact"), max_length=250)
    order = models.IntegerField(_("order"), blank=True, default=0)
    public = models.BooleanField(_("public"), default=False)

    CONTACT_TYPES = dict(settings.LEPRIKON_CONTACT_TYPES)

    class Meta:
        app_label = "leprikon"
        ordering = ("order",)
        verbose_name = _("contact")
        verbose_name_plural = _("contacts")

    def __str__(self):
        return "{}, {}: {}".format(self.leader.full_name, self.contact_type_name, self.contact)

    @cached_property
    def contact_type_name(self):
        return self.CONTACT_TYPES[self.contact_type]


class Parent(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="leprikon_parents", verbose_name=_("user")
    )
    first_name = models.CharField(_("first name"), max_length=30)
    last_name = models.CharField(_("last name"), max_length=30)
    street = models.CharField(_("street"), max_length=150)
    city = models.CharField(_("city"), max_length=150)
    postal_code = PostalCodeField(_("postal code"))
    email = EmailField(_("email address"), blank=True, default="")
    phone = models.CharField(_("phone"), max_length=30)

    class Meta:
        app_label = "leprikon"
        verbose_name = _("parent")
        verbose_name_plural = _("parents")

    def __str__(self):
        return self.full_name

    @cached_property
    def address(self):
        return "{}, {}, {}".format(self.street, self.city, self.postal_code)

    @cached_property
    def contact(self):
        if self.email and self.phone:
            return "{}, {}".format(self.phone, self.email)
        else:
            return self.email or self.phone or ""

    @cached_property
    def full_name(self):
        return "{} {}".format(self.first_name, self.last_name)


class Participant(models.Model):
    MALE = "m"
    FEMALE = "f"
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="leprikon_participants", verbose_name=_("user")
    )
    age_group = models.ForeignKey(AgeGroup, on_delete=models.PROTECT, related_name="+", verbose_name=_("age group"))
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
    street = models.CharField(_("street"), max_length=150)
    city = models.CharField(_("city"), max_length=150)
    postal_code = PostalCodeField(_("postal code"))
    email = EmailField(_("email address"), blank=True, default="")
    phone = models.CharField(_("phone"), max_length=30, blank=True, default="")
    school = models.ForeignKey(
        School, blank=True, null=True, on_delete=models.PROTECT, related_name="participants", verbose_name=_("school")
    )
    school_other = models.CharField(_("other school"), max_length=150, blank=True, default="")
    school_class = models.CharField(_("class"), max_length=30, blank=True, default="")
    health = models.TextField(_("health"), blank=True, default="")

    class Meta:
        app_label = "leprikon"
        verbose_name = _("participant")
        verbose_name_plural = _("participants")

    def __str__(self):
        return _("{first_name} {last_name} ({birth_date})").format(
            first_name=self.first_name,
            last_name=self.last_name,
            birth_date=date_format(self.birth_date, "SHORT_DATE_FORMAT"),
        )

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

    @cached_property
    def school_name(self):
        return self.school and smart_text(self.school) or self.school_other

    @cached_property
    def school_and_class(self):
        if self.school_name and self.school_class:
            return "{}, {}".format(self.school_name, self.school_class)
        else:
            return self.school_name or self.school_class or ""


class BillingInfo(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="leprikon_billing_info", verbose_name=_("user")
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
        ordering = ("name",)
        verbose_name = _("billing information")
        verbose_name_plural = _("billing information")

    def __str__(self):
        return self.name

    @cached_property
    def address(self):
        return ", ".join(filter(bool, (self.street, self.city, self.postal_code)))

    address.short_description = _("address")


class LeaderPlugin(CMSPlugin):
    leader = models.ForeignKey(Leader, on_delete=models.CASCADE, related_name="+", verbose_name=_("leader"))
    template = models.CharField(
        _("template"),
        max_length=100,
        choices=settings.LEPRIKON_LEADER_TEMPLATES,
        default=settings.LEPRIKON_LEADER_TEMPLATES[0][0],
        help_text=_("The template used to render plugin."),
    )

    class Meta:
        app_label = "leprikon"


class LeaderListPlugin(CMSPlugin):
    school_year = models.ForeignKey(
        SchoolYear, blank=True, null=True, on_delete=models.CASCADE, related_name="+", verbose_name=_("school year")
    )
    subject = models.ForeignKey(
        "leprikon.Subject", blank=True, null=True, on_delete=models.CASCADE, related_name="+", verbose_name=_("subject")
    )
    template = models.CharField(
        _("template"),
        max_length=100,
        choices=settings.LEPRIKON_LEADERLIST_TEMPLATES,
        default=settings.LEPRIKON_LEADERLIST_TEMPLATES[0][0],
        help_text=_("The template used to render plugin."),
    )

    class Meta:
        app_label = "leprikon"

    def clean(self):
        if self.school_year and self.subject and self.subject.school_year != self.school_year:
            raise ValidationError(
                {
                    "school_year": [_("Selected subject is not in the selected school year.")],
                    "subject": [_("Selected subject is not in the selected school year.")],
                }
            )

    def render(self, context):
        if self.subject:
            leaders = self.subject.leaders.all()
        else:
            school_year = (
                self.school_year or getattr(context.get("request"), "school_year") or SchoolYear.objects.get_current()
            )
            leaders = school_year.leaders.all()
        context.update(
            {
                "leaders": leaders,
            }
        )
        return context


class FilteredLeaderListPlugin(CMSPlugin):
    school_year = models.ForeignKey(
        SchoolYear, blank=True, null=True, on_delete=models.CASCADE, related_name="+", verbose_name=_("school year")
    )

    class Meta:
        app_label = "leprikon"

    def render(self, context):
        school_year = (
            self.school_year or getattr(context.get("request"), "school_year") or SchoolYear.objects.get_current()
        )
        form = LeaderFilterForm(
            school_year=school_year,
            data=context["request"].GET,
        )
        context.update(
            {
                "school_year": school_year,
                "form": form,
                "leaders": form.get_queryset(),
            }
        )
        return context
