from __future__ import unicode_literals

from .models.roles import Leader
from .models.schoolyear import SchoolYear


class school_year(object):
    def __get__(self, request, type=None):
        if request is None:
            return self
        try:
            return request._leprikon_school_year
        except AttributeError:
            years = SchoolYear.objects
            if not request.user.is_staff:
                years = years.filter(active=True)
            try:
                # return year stored in the session
                request._leprikon_school_year = years.get(id=request.session['school_year_id'])
            except (KeyError, SchoolYear.DoesNotExist):
                request._leprikon_school_year = SchoolYear.objects.get_current()
        return request._leprikon_school_year

    def __set__(self, request, school_year):
        if request:
            request._leprikon_school_year = school_year
            request.session['school_year_id'] = school_year.id

    def __delete__(self, request):
        if request:
            del(request._leprikon_school_year)



class leader(object):
    def __get__(self, request, type=None):
        if request is None:
            return self
        try:
            return request._leprikon_leader
        except AttributeError:
            try:
                request._leprikon_leader = request.user.leprikon_leader
            except (AttributeError, Leader.DoesNotExist):
                request._leprikon_leader = None
        return request._leprikon_leader

    def __set__(self, request, leader):
        pass

    def __delete__(self, request):
        if request:
            del(request._leprikon_leader)



class LeprikonMiddleware(object):

    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        type(request).school_year = school_year()
        type(request).leader = leader()
        return self.get_response(request)

    # django<1.10 method
    def process_request(self, request):
        type(request).school_year = school_year()
        type(request).leader = leader()
