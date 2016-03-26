from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

import datetime
import warnings

from .models import Leader, SchoolYear


class school_year(object):
    def __get__(self, request, type=None):
        if request is None:
            return self
        try:
            return request._leprikon_school_year
        except AttributeError:
            try:
                # return year stored in the session
                school_year = SchoolYear.objects.get(id=request.session['school_year_id'])
            except (KeyError, SchoolYear.DoesNotExist):
                try:
                    # return last active year
                    school_year = SchoolYear.objects.filter(active=True).order_by('-year')[0]
                except IndexError:
                    # Create or activate current year
                    if datetime.date.today().month < 7:
                        year = datetime.date.today().year - 1
                    else:
                        year = datetime.date.today().year
                    school_year = SchoolYear.objects.get_or_create(year=year)[0]
                    school_year.active = True
                    school_year.save()
            request._leprikon_school_year = school_year
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



class SchoolYearMiddleware(object):

    def process_request(self, request):
        warnings.warn("Using SchoolYearMiddleware is deprecated. Use LeprikonMiddleware instead.")
        type(request).school_year = school_year()
        type(request).leader = leader()



class LeprikonMiddleware(object):

    def process_request(self, request):
        type(request).school_year = school_year()
        type(request).leader = leader()


