from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from ..models.courses import Course
from ..models.events import Event
from ..models.roles import Leader
from ..models.schoolyear import SchoolYear
from ..models.subjects import Subject, SubjectGroup, SubjectType


class SchoolYearListFilter(admin.FieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        try:
            request.school_year = SchoolYear.objects.get(year=params['year'])
        except:
            pass
        self.school_year = request.school_year
        super(SchoolYearListFilter, self).__init__(field, request, params, model, model_admin, field_path)

    def expected_parameters(self):
        return ['year']

    def choices(self, cl):
        return [
            {
                'selected': school_year == self.school_year,
                'query_string': cl.get_query_string({'year': school_year.year}),
                'display': school_year,
            }
            for school_year in SchoolYear.objects.all()
        ]

    def queryset(self, request, queryset):
        return queryset.filter(**{self.field_path: self.school_year})



class ApprovedListFilter(admin.SimpleListFilter):
    title = _('approval')
    parameter_name = 'approved'

    def lookups(self, request, model_admin):
        return (
            ('yes', _('approved')),
            ('no', _('unapproved')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(approved__isnull=False)
        if self.value() == 'no':
            return queryset.filter(approved__isnull=True)



class CanceledListFilter(admin.SimpleListFilter):
    title = _('cancelation')
    parameter_name = 'canceled'

    def lookups(self, request, model_admin):
        return (
            (None, _('not canceled')),
            ('yes', _('canceled')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(canceled__isnull=False)
        else:
            return queryset.filter(canceled__isnull=True)

    def choices(self, cl):
        value = self.value()
        return [
            {
                'selected': value != 'yes',
                'query_string': cl.get_query_string({}, [self.parameter_name]),
                'display': _('active'),
            },
            {
                'selected': value == 'yes',
                'query_string': cl.get_query_string({self.parameter_name: 'yes'}),
                'display': _('canceled'),
            },
        ]



class SubjectTypeListFilter(admin.RelatedFieldListFilter):
    subject_type_type = None

    def __init__(self, field, request, params, model, model_admin, field_path):
        self.subject_types = SubjectType.objects.all()
        if self.subject_type_type:
            self.title = SubjectType.subject_type_type_labels[self.subject_type_type]
            self.subject_types = self.subject_types.filter(subject_type=self.subject_type_type)
        super(SubjectTypeListFilter, self).__init__(field, request, params, model, model_admin, field_path)
        if self.subject_type_type:
            self.title = SubjectType.subject_type_type_labels[self.subject_type_type]
        request.leprikon_subject_type_id = self.lookup_val

    def field_choices(self, field, request, model_admin):
        return [(t.id, t.plural) for t in self.subject_types.all()]


class CourseTypeListFilter(SubjectTypeListFilter):
    subject_type_type = SubjectType.COURSE


class EventTypeListFilter(SubjectTypeListFilter):
    subject_type_type = SubjectType.EVENT



class SubjectGroupListFilter(admin.RelatedFieldListFilter):
    subject_type_type = None

    def __init__(self, field, request, params, model, model_admin, field_path):
        if hasattr(request, 'leprikon_subject_type_id') and request.leprikon_subject_type_id:
            self.groups = SubjectGroup.objects.filter(subject_types__id=request.leprikon_subject_type_id)
        elif self.subject_type_type:
            self.groups = SubjectGroup.objects.filter(subject_types__subject_type=self.subject_type_type)
        else:
            self.groups = SubjectGroup.objects.all()
        super(SubjectGroupListFilter, self).__init__(field, request, params, model, model_admin, field_path)
        request.leprikon_subject_group_id = self.lookup_val

    def field_choices(self, field, request, model_admin):
        return [(g.id, g.plural) for g in self.groups.distinct()]


class CourseGroupListFilter(SubjectGroupListFilter):
    subject_type_type = SubjectType.COURSE


class EventGroupListFilter(SubjectGroupListFilter):
    subject_type_type = SubjectType.EVENT



class SubjectListFilter(admin.RelatedFieldListFilter):
    subject_type_type = None
    model = Subject

    def __init__(self, field, request, params, model, model_admin, field_path):
        self.subjects = self.model.objects.filter(school_year=request.school_year)
        if hasattr(request, 'leprikon_subject_type_id') and request.leprikon_subject_type_id:
            self.subjects = self.subjects.filter(subject_type__id=request.leprikon_subject_type_id)
        elif self.subject_type_type:
            self.subjects = self.subjects.filter(subject_type__subject_type=self.subject_type_type)
        if hasattr(request, 'leprikon_subject_group_id') and request.leprikon_subject_group_id:
            self.subjects = self.subjects.filter(subject_group__id=request.leprikon_subject_group_id)
        super(SubjectListFilter, self).__init__(field, request, params, model, model_admin, field_path)
        if self.subject_type_type:
            self.title = SubjectType.subject_type_labels[self.subject_type_type]

    def field_choices(self, field, request, model_admin):
        return [(s.id, s.name) for s in self.subjects]


class CourseListFilter(SubjectListFilter):
    subject_type_type = SubjectType.COURSE
    model = Course


class EventListFilter(SubjectListFilter):
    subject_type_type = SubjectType.EVENT
    model = Event



class LeaderListFilter(admin.RelatedFieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        self.leaders = Leader.objects.filter(school_years=request.school_year)
        super(LeaderListFilter, self).__init__(field, request, params, model, model_admin, field_path)

    def field_choices(self, field, request, model_admin):
        return [(leader.id, leader) for leader in self.leaders]
