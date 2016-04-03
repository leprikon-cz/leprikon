from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.conf import settings
from django.conf.urls import include, url
from django.views.generic.base import RedirectView

from . import views
from .conf import settings


# dictionary of all LEPRIKON_URL_* attributes of settings
LEPRIKON_URL = dict(
    (attr.lower()[len('LEPRIKON_URL_'):], getattr(settings, attr))
    for attr in dir(settings) if attr.startswith('LEPRIKON_URL_')
)

def d_url(pattern, name):
    return url(pattern.format(**LEPRIKON_URL), getattr(views, name), name=name)

urlpatterns = [
    url(r'^$', RedirectView.as_view(url='{summary}/'.format(**LEPRIKON_URL), permanent=True), name='index'),
    d_url(r'^{summary}/$',                                          'summary'),

    d_url(r'^{create_account}/$',                                   'user_create'),
    d_url(r'^{user}/$',                                             'user_update'),
    d_url(r'^{user}/{password}/$',                                  'user_password'),

    d_url(r'^{registrations}/$',                                    'registrations'),

    d_url(r'^{participants}/$',                                     'participant_list'),
    d_url(r'^{participants}/{add}/$',                               'participant_create'),
    d_url(r'^{participants}/(?P<pk>[0-9]+)/$',                      'participant_update'),
    d_url(r'^{parent}/$',                                           'parent_create'),
    d_url(r'^{parent}/(?P<pk>[0-9]+)/$',                            'parent_update'),

    d_url(r'^{clubs}/$',                                            'club_list'),
    d_url(r'^{clubs}/{mine}/$',                                     'club_list_mine'),
    d_url(r'^{clubs}/{alternating}/$',                              'club_alternating'),
    d_url(r'^{clubs}/(?P<pk>[0-9]+)/$',                             'club_detail'),
    d_url(r'^{clubs}/(?P<pk>[0-9]+)/{participants}/$',              'club_participants'),
    d_url(r'^{clubs}/(?P<pk>[0-9]+)/{journal}/$',                   'club_journal'),
    d_url(r'^{clubs}/(?P<pk>[0-9]+)/{edit}/$',                      'club_update'),
    d_url(r'^{clubs}/(?P<club>[0-9]+)/{registration}/$',            'club_registration_public'),
    d_url(r'^{clubs}/(?P<club>[0-9]+)/(?P<participant>[0-9]+)/$',   'club_registration_form'),
    d_url(r'^{clubs}/{registration}/(?P<slug>[^.]+).pdf$',          'club_registration_pdf'),
    d_url(r'^{clubs}/{registration}/(?P<pk>[0-9]+)/{cancel}/$',     'club_registration_cancel'),
    d_url(r'^{clubs}/{journal}/{entry}/{add}/(?P<club>[0-9]+)/$',   'clubjournalentry_create'),
    d_url(r'^{clubs}/{journal}/{entry}/(?P<pk>[0-9]+)/$',           'clubjournalentry_update'),
    d_url(r'^{clubs}/{journal}/{entry}/(?P<pk>[0-9]+)/{delete}/$',  'clubjournalentry_delete'),
    d_url(r'^{timesheets}/{journal}/{entry}/(?P<pk>[0-9]+)/$',           'clubjournalleaderentry_update'),
    d_url(r'^{timesheets}/{journal}/{entry}/(?P<pk>[0-9]+)/{delete}/$',  'clubjournalleaderentry_delete'),

    url(  r'^{events}/$'.format(**LEPRIKON_URL), RedirectView.as_view(url='../', permanent=True)),
    d_url(r'^{events}/{mine}/$',                                    'event_list_mine'),
    d_url(r'^{events}/(?P<pk>[0-9]+)/$',                            'event_detail'),
    d_url(r'^{events}/(?P<event_type>[^/]+)/$',                     'event_list'),
    d_url(r'^{events}/(?P<pk>[0-9]+)/{participants}/$',             'event_participants'),
    d_url(r'^{events}/(?P<pk>[0-9]+)/{edit}/$',                     'event_update'),
    d_url(r'^{events}/(?P<event>[0-9]+)/{registration}/$',          'event_registration_public'),
    d_url(r'^{events}/(?P<event>[0-9]+)/(?P<participant>[0-9]+)/$', 'event_registration_form'),
    d_url(r'^{events}/{registration}/(?P<slug>[^.]+).pdf$',         'event_registration_pdf'),
    d_url(r'^{events}/{registration}/(?P<pk>[0-9]+)/{cancel}/$',    'event_registration_cancel'),

    d_url(r'^{leaders}/$',                                          'leader_list'),

    d_url(r'^{timesheets}/$',                                       'timesheet_list'),
    d_url(r'^{timesheets}/(?P<pk>[0-9]+)/$',                        'timesheet_detail'),
    d_url(r'^{timesheets}/(?P<pk>[0-9]+)/{submit}/$',               'timesheet_submit'),
    d_url(r'^{timesheets}/(?P<pk>[0-9]+)/{add}/$',                  'timesheetentry_create'),
    d_url(r'^{timesheets}/{entry}/(?P<pk>[0-9]+)/$',                'timesheetentry_update'),
    d_url(r'^{timesheets}/{entry}/(?P<pk>[0-9]+)/{delete}/$',       'timesheetentry_delete'),

    d_url(r'^{login}/$',                                            'user_login'),
    d_url(r'^{logout}/$',                                           'user_logout'),
    d_url(r'^{password_reset}/$',                                   'password_reset'),
    d_url(r'^{password_reset}/done/$',                              'password_reset_done'),
    d_url(r'^{password_reset}/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{{1,13}}-[0-9A-Za-z]{{1,20}})/$',
                                                                    'password_reset_confirm'),
    d_url(r'^{password_reset}/complete/$',                          'password_reset_complete'),

    d_url(r'^{school_year}/$',                                      'school_year'),
    d_url(r'^{support}/$',                                          'support'),

    d_url(r'^{reports}/$',                                          'reports'),
    d_url(r'^{reports}/{clubs}/{payments}/$',                       'report_club_payments'),
    d_url(r'^{reports}/{clubs}/{payments_status}/$',                'report_club_payments_status'),
    d_url(r'^{reports}/{events}/{payments}/$',                      'report_event_payments'),
    d_url(r'^{reports}/{events}/{payments_status}/$',               'report_event_payments_status'),
]

