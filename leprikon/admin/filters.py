from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.contrib import admin
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _

from ..models import SchoolYear, Club, Event, Leader


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



class ClubListFilter(admin.RelatedFieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        self.clubs = Club.objects.filter(school_year=request.school_year)
        super(ClubListFilter, self).__init__(field, request, params, model, model_admin, field_path)

    def field_choices(self, field, request, model_admin):
        return [(club.id, club.name) for club in self.clubs]



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


