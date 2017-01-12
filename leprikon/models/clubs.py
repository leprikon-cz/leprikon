from __future__ import unicode_literals

import colorsys
from collections import namedtuple
from datetime import date, datetime, timedelta

from cms.models import CMSPlugin
from cms.models.fields import PageField
from django.core.urlresolvers import reverse_lazy as reverse
from django.db import models
from django.dispatch import receiver
from django.utils.encoding import (
    force_text, python_2_unicode_compatible, smart_text,
)
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from djangocms_text_ckeditor.fields import HTMLField
from filer.fields.file import FilerFileField
from filer.fields.image import FilerImageField

from ..conf import settings
from ..mailers import ClubRegistrationMailer
from ..utils import comma_separated, currency
from .agegroup import AgeGroup
from .fields import DAY_OF_WEEK, ColorField, DayOfWeekField, PriceField
from .place import Place
from .question import Question
from .registrations import Registration
from .roles import Leader
from .schoolyear import SchoolYear
from .startend import StartEndMixin
from .utils import PaymentStatus


@python_2_unicode_compatible
class ClubGroup(models.Model):
    name    = models.CharField(_('name'), max_length=150)
    plural  = models.CharField(_('plural'), max_length=150)
    color   = ColorField(_('color'))
    order   = models.IntegerField(_('order'), blank=True, default=0)

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('order',)
        verbose_name        = _('club group')
        verbose_name_plural = _('club groups')

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
            int(r*255),
            int(g*255),
            int(b*255),
        )



@python_2_unicode_compatible
class Club(models.Model):
    school_year = models.ForeignKey(SchoolYear, verbose_name=_('school year'), related_name='clubs')
    name        = models.CharField(_('name'), max_length=150)
    description = HTMLField(_('description'), blank=True, default='')
    groups      = models.ManyToManyField(ClubGroup, verbose_name=_('groups'), related_name='clubs')
    place       = models.ForeignKey(Place, verbose_name=_('place'), related_name='clubs', blank=True, null=True, on_delete=models.SET_NULL)
    age_groups  = models.ManyToManyField(AgeGroup, verbose_name=_('age groups'), related_name='clubs', blank=True)
    leaders     = models.ManyToManyField(Leader, verbose_name=_('leaders'), related_name='clubs', blank=True)
    price       = PriceField(_('price'), blank=True, null=True)
    unit        = models.CharField(_('unit'), max_length=150)
    public      = models.BooleanField(_('public'), default=False)
    reg_active  = models.BooleanField(_('active registration'), default=False)
    photo       = FilerImageField(verbose_name=_('photo'), related_name='+', blank=True, null=True)
    page        = PageField(verbose_name=_('page'), related_name='+', blank=True, null=True, on_delete=models.SET_NULL)
    min_count   = models.IntegerField(_('minimal count'), blank=True, null=True)
    max_count   = models.IntegerField(_('maximal count'), blank=True, null=True)
    risks       = HTMLField(_('risks'), blank=True)
    plan        = HTMLField(_('plan'), blank=True)
    evaluation  = HTMLField(_('evaluation'), blank=True)
    note        = models.CharField(_('note'), max_length=300, blank=True, default='')
    questions   = models.ManyToManyField(Question, verbose_name=_('additional questions'),
                    blank=True,
                    help_text=_('Add additional questions to be asked in the registration form.'))

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('name',)
        verbose_name        = _('club')
        verbose_name_plural = _('clubs')

    def __str__(self):
        return '{} {}'.format(self.school_year, self.name)

    def save(self, *args, **kwargs):
        if self.price is None:
            self.reg_active = False
        super(Club, self).save(*args, **kwargs)

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
    def all_times(self):
        return list(self.times.all())

    @cached_property
    def all_periods(self):
        return list(self.periods.all())

    @cached_property
    def all_questions(self):
        return list(self.questions.all())

    @cached_property
    def all_attachments(self):
        return list(self.attachments.all())

    @cached_property
    def all_registrations(self):
        return list(self.registrations.all())

    @cached_property
    def all_journal_entries(self):
        return list(self.journal_entries.all())

    def get_current_period(self):
        return self.periods.filter(end__gte=date.today()).first() or self.periods.last()

    def get_absolute_url(self):
        return reverse('leprikon:club_detail', args=(self.id,))

    def get_registration_url(self):
        return reverse('leprikon:club_registration_form', args=(self.id,))

    def get_edit_url(self):
        return reverse('admin:leprikon_club_change', args=(self.id,))

    def get_groups_list(self):
        return comma_separated(self.all_groups)
    get_groups_list.short_description = _('groups list')

    def get_leaders_list(self):
        return comma_separated(self.all_leaders)
    get_leaders_list.short_description = _('leaders list')

    def get_times_list(self):
        return comma_separated(self.all_times)
    get_times_list.short_description = _('times')

    def get_periods_list(self):
        return '<br/>'.join(smart_text(p) for p in self.all_periods)
    get_periods_list.short_description = _('periods')
    get_periods_list.allow_tags = True

    def get_next_time(self, now = None):
        try:
            return min(t.get_next_time(now) for t in self.all_times)
        except ValueError:
            return None

    @property
    def registrations_history_registrations(self):
        return ClubRegistration.objects.filter(club_history__club=self).distinct()

    @property
    def active_registrations(self):
        return self.registrations.filter(canceled=None)

    @property
    def inactive_registrations(self):
        return ClubRegistration.objects.filter(club_history__club=self).exclude(id__in=self.active_registrations.all()).distinct()

    def get_active_registrations(self, d):
        ids = ClubRegistrationHistory.objects.filter(club=self, start__lte=d).exclude(end__lt=d).values_list('registration_id', flat=True)
        return ClubRegistration.objects.filter(id__in=ids).exclude(canceled__lt=d).distinct()

    def copy_to_school_year(old, school_year):
        new = Club.objects.get(id=old.id)
        new.id = None
        new.school_year = school_year
        new.public      = False
        new.reg_active  = False
        new.evaluation  = ''
        new.note        = ''
        new.save()
        new.groups      = old.groups.all()
        new.age_groups  = old.age_groups.all()
        new.leaders     = old.leaders.all()
        new.questions   = old.questions.all()
        new.times       = old.times.all()
        new.attachments = old.attachments.all()
        year_offset = school_year.year - old.school_year.year
        for period in old.all_periods:
            period.id = None
            period.club = new
            try:
                period.start = date(period.start.year + year_offset, period.start.month, period.start.day)
            except ValueError:
                # handle leap-year
                period.start = date(period.start.year + year_offset, period.start.month, period.start.day - 1)
            try:
                period.end   = date(period.end.year   + year_offset, period.end.month,   period.end.day)
            except ValueError:
                # handle leap-year
                period.end   = date(period.end.year   + year_offset, period.end.month,   period.end.day - 1)
            period.save()
        return new



@python_2_unicode_compatible
class ClubTime(StartEndMixin, models.Model):
    club        = models.ForeignKey(Club, verbose_name=_('club'), related_name='times')
    day_of_week = DayOfWeekField(_('day of week'))
    start       = models.TimeField(_('start time'), blank=True, null=True)
    end         = models.TimeField(_('end time'), blank=True, null=True)

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('day_of_week', 'start')
        verbose_name        = _('time')
        verbose_name_plural = _('times')

    def __str__(self):
        if self.start is not None and self.end is not None:
            return _('{day}, {start:%H:%M} - {end:%H:%M}').format(
                day     = self.day,
                start   = self.start,
                end     = self.end,
            )
        elif self.start is not None:
            return _('{day}, {start:%H:%M}').format(
                day     = self.day,
                start   = self.start,
            )
        else:
            return force_text(self.day)

    @cached_property
    def day(self):
        return DAY_OF_WEEK[self.day_of_week]

    Time = namedtuple('Time', ('date', 'start', 'end'))

    def get_next_time(self, now = None):
        now = now or datetime.now()
        daydelta = (self.day_of_week - now.isoweekday()) % 7
        if daydelta == 0 and (isinstance(now, date) or self.start is None or self.start <= now.time()):
            daydelta = 7
        if isinstance(now, datetime):
            next_date = now.date() + timedelta(daydelta)
        else:
            next_date = now + timedelta(daydelta)
        return self.Time(
            date    = next_date,
            start   = self.start,
            end     = self.end,
        )



@python_2_unicode_compatible
class ClubPeriod(StartEndMixin, models.Model):
    club        = models.ForeignKey(Club, verbose_name=_('club'), related_name='periods')
    name        = models.CharField(_('name'), max_length=150)
    start       = models.DateField(_('start date'))
    end         = models.DateField(_('end date'))

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('club__name', 'start')
        verbose_name        = _('period')
        verbose_name_plural = _('periods')

    def __str__(self):
        return _('{name}, {start:%m/%d %y} - {end:%m/%d %y}').format(
            name    = self.name,
            start   = self.start,
            end     = self.end,
        )

    @cached_property
    def journal_entries(self):
        return self.club.journal_entries.filter(date__gte=self.start, date__lte=self.end)

    @cached_property
    def all_journal_entries(self):
        return list(self.journal_entries.all())

    @cached_property
    def all_registrations(self):
        return list(self.club.registrations_history_registrations.filter(created__lt=self.end))

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
                reg.participant,
                [
                    reg in entry.all_registrations
                    for entry in self.all_journal_entries
                ]
            ) for reg in self.all_registrations
        ]

    def get_leader_presences(self):
        return [
            self.PresenceRecord(
                leader,
                [
                    entry.all_leader_entries_by_leader.get(leader, None)
                    for entry in self.all_journal_entries
                ]
            ) for leader in self.club.all_leaders
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



@python_2_unicode_compatible
class ClubAttachment(models.Model):
    club    = models.ForeignKey(Club, verbose_name=_('club'), related_name='attachments')
    file    = FilerFileField(related_name='+')
    order   = models.IntegerField(_('order'), blank=True, default=0)

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('order',)
        verbose_name        = _('attachment')
        verbose_name_plural = _('attachments')

    def __str__(self):
        return force_text(self.file)



class ClubRegistration(Registration):
    club = models.ForeignKey(Club, verbose_name=_('club'), related_name='registrations')

    class Meta:
        app_label           = 'leprikon'
        verbose_name        = _('club registration')
        verbose_name_plural = _('club registrations')
        unique_together     = (('club', 'participant_birth_num'),)

    @property
    def subject(self):
        return self.club

    @property
    def periods(self):
        if self.canceled:
            return self.club.periods.filter(end__gt=self.created, start__lt=self.canceled)
        else:
            return self.club.periods.filter(end__gt=self.created)

    @cached_property
    def all_periods(self):
        return list(self.periods.all())

    @cached_property
    def all_discounts(self):
        return list(self.discounts.all())

    @cached_property
    def period_payment_statuses(self):
        return self.get_payment_statuses()

    PeriodPaymentStatus = namedtuple('PeriodPaymentStatus', ('period', 'status'))
    def get_period_payment_statuses(self, d=None):
        paid        = self.get_paid(d)
        for counter, period in enumerate(self.all_periods, start=-len(self.all_periods)):
            try:
                discount_obj = list(filter(lambda d: d.period == period, self.all_discounts)).pop()
                discount    = discount_obj.discount
                explanation = discount_obj.explanation
            except:
                discount    = 0
                explanation = ''
            yield self.PeriodPaymentStatus(
                period  = period,
                status  = PaymentStatus(
                    price       = self.price,
                    discount    = discount,
                    explanation = explanation,
                    paid        = min(self.price - discount, paid) if counter < -1 else paid,
                ),
            )
            paid = max(paid - (self.price - discount), 0)

    @cached_property
    def payment_statuses(self):
        return self.get_payment_statuses()

    PaymentStatuses = namedtuple('PaymentStatuses', ('partial', 'total'))
    def get_payment_statuses(self, d=None):
        if d is None:
            d = date.today()
        partial_price   = self.price * len(list(filter(lambda p: p.start <= d, self.all_periods)))
        total_price     = self.price * len(self.all_periods)
        partial_discount= sum(discount.discount for discount in filter(lambda discount: discount.period.start <= d, self.all_discounts))
        partial_explanation = comma_separated(discount.explanation for discount in filter(lambda discount: discount.period.start <= d, self.all_discounts))
        total_discount  = sum(discount.discount for discount in self.all_discounts)
        total_explanation   = comma_separated(discount.explanation for discount in self.all_discounts)
        paid            = self.get_paid(d)
        return self.PaymentStatuses(
            partial = PaymentStatus(price=partial_price, discount=partial_discount, explanation=partial_explanation, paid=paid),
            total   = PaymentStatus(price=total_price,   discount=total_discount,   explanation=total_explanation,   paid=paid),
        )

    def send_mail(self):
        ClubRegistrationMailer().send_mail(self)



@python_2_unicode_compatible
class ClubRegistrationDiscount(models.Model):
    registration    = models.ForeignKey(ClubRegistration, verbose_name=_('registration'), related_name='discounts')
    period          = models.ForeignKey(ClubPeriod, verbose_name=_('period'), related_name='discounts')
    discount        = PriceField(_('discount'), default=0)
    explanation     = models.CharField(_('discount explanation'), max_length=250, blank=True, default='')

    class Meta:
        app_label           = 'leprikon'
        verbose_name        = _('club discount')
        verbose_name_plural = _('club discounts')
        ordering            = ('period',)
        unique_together     = (('registration', 'period'),)

    def __str__(self):
        return '{registration}, {period}, {discount}'.format(
            registration    = self.registration,
            period          = self.period,
            discount        = currency(self.discount),
        )



class ClubRegistrationHistory(models.Model):
    registration = models.ForeignKey(ClubRegistration, verbose_name=_('club'), related_name='club_history')
    club = models.ForeignKey(Club, verbose_name=_('club'), related_name='registrations_history')
    start = models.DateField()
    end = models.DateField(default=None, null=True)

    class Meta:
        ordering            = ('start',)

    @property
    def club_journal_entries(self):
        qs = ClubJournalEntry.objects.filter(club=self.club, date__gte=self.start)
        if self.end:
            return qs.filter(date__lte=self.end)
        else:
            return qs



@receiver(models.signals.post_save, sender=ClubRegistration)
def update_club_registration_history(sender, instance, created, **kwargs):
    d = date.today()
    # if created or changed
    if (created or ClubRegistrationHistory.objects.filter(registration_id=instance.id, end=None).exclude(club_id=instance.club_id).update(end=d)):
        # reopen or create entry starting today
        ClubRegistrationHistory.objects.filter(registration_id=instance.id, club_id=instance.club_id, start=d).update(end=None) or \
        ClubRegistrationHistory.objects.create(registration_id=instance.id, club_id=instance.club_id, start=d)



@python_2_unicode_compatible
class ClubRegistrationRequest(models.Model):
    user    = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user'), related_name='club_registration_requests', blank=True, null=True)
    club    = models.ForeignKey(Club, verbose_name=_('club'), related_name='registration_requests')
    created = models.DateTimeField(_('time of request'), editable=False, auto_now_add=True)
    contact = models.CharField(_('contact'), max_length=150, help_text=_('Enter phone number, e-mail address or other contact.'))

    class Meta:
        app_label           = 'leprikon'
        verbose_name        = _('club registration request')
        verbose_name_plural = _('club registration requests')
        ordering            = ('created',)
        unique_together     = (('user', 'club'),)

    def __str__(self):
        return '{user}, {club}'.format(
            user    = self.user,
            club    = self.club,
        )



@python_2_unicode_compatible
class ClubPayment(models.Model):
    registration    = models.ForeignKey(ClubRegistration, verbose_name=_('registration'), related_name='payments', on_delete=models.PROTECT)
    date            = models.DateField(_('payment date'))
    amount          = PriceField(_('amount'))

    class Meta:
        app_label           = 'leprikon'
        verbose_name        = _('club payment')
        verbose_name_plural = _('club payments')

    def __str__(self):
        return '{registration}, {amount}'.format(
            registration    = self.registration,
            amount          = currency(self.amount),
        )



def get_default_agenda():
    return '<p>{}</p>'.format(_('instruction on OSH'))

@python_2_unicode_compatible
class ClubJournalEntry(StartEndMixin, models.Model):
    club        = models.ForeignKey(Club, verbose_name=_('club'), related_name='journal_entries', editable=False)
    date        = models.DateField(_('date'))
    start       = models.TimeField(_('start time'), blank=True, null=True,
                    help_text=_('Leave empty, if the club does not take place'))
    end         = models.TimeField(_('end time'), blank=True, null=True,
                    help_text=_('Leave empty, if the club does not take place'))
    agenda      = HTMLField(_('session agenda'), default=get_default_agenda)
    registrations = models.ManyToManyField(ClubRegistration, verbose_name=_('participants'),
                    blank=True, related_name='journal_entries')

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('date', 'start', 'end')
        verbose_name        = _('journal entry')
        verbose_name_plural = _('journal entries')

    def __str__(self):
        return '{club}, {date}'.format(
            club    = self.club.name,
            date    = self.date,
        )

    @cached_property
    def datetime_start(self):
        try:
            return datetime.combine(self.date, self.start)
        except:
            return None

    @cached_property
    def datetime_end(self):
        try:
            return datetime.combine(self.date, self.end)
        except:
            return None

    @cached_property
    def duration(self):
        try:
            return self.datetime_end - self.datetime_start
        except:
            return timedelta()
    duration.short_description = _('duration')

    @cached_property
    def all_registrations(self):
        return list(self.registrations.all())

    @cached_property
    def all_leader_entries(self):
        return list(self.leader_entries.all())

    @cached_property
    def all_leader_entries_by_leader(self):
        return dict((e.timesheet.leader, e) for e in self.all_leader_entries)

    @cached_property
    def all_leaders(self):
        return list(
            le.timesheet.leader for le in self.all_leader_entries
            if le.timesheet.leader in self.club.all_leaders
        )

    @cached_property
    def all_alternates(self):
        return list(
            le.timesheet.leader for le in self.all_leader_entries
            if le.timesheet.leader not in self.club.all_leaders
        )

    @property
    def timesheets(self):
        from .timesheets import Timesheet
        return Timesheet.objects.by_date(self.start).filter(
            leader__in = self.all_leaders + self.all_alternates,
        )

    def save(self, *args, **kwargs):
        if self.end is None:
            self.end = self.start
        super(ClubJournalEntry, self).save(*args, **kwargs)

    def get_edit_url(self):
        return reverse('leprikon:clubjournalentry_update', args=(self.id,))

    def get_delete_url(self):
        return reverse('leprikon:clubjournalentry_delete', args=(self.id,))



@python_2_unicode_compatible
class ClubJournalLeaderEntry(StartEndMixin, models.Model):
    club_entry  = models.ForeignKey(ClubJournalEntry, verbose_name=_('club journal entry'), related_name='leader_entries', editable=False)
    timesheet   = models.ForeignKey('leprikon.Timesheet', verbose_name=_('timesheet'), related_name='club_entries', editable=False, on_delete=models.PROTECT)
    start       = models.TimeField(_('start time'))
    end         = models.TimeField(_('end time'))

    class Meta:
        app_label   = 'leprikon'
        verbose_name        = _('club journal leader entry')
        verbose_name_plural = _('club journal leader entries')
        unique_together     = (('club_entry', 'timesheet'),)

    def __str__(self):
        return '{}'.format(self.duration)

    @cached_property
    def date(self):
        return self.club_entry.date
    date.short_description = _('date')
    date.admin_order_field = 'club_entry__date'

    @cached_property
    def club(self):
        return self.club_entry.club
    club.short_description = _('club')

    @cached_property
    def datetime_start(self):
        return datetime.combine(self.date, self.start)

    @cached_property
    def datetime_end(self):
        return datetime.combine(self.date, self.end)

    @cached_property
    def duration(self):
        return self.datetime_end - self.datetime_start
    duration.short_description = _('duration')

    @property
    def group(self):
        return self.club

    def get_edit_url(self):
        return reverse('leprikon:clubjournalleaderentry_update', args=(self.id,))

    def get_delete_url(self):
        return reverse('leprikon:clubjournalleaderentry_delete', args=(self.id,))



class ClubPlugin(CMSPlugin):
    club        = models.ForeignKey(Club, verbose_name=_('club'))
    template    = models.CharField(_('template'), max_length=100,
                    choices=settings.LEPRIKON_CLUB_TEMPLATES,
                    default=settings.LEPRIKON_CLUB_TEMPLATES[0][0],
                    help_text=_('The template used to render plugin.'))

    class Meta:
        app_label = 'leprikon'



class ClubListPlugin(CMSPlugin):
    school_year = models.ForeignKey(SchoolYear, verbose_name=_('school year'),
                    blank=True, null=True)
    age_groups  = models.ManyToManyField(AgeGroup, verbose_name=_('age groups'),
                    blank=True,
                    help_text=_('Keep empty to skip searching by age groups.'))
    groups      = models.ManyToManyField(ClubGroup, verbose_name=_('club groups'),
                    blank=True,
                    help_text=_('Keep empty to skip searching by groups.'))
    leaders     = models.ManyToManyField(Leader, verbose_name=_('leaders'),
                    blank=True,
                    help_text=_('Keep empty to skip searching by leaders.'))
    template    = models.CharField(_('template'), max_length=100,
                    choices=settings.LEPRIKON_CLUBLIST_TEMPLATES,
                    default=settings.LEPRIKON_CLUBLIST_TEMPLATES[0][0],
                    help_text=_('The template used to render plugin.'))

    class Meta:
        app_label = 'leprikon'

    def copy_relations(self, oldinstance):
        self.groups     = oldinstance.groups.all()
        self.age_groups = oldinstance.age_groups.all()
        self.leaders    = oldinstance.leaders.all()



class FilteredClubListPlugin(CMSPlugin):
    school_year = models.ForeignKey(SchoolYear, verbose_name=_('school year'),
                    blank=True, null=True)

    class Meta:
        app_label = 'leprikon'

