from __future__ import unicode_literals

from django.contrib import admin

from ..models.courses import Course
from ..models.events import Event
from ..models.roles import Leader
from ..models.schoolyear import SchoolYear


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



class CourseTypeListFilter(admin.RelatedFieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        super(CourseTypeListFilter, self).__init__(field, request, params, model, model_admin, field_path)
        request.course_type_id = self.lookup_val



class CourseListFilter(admin.RelatedFieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        self.courses = Course.objects.filter(school_year=request.school_year)
        if hasattr(request, 'course_type_id') and request.course_type_id:
            self.courses = self.courses.filter(course_type__id=request.course_type_id)
        super(CourseListFilter, self).__init__(field, request, params, model, model_admin, field_path)

    def field_choices(self, field, request, model_admin):
        return [(course.id, course.name) for course in self.courses]



class EventTypeListFilter(admin.RelatedFieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        super(EventTypeListFilter, self).__init__(field, request, params, model, model_admin, field_path)
        request.event_type_id = self.lookup_val



class EventListFilter(admin.RelatedFieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        self.events = Event.objects.filter(school_year=request.school_year)
        if hasattr(request, 'event_type_id') and request.event_type_id:
            self.events = self.events.filter(event_type__id=request.event_type_id)
        super(EventListFilter, self).__init__(field, request, params, model, model_admin, field_path)

    def field_choices(self, field, request, model_admin):
        return [(event.id, event.name) for event in self.events]



class LeaderListFilter(admin.RelatedFieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        self.leaders = Leader.objects.filter(school_years=request.school_year)
        super(LeaderListFilter, self).__init__(field, request, params, model, model_admin, field_path)

    def field_choices(self, field, request, model_admin):
        return [(leader.id, leader) for leader in self.leaders]

