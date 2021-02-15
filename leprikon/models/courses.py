from collections import namedtuple
from datetime import date, datetime, timedelta

from cms.models import CMSPlugin
from django.db import models, transaction
from django.dispatch import receiver
from django.utils.encoding import force_text
from django.utils.formats import date_format
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from ..conf import settings
from ..utils import comma_separated
from .agegroup import AgeGroup
from .department import Department
from .fields import DAY_OF_WEEK, DayOfWeekField
from .journals import JournalEntry
from .roles import Leader
from .schoolyear import SchoolYear, SchoolYearDivision, SchoolYearPeriod
from .startend import StartEndMixin
from .subjects import Subject, SubjectDiscount, SubjectGroup, SubjectRegistration, SubjectType
from .targetgroup import TargetGroup
from .utils import PaymentStatus, change_year


class Course(Subject):
    school_year_division = models.ForeignKey(
        SchoolYearDivision, on_delete=models.PROTECT, related_name="courses", verbose_name=_("school year division")
    )
    allow_period_selection = models.BooleanField(
        _("allow period selection"),
        default=False,
        help_text=_("allow user to choose school year periods on registration form"),
    )

    class Meta:
        app_label = "leprikon"
        ordering = ("code", "name")
        verbose_name = _("course")
        verbose_name_plural = _("courses")

    @cached_property
    def all_times(self):
        return list(self.times.all())

    @cached_property
    def all_periods(self):
        return list(self.school_year_division.periods.all())

    @cached_property
    def all_journal_entries(self):
        return list(self.journal_entries.all())

    def get_times_list(self):
        return comma_separated(self.all_times)

    get_times_list.short_description = _("times")

    def get_next_time(self, now=None):
        try:
            return min(t.get_next_time(now) for t in self.all_times)
        except ValueError:
            return None

    @property
    def registrations_history_registrations(self):
        return CourseRegistration.objects.filter(course_history__course=self).distinct()

    @property
    def inactive_registrations(self):
        return (
            CourseRegistration.objects.filter(course_history__course=self)
            .exclude(id__in=self.active_registrations.all())
            .distinct()
        )

    def copy_to_school_year(old, school_year):
        new = Course.objects.get(id=old.id)
        new.id, new.pk = None, None
        new.school_year = school_year
        new.public = False
        new.evaluation = ""
        new.note = ""
        year_delta = school_year.year - old.school_year.year
        new.school_year_division = (
            SchoolYearDivision.objects.filter(
                school_year=school_year,
                name=old.school_year_division.name,
            ).first()
            or old.school_year_division.copy_to_school_year(school_year)
        )
        new.reg_from = new.reg_from and change_year(new.reg_from, year_delta)
        new.reg_to = new.reg_to and change_year(new.reg_to, year_delta)
        new.save()
        new.times.set(old.times.all())
        new.groups.set(old.groups.all())
        new.age_groups.set(old.age_groups.all())
        new.target_groups.set(old.target_groups.all())
        for leader in old.all_leaders:
            school_year.leaders.add(leader)
        new.leaders.set(old.all_leaders)
        new.questions.set(old.questions.all())
        new.attachments.set(old.attachments.all())
        return new


class CourseTime(StartEndMixin, models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="times", verbose_name=_("course"))
    day_of_week = DayOfWeekField(_("day of week"))
    start = models.TimeField(_("start time"), blank=True, null=True)
    end = models.TimeField(_("end time"), blank=True, null=True)

    class Meta:
        app_label = "leprikon"
        ordering = ("day_of_week", "start")
        verbose_name = _("time")
        verbose_name_plural = _("times")

    def __str__(self):
        if self.start is not None and self.end is not None:
            return _("{day}, {start:%H:%M} - {end:%H:%M}").format(
                day=self.day,
                start=self.start,
                end=self.end,
            )
        elif self.start is not None:
            return _("{day}, {start:%H:%M}").format(
                day=self.day,
                start=self.start,
            )
        else:
            return force_text(self.day)

    @cached_property
    def day(self):
        return DAY_OF_WEEK[self.day_of_week]

    Time = namedtuple("Time", ("date", "start", "end"))

    def get_next_time(self, now=None):
        now = now or datetime.now()
        daydelta = (self.day_of_week - now.isoweekday()) % 7
        if daydelta == 0 and (isinstance(now, date) or self.start is None or self.start <= now.time()):
            daydelta = 7
        if isinstance(now, datetime):
            next_date = now.date() + timedelta(daydelta)
        else:
            next_date = now + timedelta(daydelta)
        return self.Time(
            date=next_date,
            start=self.start,
            end=self.end,
        )


class CourseRegistration(SubjectRegistration):
    subject_type = SubjectType.COURSE

    class Meta:
        app_label = "leprikon"
        verbose_name = _("course registration")
        verbose_name_plural = _("course registrations")

    @cached_property
    def all_registration_periods(self):
        return list(self.course_registration_periods.select_related("period"))

    def get_period_payment_statuses(self, d=None):
        paid = self.get_paid(d)
        for counter, registration_period in enumerate(self.all_registration_periods, start=1):
            period_payment_status = registration_period.get_payment_status(
                paid=paid,
                last_period=counter == len(self.all_registration_periods),
                d=d,
            )
            yield period_payment_status
            paid -= period_payment_status.status.paid
        if not self.all_registration_periods:
            # create fake registration period to ensure some payment status
            registration_period = CourseRegistrationPeriod(
                registration=self,
                period=SchoolYearPeriod(
                    name=_("no period"),
                ),
            )
            yield CourseRegistrationPeriod.PeriodPaymentStatus(
                period=registration_period.period,
                registration_period=registration_period,
                status=PaymentStatus(
                    price=0,
                    discount=0,
                    explanation="",
                    paid=paid,
                    current_date=d,
                    due_from=None,
                    due_date=None,
                ),
            )

    def get_payment_status(self, d=None):
        return sum(pps.status for pps in self.get_period_payment_statuses(d))

    @cached_property
    def period_payment_statuses(self):
        return list(self.get_period_payment_statuses())

    @transaction.atomic
    def request_payment(self, payment_requested_by):
        self.course_registration_periods.filter(
            period__due_from__lte=date.today(),
        ).update(payment_requested=True)
        super().request_payment(payment_requested_by)


class CourseRegistrationPeriod(models.Model):
    registration = models.ForeignKey(
        CourseRegistration,
        on_delete=models.CASCADE,
        related_name="course_registration_periods",
        verbose_name=_("registration"),
    )
    period = models.ForeignKey(
        SchoolYearPeriod,
        on_delete=models.PROTECT,
        related_name="course_registration_periods",
        verbose_name=_("period"),
    )
    payment_requested = models.BooleanField(_("payment requested"), default=False)

    class Meta:
        app_label = "leprikon"
        verbose_name = _("registered period")
        verbose_name_plural = _("registered periods")
        ordering = ("period__start",)

    def __str__(self):
        return str(self.period)

    @cached_property
    def all_discounts(self):
        # use cached self.registration.all_discounts instead of
        # return list(self.discounts.all())
        return [discount for discount in self.registration.all_discounts if discount.registration_period_id == self.id]

    PeriodPaymentStatus = namedtuple(
        "PeriodPaymentStatus",
        ("period", "registration_period", "status"),
    )

    def get_payment_status(self, paid, last_period, d=None):
        if d is None:
            d = date.today()
        discount = sum(discount.amount for discount in self.all_discounts if discount.accounted.date() <= d)
        explanation = ",\n".join(
            discount.explanation.strip()
            for discount in self.all_discounts
            if discount.accounted.date() <= d and discount.explanation.strip()
        )
        return self.PeriodPaymentStatus(
            period=self.period,
            registration_period=self,
            status=PaymentStatus(
                price=self.registration.price,
                discount=discount,
                explanation=explanation,
                paid=min(self.registration.price - discount, paid) if not last_period else paid,
                current_date=d,
                due_from=self.registration.payment_requested
                and max(
                    self.period.due_from,
                    self.registration.payment_requested.date(),
                ),
                due_date=self.registration.payment_requested
                and max(
                    self.period.due_date,
                    self.registration.payment_requested.date()
                    + timedelta(days=self.registration.subject.min_due_date_days),
                ),
            ),
        )


class CourseDiscount(SubjectDiscount):
    registration = models.ForeignKey(
        CourseRegistration,
        on_delete=models.CASCADE,
        related_name="discounts",
        verbose_name=_("registration"),
    )
    registration_period = models.ForeignKey(
        CourseRegistrationPeriod,
        on_delete=models.CASCADE,
        related_name="discounts",
        verbose_name=_("period"),
    )

    @cached_property
    def period(self):
        return self.registration_period.period

    class Meta:
        app_label = "leprikon"
        verbose_name = _("course discount")
        verbose_name_plural = _("course discounts")
        ordering = ("accounted",)


class CourseRegistrationHistory(StartEndMixin, models.Model):
    registration = models.ForeignKey(
        CourseRegistration,
        editable=False,
        on_delete=models.PROTECT,
        related_name="course_history",
        verbose_name=_("course"),
    )
    course = models.ForeignKey(
        Course, editable=False, on_delete=models.PROTECT, related_name="registrations_history", verbose_name=_("course")
    )
    start = models.DateField()
    end = models.DateField(blank=True, null=True)

    class Meta:
        app_label = "leprikon"
        ordering = ("start",)
        verbose_name = _("course registration history")
        verbose_name_plural = _("course registration history")

    def __str__(self):
        return "{course}, {start} - {end}".format(
            course=self.course.name,
            start=date_format(self.start, "SHORT_DATE_FORMAT"),
            end=date_format(self.end, "SHORT_DATE_FORMAT") if self.end else _("now"),
        )

    @property
    def journal_entries(self):
        qs = JournalEntry.objects.filter(subject_id=self.course_id, date__gte=self.start)
        if self.end:
            return qs.filter(date__lte=self.end)
        else:
            return qs

    def save(self, *args, **kwargs):
        if self.id:
            original = self.__class__.objects.get(id=self.id)
            min_journal_date = original.journal_entries.aggregate(models.Min("date"))["date__min"]
            max_journal_date = original.journal_entries.aggregate(models.Max("date"))["date__max"]
            # if journal entry exists, start must be set and lower or equal to min journal date
            if min_journal_date and self.start > min_journal_date:
                self.start = min_journal_date
            # end can not be lower than max journal date
            if self.end and max_journal_date and self.end < max_journal_date:
                self.end = max_journal_date
        super().save(*args, **kwargs)


@receiver(models.signals.post_save, sender=CourseRegistration)
def update_course_registration_history(sender, instance, created, **kwargs):
    if instance.approved:
        d = date.today()
        # if created or changed
        if instance.course_history.count() == 0 or instance.course_history.filter(end=None).exclude(
            course_id=instance.subject_id
        ).update(end=d):
            # reopen or create entry starting today
            (
                CourseRegistrationHistory.objects.filter(
                    registration_id=instance.id,
                    course_id=instance.subject_id,
                    start=d,
                ).update(end=None)
                or CourseRegistrationHistory.objects.create(
                    registration_id=instance.id,
                    course_id=instance.subject_id,
                    start=d,
                )
            )


class CoursePlugin(CMSPlugin):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="+", verbose_name=_("course"))
    template = models.CharField(
        _("template"),
        max_length=100,
        choices=settings.LEPRIKON_COURSE_TEMPLATES,
        default=settings.LEPRIKON_COURSE_TEMPLATES[0][0],
        help_text=_("The template used to render plugin."),
    )

    class Meta:
        app_label = "leprikon"


class CourseListPlugin(CMSPlugin):
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
    course_types = models.ManyToManyField(
        SubjectType,
        blank=True,
        limit_choices_to={"subject_type": SubjectType.COURSE},
        related_name="+",
        verbose_name=_("course types"),
        help_text=_("Keep empty to skip searching by course types."),
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
        verbose_name=_("course groups"),
        help_text=_("Keep empty to skip searching by groups."),
    )
    leaders = models.ManyToManyField(
        Leader,
        blank=True,
        related_name="+",
        verbose_name=_("leaders"),
        help_text=_("Keep empty to skip searching by leaders."),
    )
    template = models.CharField(
        _("template"),
        max_length=100,
        choices=settings.LEPRIKON_COURSELIST_TEMPLATES,
        default=settings.LEPRIKON_COURSELIST_TEMPLATES[0][0],
        help_text=_("The template used to render plugin."),
    )

    class Meta:
        app_label = "leprikon"

    def copy_relations(self, oldinstance):
        self.departments.set(oldinstance.departments.all())
        self.course_types.set(oldinstance.course_types.all())
        self.groups.set(oldinstance.groups.all())
        self.age_groups.set(oldinstance.age_groups.all())
        self.target_groups.set(oldinstance.target_groups.all())
        self.leaders.set(oldinstance.leaders.all())

    @cached_property
    def all_departments(self):
        return list(self.departments.all())

    @cached_property
    def all_course_types(self):
        return list(self.course_types.all())

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
        courses = Course.objects.filter(school_year=school_year, public=True).distinct()

        if self.all_departments:
            courses = courses.filter(department__in=self.all_departments)
        if self.all_course_types:
            courses = courses.filter(subject_type__in=self.all_course_types)
        if self.all_age_groups:
            courses = courses.filter(age_groups__in=self.all_age_groups)
        if self.all_target_groups:
            courses = courses.filter(target_groups__in=self.all_target_groups)
        if self.all_leaders:
            courses = courses.filter(leaders__in=self.all_leaders)
        if self.all_groups:
            courses = courses.filter(groups__in=self.all_groups)
            groups = self.all_groups
        elif self.all_course_types:
            groups = SubjectGroup.objects.filter(subject_types__in=self.all_course_types)
        else:
            groups = SubjectGroup.objects.all()

        context.update(
            {
                "school_year": school_year,
                "courses": courses,
                "groups": (self.Group(group=group, objects=courses.filter(groups=group)) for group in groups),
            }
        )
        return context


class FilteredCourseListPlugin(CMSPlugin):
    school_year = models.ForeignKey(
        SchoolYear, blank=True, null=True, on_delete=models.CASCADE, related_name="+", verbose_name=_("school year")
    )
    course_types = models.ManyToManyField(
        SubjectType,
        limit_choices_to={"subject_type": SubjectType.COURSE},
        related_name="+",
        verbose_name=_("course types"),
    )

    class Meta:
        app_label = "leprikon"

    def copy_relations(self, oldinstance):
        self.course_types.set(oldinstance.course_types.all())

    @cached_property
    def all_course_types(self):
        return list(self.course_types.all())

    def render(self, context):
        school_year = (
            self.school_year or getattr(context.get("request"), "school_year") or SchoolYear.objects.get_current()
        )

        from ..forms.subjects import SubjectFilterForm

        form = SubjectFilterForm(
            subject_type_type=SubjectType.COURSE,
            subject_types=self.all_course_types,
            school_year=school_year,
            is_staff=context["request"].user.is_staff,
            data=context["request"].GET,
        )
        context.update(
            {
                "school_year": school_year,
                "form": form,
                "courses": form.get_queryset(),
            }
        )
        return context
