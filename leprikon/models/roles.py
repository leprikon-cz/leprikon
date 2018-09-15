from collections import namedtuple

from cms.models import CMSPlugin
from cms.models.fields import PageField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.encoding import python_2_unicode_compatible, smart_text
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from djangocms_text_ckeditor.fields import HTMLField
from filer.fields.image import FilerImageField

from ..conf import settings
from ..forms.leaders import LeaderFilterForm
from .agegroup import AgeGroup
from .citizenship import Citizenship
from .fields import BirthNumberField, PostalCodeField
from .school import School
from .schoolyear import SchoolYear


@python_2_unicode_compatible
class Leader(models.Model):
    user            = models.OneToOneField(settings.AUTH_USER_MODEL, verbose_name=_('user'),
                                           related_name='leprikon_leader', on_delete=models.PROTECT)
    description     = HTMLField(_('description'), blank=True, default='')
    photo           = FilerImageField(verbose_name=_('photo'), blank=True, null=True,
                                      related_name='+', on_delete=models.SET_NULL)
    page            = PageField(verbose_name=_('page'), blank=True, null=True,
                                related_name='+', on_delete=models.SET_NULL)
    school_years    = models.ManyToManyField(SchoolYear, verbose_name=_('school years'), related_name='leaders')

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('user__first_name', 'user__last_name')
        verbose_name        = _('leader')
        verbose_name_plural = _('leaders')

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
        return '{} {}'.format(self.first_name, self.last_name).strip()

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
        from .courses import CourseJournalLeaderEntry
        return CourseJournalLeaderEntry.objects.filter(
            timesheet__leader                   = self,
            course_entry__course__school_year   = school_year,
        ).exclude(course_entry__course__in      = self.subjects.all())

    SubjectsGroup = namedtuple('SubjectsGroup', ('subject_type', 'subjects'))

    def get_subjects_by_types(self):
        from .subjects import SubjectType
        return (
            self.SubjectsGroup(
                subject_type = subject_type,
                subjects = subject_type.subjects.filter(leaders=self)
            )
            for subject_type in SubjectType.objects.all()
        )



@python_2_unicode_compatible
class Contact(models.Model):
    leader          = models.ForeignKey(Leader, verbose_name=_('leader'), related_name='contacts')
    contact_type    = models.CharField(_('contact type'), max_length=30,
                                       choices=settings.LEPRIKON_CONTACT_TYPES)
    contact         = models.CharField(_('contact'), max_length=250)
    order           = models.IntegerField(_('order'), blank=True, default=0)
    public          = models.BooleanField(_('public'), default=False)

    CONTACT_TYPES   = dict(settings.LEPRIKON_CONTACT_TYPES)

    class Meta:
        app_label           = 'leprikon'
        ordering            = ('order',)
        verbose_name        = _('contact')
        verbose_name_plural = _('contacts')

    def __str__(self):
        return '{}, {}: {}'.format(self.leader.full_name, self.contact_type_name, self.contact)

    @cached_property
    def contact_type_name(self):
        return self.CONTACT_TYPES[self.contact_type]



@python_2_unicode_compatible
class Parent(models.Model):
    user            = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user'),
                                        related_name='leprikon_parents')
    first_name      = models.CharField(_('first name'),   max_length=30)
    last_name       = models.CharField(_('last name'),    max_length=30)
    street          = models.CharField(_('street'),       max_length=150)
    city            = models.CharField(_('city'),         max_length=150)
    postal_code     = PostalCodeField(_('postal code'))
    email           = models.EmailField(_('email address'), blank=True, default='')
    phone           = models.CharField(_('phone'), max_length=30)

    class Meta:
        app_label           = 'leprikon'
        verbose_name        = _('parent')
        verbose_name_plural = _('parents')

    def __str__(self):
        return self.full_name

    @cached_property
    def address(self):
        return '{}, {}, {}'.format(self.street, self.city, self.postal_code)

    @cached_property
    def contact(self):
        if self.email and self.phone:
            return '{}, {}'.format(self.phone, self.email)
        else:
            return self.email or self.phone or ''

    @cached_property
    def all_participants(self):
        return list(self.participants.all())

    @cached_property
    def full_name(self):
        return '{} {}'.format(self.first_name, self.last_name)



@python_2_unicode_compatible
class Participant(models.Model):
    user            = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user'),
                                        related_name='leprikon_participants')
    age_group       = models.ForeignKey(AgeGroup, verbose_name=_('age group'),
                                        related_name='+', on_delete=models.PROTECT)
    first_name      = models.CharField(_('first name'),   max_length=30)
    last_name       = models.CharField(_('last name'),    max_length=30)
    birth_num       = BirthNumberField(_('birth number'))
    street          = models.CharField(_('street'),       max_length=150)
    city            = models.CharField(_('city'),         max_length=150)
    postal_code     = PostalCodeField(_('postal code'))
    email           = models.EmailField(_('email address'), blank=True, default='')
    phone           = models.CharField(_('phone'),        max_length=30,  blank=True, default='')
    citizenship     = models.ForeignKey(Citizenship, verbose_name=_('citizenship'),
                                        related_name='+', on_delete=models.PROTECT)
    school          = models.ForeignKey(School, verbose_name=_('school'), blank=True, null=True,
                                        related_name='participants', on_delete=models.PROTECT)
    school_other    = models.CharField(_('other school'), max_length=150, blank=True, default='')
    school_class    = models.CharField(_('class'),        max_length=30,  blank=True, default='')
    health          = models.TextField(_('health'), blank=True, default='')
    MALE = 'm'
    FEMALE = 'f'
    gender          = models.CharField(_('gender'), max_length=1, editable=False,
                                       choices=((MALE, _('male')), (FEMALE, _('female'))))

    class Meta:
        app_label           = 'leprikon'
        verbose_name        = _('participant')
        verbose_name_plural = _('participants')
        unique_together     = (('user', 'birth_num'),)

    def __str__(self):
        return _('{first_name} {last_name} ({birth_num})').format(
            first_name  = self.first_name,
            last_name   = self.last_name,
            birth_num   = self.birth_num,
        )

    def validate_unique(self, exclude=None):
        try:
            # perform the all unique checks, do not exclude anything
            super(Participant, self).validate_unique(None)
        except ValidationError:
            # The only unique constraint is on birth_num and user.
            # Let's use nice birth_num related message instead of the default one.
            raise ValidationError(
                message={'birth_num': _('You have already entered participant with this birth number')},
            )

    def save(self, *args, **kwargs):
        self.gender = self.birth_num[2:4] > '50' and self.FEMALE or self.MALE
        super(Participant, self).save(*args, **kwargs)

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

    @cached_property
    def school_name(self):
        return self.school and smart_text(self.school) or self.school_other

    @cached_property
    def school_and_class(self):
        if self.school_name and self.school_class:
            return '{}, {}'.format(self.school_name, self.school_class)
        else:
            return self.school_name or self.school_class or ''



class LeaderPlugin(CMSPlugin):
    leader      = models.ForeignKey(Leader, verbose_name=_('leader'), related_name='+')
    template    = models.CharField(
        _('template'), max_length=100,
        choices=settings.LEPRIKON_LEADER_TEMPLATES,
        default=settings.LEPRIKON_LEADER_TEMPLATES[0][0],
        help_text=_('The template used to render plugin.'),
    )

    class Meta:
        app_label = 'leprikon'



class LeaderListPlugin(CMSPlugin):
    school_year = models.ForeignKey(SchoolYear, verbose_name=_('school year'),
                                    related_name='+', blank=True, null=True)
    subject     = models.ForeignKey('leprikon.Subject', verbose_name=_('subject'),
                                    related_name='+', blank=True, null=True)
    template    = models.CharField(
        _('template'), max_length=100,
        choices=settings.LEPRIKON_LEADERLIST_TEMPLATES,
        default=settings.LEPRIKON_LEADERLIST_TEMPLATES[0][0],
        help_text=_('The template used to render plugin.'),
    )

    class Meta:
        app_label = 'leprikon'

    def clean(self):
        if self.school_year and self.subject and self.subject.school_year != self.school_year:
            raise ValidationError({
                'school_year': [_('Selected subject is not in the selected school year.')],
                'subject': [_('Selected subject is not in the selected school year.')],
            })

    def render(self, context):
        if self.subject:
            leaders = self.subject.leaders.all()
        else:
            school_year = (self.school_year or getattr(context.get('request'), 'school_year') or
                           SchoolYear.objects.get_current())
            leaders = school_year.leaders.all()
        context.update({
            'leaders':      leaders,
        })
        return context



class FilteredLeaderListPlugin(CMSPlugin):
    school_year = models.ForeignKey(SchoolYear, verbose_name=_('school year'),
                                    related_name='+', blank=True, null=True)

    class Meta:
        app_label = 'leprikon'

    def render(self, context):
        school_year = (self.school_year or getattr(context.get('request'), 'school_year') or
                       SchoolYear.objects.get_current())
        form = LeaderFilterForm(
            school_year = school_year,
            data=context['request'].GET,
        )
        context.update({
            'school_year':  school_year,
            'form':         form,
            'leaders':      form.get_queryset(),
        })
        return context
