# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.utils.translation import ugettext_lazy as _


PRICE_DECIMAL_PLACES  = 2
PRICE_MAX_DIGITS      = 10


LEPRIKON_CONTACT_TYPES = (
    ('email', _('email')),
    ('phone', _('phone')),
    ('url', _('url')),
)

LEPRIKON_CLUBLIST_TEMPLATES = (
    ('default', _('Default')),
    ('grouped', _('Grouped by club groups')),
)

LEPRIKON_EVENTLIST_TEMPLATES = (
    ('default', _('Default')),
    ('grouped', _('Grouped by event groups')),
)

LEPRIKON_COLOR_PAID      = '#0a0'
LEPRIKON_COLOR_NOTPAID   = '#e00'
LEPRIKON_COLOR_OVERPAID  = '#00a'

LEPRIKON_QUESTION_FIELDS = {
    'boolean': {
        'name': _('boolean field'),
        'class': 'django.forms.BooleanField',
    },
    'char': {
        'name': _('char field'),
        'class': 'django.forms.CharField',
    },
    'text': {
        'name': _('text field'),
        'class': 'leprikon.forms.fields.TextField',
    },
    'choice': {
        'name': _('choice field'),
        'class': 'django.forms.ChoiceField',
    },
    'date': {
        'name': _('date field'),
        'class': 'django.forms.DateField',
    },
}

LEPRIKON_PARAM_BACK = 'zpet'

LEPRIKON_URL_SUMMARY = 'prehled'
LEPRIKON_URL_CREATE_ACCOUNT = 'novy-uzivatel'
LEPRIKON_URL_CLUBS = 'krouzky'
LEPRIKON_URL_EVENTS = 'akce'
LEPRIKON_URL_LEADERS = 'vedouci'
LEPRIKON_URL_TIMESHEETS = 'vykazy'
LEPRIKON_URL_SUBMIT = 'odevzdat'
LEPRIKON_URL_ENTRY = 'zaznam'
LEPRIKON_URL_PARENT = 'zastupce'
LEPRIKON_URL_PARTICIPANT = 'ucastnik'
LEPRIKON_URL_PARTICIPANTS = 'ucastnici'
LEPRIKON_URL_USER = 'uzivatel'
LEPRIKON_URL_PASSWORD = 'heslo'
LEPRIKON_URL_PASSWORD_RESET = 'reset-hesla'
LEPRIKON_URL_LOGIN = 'prihlasit'
LEPRIKON_URL_LOGOUT = 'odhlasit'
LEPRIKON_URL_SCHOOL_YEAR = 'skolni-rok'
LEPRIKON_URL_SUPPORT = 'pomoc'
LEPRIKON_URL_EDIT = 'upravit'
LEPRIKON_URL_JOURNAL = 'denik'
LEPRIKON_URL_MINE = 'moje'
LEPRIKON_URL_ALTERNATING = 'zastup'
LEPRIKON_URL_REPORTS = 'reporty'
LEPRIKON_URL_PAYMENTS = 'platby'
LEPRIKON_URL_PAYMENTS_STATUS = 'stav-plateb'
LEPRIKON_URL_ADD = 'pridat'
LEPRIKON_URL_DELETE = 'smazat'
LEPRIKON_URL_CANCEL = 'zrusit'
LEPRIKON_URL_REGISTRATION = 'prihlaska'
LEPRIKON_URL_REGISTRATIONS = 'prihlasky'

LEPRIKON_MENU_ADD_LOGOUT = True

