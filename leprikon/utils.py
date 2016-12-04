from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

import locale
import os
import string
from datetime import date
from django.core.urlresolvers import reverse_lazy as reverse
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils.encoding import iri_to_uri, smart_text
from django.utils.translation import get_language, ugettext_lazy as _
from urllib import urlencode

from .conf import settings


class LocaleConv:
    def __init__(self, languages):
        """
        This function loads localeconv for all languages during module load.
        It is necessary, because using locale.setlocale later may be dangerous
        (It is not thread-safe in most of the implementations.)
        """
        original_locale_name = locale.setlocale(locale.LC_ALL)
        self.localeconv = {}
        for code, name in languages:
            locale_name = locale.locale_alias[code].split('.')[0]+'.UTF-8'
            locale.setlocale(locale.LC_ALL, str(locale_name))
            self.localeconv[code] = locale.localeconv()
        locale.setlocale(locale.LC_ALL, original_locale_name)

    def __call__(self, language=None):
        return self.localeconv[language or get_language()]


localeconv = LocaleConv(settings.LANGUAGES)



# This function is inspired by python's standard locale.currency().

def currency(val, international=False):
    """Formats val according to the currency settings for current language."""
    conv = localeconv()

    digits = settings.PRICE_DECIMAL_PLACES

    # grouping
    groups = []
    s = str(abs(int(val)))
    for interval in locale._grouping_intervals(conv['mon_grouping']):
        if not s:
            break
        groups.append(s[-interval:])
        s = s[:-interval]
    if s:
        groups.append(s)
    groups.reverse()
    s = smart_text(conv['mon_thousands_sep']).join(groups)

    # display fraction for non integer values
    if digits and not isinstance(val, int):
        s += smart_text(conv['mon_decimal_point']) + '{{:.{}f}}'.format(digits).format(val).split('.')[1]

    # '<' and '>' are markers if the sign must be inserted between symbol and value
    s = '<' + s + '>'

    smb = smart_text(conv[international and 'int_curr_symbol' or 'currency_symbol'])
    precedes = conv[val<0 and 'n_cs_precedes' or 'p_cs_precedes']
    separated = conv[val<0 and 'n_sep_by_space' or 'p_sep_by_space']

    if precedes:
        s = smb + (separated and ' ' or '') + s
    else:
        s = s + (separated and ' ' or '') + smb

    sign_pos = conv[val<0 and 'n_sign_posn' or 'p_sign_posn']
    sign = conv[val<0 and 'negative_sign' or 'positive_sign']

    if sign_pos == 0:
        s = '(' + s + ')'
    elif sign_pos == 1:
        s = sign + s
    elif sign_pos == 2:
        s = s + sign
    elif sign_pos == 3:
        s = s.replace('<', sign)
    elif sign_pos == 4:
        s = s.replace('>', sign)
    else:
        # the default if nothing specified;
        # this should be the most fitting sign position
        s = sign + s

    return s.replace('<', '').replace('>', '').replace(' ', '\u00A0')


def comma_separated(l):
    l = map(smart_text, l)
    if len(l) > 2:
        return _(', and ').join([', '.join(l[:-1]), l[-1]])
    else:
        return _(', and ').join(l)


def get_rand_hash(length=32, stringset=string.ascii_letters+string.digits):
    return ''.join([stringset[i%len(stringset)] for i in [ord(x) for x in os.urandom(length)]])


def current_url(request):
    if request.META['QUERY_STRING']:
        return '{}?{}'.format(request.path, request.META['QUERY_STRING'])
    else:
        return request.path

def url_back(request):
    return request.POST.get(
        settings.LEPRIKON_PARAM_BACK,
        request.GET.get(
            settings.LEPRIKON_PARAM_BACK,
            reverse('leprikon:summary'),
        ),
    )

def url_with_back(url, url_back):
    return '{}?{}'.format(url, urlencode({settings.LEPRIKON_PARAM_BACK: iri_to_uri(url_back)}))

def reverse_with_back(request, *args, **kwargs):
    return url_with_back(reverse(*args, **kwargs), current_url(request))



def get_birth_date(birth_num):
    birth_num = birth_num.replace('/','')
    y = int(birth_num[:2])
    if len(birth_num) == 9:
        # before 1954
        if y < 54:
            year = 1900+y
        else:
            year = 1800+y
    else:
        year = int(date.today().year/100)*100 + y
        if y > date.today().year%100:
            year -= 100
    month = int(birth_num[2:4]) % 50 % 20
    day = int(birth_num[4:6])
    return date(year, month, day)

def get_age(birth_date, today=None):
    today = today or date.today()
    if date(today.year, birth_date.month, birth_date.day) > today:
        return today.year - birth_date.year - 1
    else:
        return today.year - birth_date.year



@transaction.atomic
def merge_users(source, target):
    if not target.first_name and source.first_name:
        target.first_name = source.first_name
    if not target.last_name and source.last_name:
        target.last_name = source.last_name
    if not target.email and source.email:
        target.email = source.email
    target.date_joined = min(source.date_joined, target.date_joined)

    try:
        leader = source.leprikon_leader
        leader.user = target
        leader.save()
    except ObjectDoesNotExist:
        pass
    except IntegrityError:
        # both users are leaders
        raise

    source.leprikon_clubregistrations.update(user=target)
    source.leprikon_eventregistrations.update(user=target)

    for p in source.leprikon_participants.all():
        if not target.leprikon_participants.filter(birth_num=p.birth_num).exists():
            p.user = target
            p.save()

    for p in source.leprikon_parents.all():
        if not target.leprikon_parents.filter(first_name=p.first_name, last_name=p.last_name).exists():
            p.user = target
            p.save()

    for mr in source.leprikon_messages.all():
        if not target.leprikon_messages.filter(message=mr.message).exists():
            mr.recipient = target
            mr.save()

    try:
        # support social auth
        source.social_auth.update(user=target)
    except AttributeError:
        pass

    source.delete()

