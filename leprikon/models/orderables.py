from collections import namedtuple
from datetime import date, datetime, timedelta

from cms.models import CMSPlugin
from django.db import models
from django.utils.formats import date_format, time_format
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from ..conf import settings
from .agegroup import AgeGroup
from .department import Department
from .roles import Leader
from .schoolyear import SchoolYear
from .subjects import Subject, SubjectDiscount, SubjectGroup, SubjectRegistration, SubjectType
from .targetgroup import TargetGroup
from .utils import PaymentStatus


class Orderable(Subject):
    duration = models.DurationField(_("duration"), help_text=_("Format: HH:MM:SS"))
    due_from_days = models.IntegerField(
        _("number of days to send the payment request before event date"),
        blank=True,
        null=True,
        help_text=_(
            "If set, payment request will be sent this number of days before event date. "
            "If not set, payment request will be sent when registration is approved."
        ),
    )
    due_date_days = models.IntegerField(_("number of days to due date before event date"), default=0)

    class Meta:
        app_label = "leprikon"
        ordering = ("code", "name")
        verbose_name = _("orderable event")
        verbose_name_plural = _("orderable events")

    @property
    def inactive_registrations(self):
        return self.registrations.filter(canceled__isnull=False)

    def get_times_list(self):
        return self.duration

    get_times_list.short_description = _("duration")

    def copy_to_school_year(old, school_year):
        new = Orderable.objects.get(id=old.id)
        new.id, new.pk = None, None
        new.school_year = school_year
        new.public = False
        new.evaluation = ""
        new.note = ""
        new.save()
        new.groups.set(old.groups.all())
        new.age_groups.set(old.age_groups.all())
        new.target_groups.set(old.target_groups.all())
        for leader in old.all_leaders:
            school_year.leaders.add(leader)
        new.leaders.set(old.all_leaders)
        new.questions.set(old.questions.all())
        new.attachments.set(old.attachments.all())
        return new


class OrderableRegistration(SubjectRegistration):
    subject_type = SubjectType.ORDERABLE
    start_date = models.DateField(_("start date"))
    start_time = models.TimeField(_("start time"), blank=True, null=True)

    class Meta:
        app_label = "leprikon"
        verbose_name = _("orderable event registration")
        verbose_name_plural = _("orderable event registrations")

    def get_payment_status(self, d=None):
        return PaymentStatus(
            price=self.price,
            discount=self.get_discounted(d),
            explanation=",\n".join(
                discount.explanation.strip()
                for discount in self.all_discounts
                if (d is None or discount.accounted.date() <= d) and discount.explanation.strip()
            ),
            paid=self.get_paid(d),
            current_date=d or date.today(),
            due_from=self.payment_requested
            and (
                self.payment_requested.date()
                if self.subject.orderable.due_from_days is None
                else max(
                    self.start_date - timedelta(days=self.subject.orderable.due_from_days),
                    self.payment_requested.date(),
                )
            ),
            due_date=self.payment_requested
            and max(
                self.start_date - timedelta(days=self.subject.orderable.due_date_days),
                self.payment_requested.date() + timedelta(days=self.subject.min_due_date_days),
            ),
        )

    @cached_property
    def end_date(self):
        if self.start_time:
            return (datetime.combine(self.start_date, self.start_time) + self.subject.orderable.duration).date()
        else:
            return self.start_date + self.subject.orderable.duration

    @cached_property
    def end_time(self):
        if self.start_time:
            return (datetime.combine(self.start_date, self.start_time) + self.subject.orderable.duration).time()

    def event_date(self):
        return "{start}{separator}{end}".format(
            start=(
                date_format(datetime.combine(self.start_date, self.start_time), "SHORT_DATETIME_FORMAT")
                if self.start_time
                else date_format(self.start_date, "SHORT_DATE_FORMAT")
            ),
            separator=" - " if self.start_date != self.end_date or self.end_time is not None else "",
            end=(
                (time_format(self.end_time, "TIME_FORMAT") if self.end_time else "")
                if self.start_date == self.end_date
                else (
                    date_format(datetime.combine(self.end_date, self.end_time), "SHORT_DATETIME_FORMAT")
                    if self.end_time
                    else date_format(self.end_date, "SHORT_DATE_FORMAT")
                )
            ),
        )

    event_date.admin_order_field = "start_date"
    event_date.short_description = _("event date")


class OrderableDiscount(SubjectDiscount):
    registration = models.ForeignKey(
        OrderableRegistration, on_delete=models.CASCADE, related_name="discounts", verbose_name=_("registration")
    )

    class Meta:
        app_label = "leprikon"
        verbose_name = _("orderable event discount")
        verbose_name_plural = _("orderable event discounts")
        ordering = ("accounted",)


class OrderablePlugin(CMSPlugin):
    event = models.ForeignKey(Orderable, on_delete=models.CASCADE, related_name="+", verbose_name=_("event"))
    template = models.CharField(
        _("template"),
        max_length=100,
        choices=settings.LEPRIKON_ORDERABLE_TEMPLATES,
        default=settings.LEPRIKON_ORDERABLE_TEMPLATES[0][0],
        help_text=_("The template used to render plugin."),
    )

    class Meta:
        app_label = "leprikon"


class OrderableListPlugin(CMSPlugin):
    school_year = models.ForeignKey(
        SchoolYear, blank=True, null=True, on_delete=models.CASCADE, related_name="+", verbose_name=_("school year")
    )
    departments = models.ManyToManyField(
        Department,
        blank=True,
        related_name="+",
        verbose_name=_("departments"),
        help_text=_("Keep empty to skip searching by departments."),
    )
    event_types = models.ManyToManyField(
        SubjectType,
        blank=True,
        limit_choices_to={"subject_type": SubjectType.ORDERABLE},
        related_name="+",
        verbose_name=_("event types"),
        help_text=_("Keep empty to skip searching by event types."),
    )
    age_groups = models.ManyToManyField(
        AgeGroup,
        blank=True,
        related_name="+",
        verbose_name=_("age groups"),
        help_text=_("Keep empty to skip searching by age groups."),
    )
    target_groups = models.ManyToManyField(
        TargetGroup,
        blank=True,
        related_name="+",
        verbose_name=_("target groups"),
        help_text=_("Keep empty to skip searching by target groups."),
    )
    groups = models.ManyToManyField(
        SubjectGroup,
        blank=True,
        related_name="+",
        verbose_name=_("event groups"),
        help_text=_("Keep empty to skip searching by groups."),
    )
    leaders = models.ManyToManyField(
        Leader,
        verbose_name=_("leaders"),
        blank=True,
        related_name="+",
        help_text=_("Keep empty to skip searching by leaders."),
    )
    template = models.CharField(
        _("template"),
        max_length=100,
        choices=settings.LEPRIKON_ORDERABLELIST_TEMPLATES,
        default=settings.LEPRIKON_ORDERABLELIST_TEMPLATES[0][0],
        help_text=_("The template used to render plugin."),
    )

    class Meta:
        app_label = "leprikon"

    def copy_relations(self, oldinstance):
        self.departments.set(oldinstance.departments.all())
        self.event_types.set(oldinstance.event_types.all())
        self.groups.set(oldinstance.groups.all())
        self.age_groups.set(oldinstance.age_groups.all())
        self.target_groups.set(oldinstance.age_groups.all())
        self.leaders.set(oldinstance.leaders.all())

    @cached_property
    def all_departments(self):
        return list(self.departments.all())

    @cached_property
    def all_event_types(self):
        return list(self.event_types.all())

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

    Group = namedtuple("Group", ("group", "objects"))

    def render(self, context):
        school_year = (
            self.school_year or getattr(context.get("request"), "school_year") or SchoolYear.objects.get_current()
        )
        events = Orderable.objects.filter(school_year=school_year, public=True).distinct()

        if self.all_departments:
            events = events.filter(department__in=self.all_departments)
        if self.all_event_types:
            events = events.filter(subject_type__in=self.all_event_types)
        if self.all_age_groups:
            events = events.filter(age_groups__in=self.all_age_groups)
        if self.all_target_groups:
            events = events.filter(target_groups__in=self.all_target_groups)
        if self.all_leaders:
            events = events.filter(leaders__in=self.all_leaders)
        if self.all_groups:
            events = events.filter(groups__in=self.all_groups)
            groups = self.all_groups
        elif self.all_event_types:
            groups = SubjectGroup.objects.filter(subject_types__in=self.all_event_types)
        else:
            groups = SubjectGroup.objects.all()

        context.update(
            {
                "school_year": school_year,
                "events": events,
                "groups": (self.Group(group=group, objects=events.filter(groups=group)) for group in groups),
            }
        )
        return context


class FilteredOrderableListPlugin(CMSPlugin):
    school_year = models.ForeignKey(
        SchoolYear, blank=True, null=True, on_delete=models.CASCADE, related_name="+", verbose_name=_("school year")
    )
    event_types = models.ManyToManyField(
        SubjectType,
        limit_choices_to={"subject_type": SubjectType.ORDERABLE},
        related_name="+",
        verbose_name=_("event types"),
    )

    class Meta:
        app_label = "leprikon"

    def copy_relations(self, oldinstance):
        self.event_types = oldinstance.event_types.all()

    @cached_property
    def all_event_types(self):
        return list(self.event_types.all())

    def render(self, context):
        school_year = (
            self.school_year or getattr(context.get("request"), "school_year") or SchoolYear.objects.get_current()
        )

        from ..forms.subjects import SubjectFilterForm

        form = SubjectFilterForm(
            subject_type_type=SubjectType.ORDERABLE,
            subject_types=self.all_event_types,
            school_year=school_year,
            is_staff=context["request"].user.is_staff,
            data=context["request"].GET,
        )
        context.update(
            {
                "school_year": school_year,
                "form": form,
                "events": form.get_queryset(),
            }
        )
        return context
