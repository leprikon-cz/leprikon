from __future__ import unicode_literals

from django.contrib import admin

from ..models.clubs import Club
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



class ClubTypeListFilter(admin.RelatedFieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        super(ClubTypeListFilter, self).__init__(field, request, params, model, model_admin, field_path)
        request.club_type_id = self.lookup_val



class ClubListFilter(admin.RelatedFieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        self.clubs = Club.objects.filter(school_year=request.school_year)
        if hasattr(request, 'club_type_id') and request.club_type_id:
            self.clubs = self.clubs.filter(club_type__id=request.club_type_id)
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

