from datetime import date

from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from .startend import StartEndMixin


class SchoolYearManager(models.Manager):
    def get_current(self):
        # by default use last active year
        school_year = self.filter(active=True).order_by('-year').first()
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



@python_2_unicode_compatible
class SchoolYear(models.Model):
    year    = models.IntegerField(_('year'), unique=True)
    active  = models.BooleanField(_('active'), default=False)

    objects = SchoolYearManager()

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('-year',)
        verbose_name        = _('school year')
        verbose_name_plural = _('school years')

    def __str__(self):
        return self.name

    def delete(self):
        if self.courses.count() or self.events.count():
            raise Exception(_('Can not delete sclool year with courses or events.'))
        super(SchoolYear, self).delete()

    @cached_property
    def name(self):
        return '{}/{}'.format(self.year, self.year + 1)



@python_2_unicode_compatible
class SchoolYearDivision(models.Model):
    school_year = models.ForeignKey(SchoolYear, verbose_name=_('school year'), related_name='divisions')
    name        = models.CharField(_('division name'), max_length=150)
    period_name = models.CharField(_('period name'), max_length=150)

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('name',)
        unique_together     = (('school_year', 'name'),)
        verbose_name        = _('school year division')
        verbose_name_plural = _('school year divisions')

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
        year_offset = school_year.year - old.school_year.year
        periods = []
        for period in old.all_periods:
            try:
                start = date(period.start.year + year_offset, period.start.month, period.start.day)
            except ValueError:
                # handle leap-year
                start = date(period.start.year + year_offset, period.start.month, period.start.day - 1)
            try:
                end   = date(period.end.year   + year_offset, period.end.month,   period.end.day)
            except ValueError:
                # handle leap-year
                end   = date(period.end.year   + year_offset, period.end.month,   period.end.day - 1)
            periods.append(SchoolYearPeriod(
                school_year_division=new,
                name=period.name,
                start=start,
                end=end,
            ))
        SchoolYearPeriod.objects.bulk_create(periods)
        return new



@python_2_unicode_compatible
class SchoolYearPeriod(StartEndMixin, models.Model):
    school_year_division = models.ForeignKey(SchoolYearDivision, verbose_name=_('school year division'),
                                             related_name='periods')
    name        = models.CharField(_('name'), max_length=150)
    start       = models.DateField(_('start date'))
    end         = models.DateField(_('end date'))

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('start',)
        verbose_name        = _('school year period')
        verbose_name_plural = _('school year periods')

    def __str__(self):
        return _('{name}, {start:%m/%d %y} - {end:%m/%d %y}').format(
            name    = self.name,
            start   = self.start,
            end     = self.end,
        )
