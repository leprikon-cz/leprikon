from datetime import date

from cms.models import CMSPlugin
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from ..utils import comma_separated
from .startend import StartEndMixin
from .utils import change_year


class SchoolYearManager(models.Manager):
    def get_current(self):
        # by default use last active year
        school_year = self.filter(active=True).order_by("-year").first()
        if school_year is None:
            # Create or activate current year
            if date.today().month < 7:
                year = date.today().year - 1
            else:
                year = date.today().year
            school_year = SchoolYear.objects.get_or_create(year=year)[0]
            school_year.active = True
            school_year.save()
        return school_year


class SchoolYear(models.Model):
    year = models.IntegerField(_("year"), unique=True, help_text=_("Only the first of the two years."))
    active = models.BooleanField(_("active"), default=False)

    objects = SchoolYearManager()

    class Meta:
        app_label = "leprikon"
        ordering = ("-year",)
        verbose_name = _("school year")
        verbose_name_plural = _("school years")

    def __str__(self):
        return self.name

    def delete(self):
        if self.courses.count() or self.events.count():
            raise Exception(_("Can not delete sclool year with courses or events."))
        super().delete()

    @cached_property
    def name(self):
        return "{}/{}".format(self.year, self.year + 1)


class SchoolYearDivision(models.Model):
    school_year = models.ForeignKey(
        SchoolYear, on_delete=models.CASCADE, related_name="divisions", verbose_name=_("school year")
    )
    name = models.CharField(_("division name"), max_length=150)
    period_name = models.CharField(_("period name"), max_length=150)

    class Meta:
        app_label = "leprikon"
        ordering = ("name",)
        unique_together = (("school_year", "name"),)
        verbose_name = _("school year division")
        verbose_name_plural = _("school year divisions")

    def __str__(self):
        return self.name

    @cached_property
    def all_periods(self):
        return list(self.periods.all())

    def copy_to_school_year(old, school_year):
        new = SchoolYearDivision.objects.get(id=old.id)
        new.id, new.pk = None, None
        new.school_year = school_year
        new.save()
        year_delta = school_year.year - old.school_year.year
        periods = []
        for period in old.all_periods:
            periods.append(
                SchoolYearPeriod(
                    school_year_division=new,
                    name=period.name,
                    start=change_year(period.start, year_delta),
                    end=change_year(period.end, year_delta),
                    due_from=change_year(period.due_from, year_delta),
                    due_date=change_year(period.due_date, year_delta),
                )
            )
        SchoolYearPeriod.objects.bulk_create(periods)
        return new

    def get_current_period(self):
        return self.periods.filter(end__gte=date.today()).first() or self.periods.last()


class SchoolYearPeriod(StartEndMixin, models.Model):
    school_year_division = models.ForeignKey(
        SchoolYearDivision, on_delete=models.CASCADE, related_name="periods", verbose_name=_("school year division")
    )
    name = models.CharField(_("name"), max_length=150)
    start = models.DateField(_("start date"))
    end = models.DateField(_("end date"))
    due_from = models.DateField(_("due from"))
    due_date = models.DateField(_("due date"))

    class Meta:
        app_label = "leprikon"
        ordering = ("start",)
        verbose_name = _("school year period")
        verbose_name_plural = _("school year periods")

    def __str__(self):
        return _("{name}, {start:%m/%d %y} - {end:%m/%d %y}").format(
            name=self.name,
            start=self.start,
            end=self.end,
        )


class SchoolYearBlockPlugin(CMSPlugin):
    school_years = models.ManyToManyField(
        SchoolYear,
        related_name="+",
        verbose_name=_("school years"),
        help_text=_("Which school years should the block be visible for?"),
    )

    class Meta:
        app_label = "leprikon"

    def __str__(self):
        return comma_separated(self.all_school_years)

    @cached_property
    def all_school_years(self):
        return list(self.school_years.all())

    def copy_relations(self, oldinstance):
        self.school_years.set(oldinstance.school_years.all())
