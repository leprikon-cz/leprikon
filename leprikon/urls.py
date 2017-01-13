from __future__ import unicode_literals

from django.conf.urls import include, url
from django.views.generic.base import RedirectView

from . import views
from .api import urls as api_urls
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

    d_url(r'^{registrations}/$',                                    'registration_list'),

    d_url(r'^{participants}/$',                                     'participant_list'),
    d_url(r'^{participants}/{add}/$',                               'participant_create'),
    d_url(r'^{participants}/(?P<pk>[0-9]+)/$',                      'participant_update'),
    d_url(r'^{parent}/$',                                           'parent_create'),
    d_url(r'^{parent}/(?P<pk>[0-9]+)/$',                            'parent_update'),

    url(  r'^{courses}/$'.format(**LEPRIKON_URL), RedirectView.as_view(url='../', permanent=True)),
    d_url(r'^{courses}/{mine}/$',                                               'course_list_mine'),
    d_url(r'^{courses}/{alternating}/$',                                        'course_alternating'),
    d_url(r'^{courses}/(?P<course_type>[^/]+)/$',                               'course_list'),
    d_url(r'^{courses}/(?P<course_type>[^/]+)/(?P<pk>[0-9]+)/$',                'course_detail'),
    d_url(r'^{courses}/(?P<course_type>[^/]+)/(?P<pk>[0-9]+)/{registrations}/$','course_registrations'),
    d_url(r'^{courses}/(?P<course_type>[^/]+)/(?P<pk>[0-9]+)/{journal}/$',      'course_journal'),
    d_url(r'^{courses}/(?P<course_type>[^/]+)/(?P<pk>[0-9]+)/{edit}/$',         'course_update'),
    d_url(r'^{courses}/(?P<course_type>[^/]+)/(?P<pk>[0-9]+)/{registration}/$', 'course_registration_form'),
    d_url(r'^{courses}/{registration}/(?P<slug>[^.]+).pdf$',                    'course_registration_pdf'),
    d_url(r'^{courses}/{registration}/(?P<pk>[0-9]+)/{cancel}/$',               'course_registration_cancel'),
    d_url(r'^{courses}/{journal}/{entry}/{add}/(?P<course>[0-9]+)/$',           'coursejournalentry_create'),
    d_url(r'^{courses}/{journal}/{entry}/(?P<pk>[0-9]+)/$',                     'coursejournalentry_update'),
    d_url(r'^{courses}/{journal}/{entry}/(?P<pk>[0-9]+)/{delete}/$',            'coursejournalentry_delete'),
    d_url(r'^{timesheets}/{journal}/{entry}/(?P<pk>[0-9]+)/$',                  'coursejournalleaderentry_update'),
    d_url(r'^{timesheets}/{journal}/{entry}/(?P<pk>[0-9]+)/{delete}/$',         'coursejournalleaderentry_delete'),

    url(  r'^{events}/$'.format(**LEPRIKON_URL), RedirectView.as_view(url='../', permanent=True)),
    d_url(r'^{events}/{mine}/$',                                                'event_list_mine'),
    d_url(r'^{events}/(?P<event_type>[^/]+)/$',                                 'event_list'),
    d_url(r'^{events}/(?P<event_type>[^/]+)/(?P<pk>[0-9]+)/$',                  'event_detail'),
    d_url(r'^{events}/(?P<event_type>[^/]+)/(?P<pk>[0-9]+)/{registrations}/$',  'event_registrations'),
    d_url(r'^{events}/(?P<event_type>[^/]+)/(?P<pk>[0-9]+)/{edit}/$',           'event_update'),
    d_url(r'^{events}/(?P<event_type>[^/]+)/(?P<pk>[0-9]+)/{registration}/$',   'event_registration_form'),
    d_url(r'^{events}/{registration}/(?P<slug>[^.]+).pdf$',                     'event_registration_pdf'),
    d_url(r'^{events}/{registration}/(?P<pk>[0-9]+)/{cancel}/$',                'event_registration_cancel'),

    d_url(r'^{leaders}/$',                                          'leader_list'),

    d_url(r'^{messages}/$',                                         'message_list'),
    d_url(r'^{messages}/(?P<slug>[^.]+)/$',                         'message_detail'),

    d_url(r'^{timesheets}/$',                                       'timesheet_list'),
    d_url(r'^{timesheets}/(?P<pk>[0-9]+)/$',                        'timesheet_detail'),
    d_url(r'^{timesheets}/(?P<pk>[0-9]+)/{submit}/$',               'timesheet_submit'),
    d_url(r'^{timesheets}/{entry}/{add}/$',                         'timesheetentry_create'),
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

    d_url(r'^{reports}/$',                                          'report_list'),
    d_url(r'^{reports}/{courses}/{payments}/$',                     'report_course_payments'),
    d_url(r'^{reports}/{courses}/{payments_status}/$',              'report_course_payments_status'),
    d_url(r'^{reports}/{courses}/{stats}/$',                        'report_course_stats'),
    d_url(r'^{reports}/{events}/{payments}/$',                      'report_event_payments'),
    d_url(r'^{reports}/{events}/{payments_status}/$',               'report_event_payments_status'),
    d_url(r'^{reports}/{debtors}/$',                                'report_debtors'),

    d_url(r'^{terms_conditions}/$',                                 'terms_conditions'),

    url(r'^api/', include(api_urls, 'api')),
]

