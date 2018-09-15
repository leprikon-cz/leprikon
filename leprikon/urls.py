from django.conf.urls import include, url
from django.db import transaction
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
    return url(pattern.format(**LEPRIKON_URL), transaction.atomic(getattr(views, name)), name=name)


app_name = 'leprikon'

urlpatterns = [
    url(r'^$', RedirectView.as_view(url='{summary}/'.format(**LEPRIKON_URL), permanent=True), name='index'),
    d_url(r'^{summary}/$',          'summary'),

    d_url(r'^{create_account}/$',           'user_create'),
    d_url(r'^{user}/{agreement}/$',         'user_agreement'),
    d_url(r'^{user}/{email}/$',             'user_email'),
    d_url(r'^{user}/$',                     'user_update'),
    d_url(r'^{user}/{password}/$',          'user_password'),
    d_url(r'^{login}/$',                    'user_login'),
    d_url(r'^{logout}/$',                   'user_logout'),
    d_url(r'^{password_reset}/$',           'password_reset'),
    d_url(r'^{password_reset}/done/$',      'password_reset_done'),
    d_url(r'^{password_reset}/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{{1,13}}-[0-9A-Za-z]{{1,20}})/$',
          'password_reset_confirm'),
    d_url(r'^{password_reset}/complete/$',  'password_reset_complete'),

    d_url(r'^{leader}/$',                                                           'leader_summary'),
    d_url(r'^{leader}/{journal}/(?P<pk>[0-9]+)/$',                                  'course_journal'),
    d_url(r'^{leader}/{journal}/{journalentry}/{add}/(?P<course>[0-9]+)/$',         'coursejournalentry_create'),
    d_url(r'^{leader}/{journal}/{journalentry}/(?P<pk>[0-9]+)/$',                   'coursejournalentry_update'),
    d_url(r'^{leader}/{journal}/{journalentry}/(?P<pk>[0-9]+)/{delete}/$',          'coursejournalentry_delete'),
    d_url(r'^{leader}/{journal}/{alternating}/$',                                   'course_alternating'),
    d_url(r'^{leader}/{timesheets}/$',                                              'timesheet_list'),
    d_url(r'^{leader}/{timesheets}/(?P<pk>[0-9]+)/$',                               'timesheet_detail'),
    d_url(r'^{leader}/{timesheets}/(?P<pk>[0-9]+)/{submit}/$',                      'timesheet_submit'),
    d_url(r'^{leader}/{timesheets}/{entry}/{add}/$',                                'timesheetentry_create'),
    d_url(r'^{leader}/{timesheets}/{entry}/(?P<pk>[0-9]+)/$',                       'timesheetentry_update'),
    d_url(r'^{leader}/{timesheets}/{entry}/(?P<pk>[0-9]+)/{delete}/$',              'timesheetentry_delete'),
    d_url(r'^{leader}/{timesheets}/{journalentry}/(?P<pk>[0-9]+)/$',                'coursejournalleaderentry_update'),
    d_url(r'^{leader}/{timesheets}/{journalentry}/(?P<pk>[0-9]+)/{delete}/$',       'coursejournalleaderentry_delete'),
    d_url(r'^{leader}/(?P<subject_type>[^/]+)/$',                                   'subject_list_mine'),
    d_url(r'^{leader}/(?P<subject_type>[^/]+)/(?P<pk>[0-9]+)/{edit}/$',             'subject_update'),
    d_url(r'^{leader}/(?P<subject_type>[^/]+)/(?P<pk>[0-9]+)/{registrations}/$',    'subject_registrations'),

    d_url(r'^{registrations}/$',                                    'registration_list'),
    d_url(r'^{registrations}/(?P<pk>[^/]+)/(?P<slug>[^.]+).pdf$',   'registration_pdf'),
    d_url(r'^{registrations}/(?P<pk>[^/]+)/{cancel}/$',             'registration_cancel'),

    d_url(r'^{payments}/$',                                         'payment_list'),
    d_url(r'^{payments}/(?P<pk>[^/]+)/(?P<slug>[^.]+).pdf$',        'payment_pdf'),

    d_url(r'^{participants}/$',                             'participant_list'),
    d_url(r'^{participants}/{add}/$',                       'participant_create'),
    d_url(r'^{participants}/(?P<pk>[0-9]+)/$',              'participant_update'),
    d_url(r'^{participants}/{parent}/{add}/$',              'parent_create'),
    d_url(r'^{participants}/{parent}/(?P<pk>[0-9]+)/$',     'parent_update'),

    d_url(r'^{messages}/$',                                 'message_list'),
    d_url(r'^{messages}/(?P<slug>[^.]+)/$',                 'message_detail'),

    d_url(r'^{leaders}/$',                                  'leader_list'),
    # d_url(r'^{leaders}/(?P<slug>[^.]+)/$',                  'leader_detail'),

    d_url(r'^{school_year}/$',                              'school_year'),

    d_url(r'^{reports}/$',                                  'report_list'),
    d_url(r'^{reports}/{courses}/{payments}/$',             'report_course_payments'),
    d_url(r'^{reports}/{courses}/{payments_status}/$',      'report_course_payments_status'),
    d_url(r'^{reports}/{courses}/{stats}/$',                'report_course_stats'),
    d_url(r'^{reports}/{events}/{payments}/$',              'report_event_payments'),
    d_url(r'^{reports}/{events}/{payments_status}/$',       'report_event_payments_status'),
    d_url(r'^{reports}/{events}/{stats}/$',                 'report_event_stats'),
    d_url(r'^{reports}/{debtors}/$',                        'report_debtors'),

    d_url(r'^{terms_conditions}/$',                         'terms_conditions'),

    url(r'^api/', include(api_urls, 'api')),

    d_url(r'^(?P<subject_type>[^/]+)/$',                                 'subject_list'),
    d_url(r'^(?P<subject_type>[^/]+)/(?P<pk>[0-9]+)/$',                  'subject_detail'),
    d_url(r'^(?P<subject_type>[^/]+)/(?P<pk>[0-9]+)/{registration}/$',   'subject_registration_form'),
]
