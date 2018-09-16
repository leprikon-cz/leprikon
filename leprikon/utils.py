import locale
import os
import string
import unicodedata
import zlib
from datetime import date
from urllib.parse import urlencode

from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse_lazy as reverse
from django.db import IntegrityError, transaction
from django.utils.encoding import iri_to_uri, smart_text
from django.utils.translation import ugettext_lazy as _

from .conf import settings


def _get_localeconv():
    """
    This function loads localeconv during module load.
    It is necessary, because using locale.setlocale later may be dangerous
    (It is not thread-safe in most of the implementations.)
    """
    original_locale_name = locale.setlocale(locale.LC_ALL)
    locale_name = locale.locale_alias[settings.LANGUAGE_CODE].split('.')[0] + '.UTF-8'
    locale.setlocale(locale.LC_ALL, str(locale_name))
    lc = locale.localeconv()
    locale.setlocale(locale.LC_ALL, original_locale_name)
    return lc


localeconv = _get_localeconv()


# This function is inspired by python's standard locale.currency().
def currency(val, international=False):
    """Formats val according to the currency settings for current language."""
    digits = settings.PRICE_DECIMAL_PLACES

    # grouping
    groups = []
    s = str(abs(int(val)))
    for interval in locale._grouping_intervals(localeconv['mon_grouping']):
        if not s:
            break
        groups.append(s[-interval:])
        s = s[:-interval]
    if s:
        groups.append(s)
    groups.reverse()
    s = smart_text(localeconv['mon_thousands_sep']).join(groups)

    # display fraction for non integer values
    if digits and not isinstance(val, int):
        s += smart_text(localeconv['mon_decimal_point']) + '{{:.{}f}}'.format(digits).format(val).split('.')[1]

    # '<' and '>' are markers if the sign must be inserted between symbol and value
    s = '<' + s + '>'

    smb = smart_text(localeconv[international and 'int_curr_symbol' or 'currency_symbol'])
    precedes = localeconv[val < 0 and 'n_cs_precedes' or 'p_cs_precedes']
    separated = localeconv[val < 0 and 'n_sep_by_space' or 'p_sep_by_space']

    if precedes:
        s = smb + (separated and ' ' or '') + s
    else:
        s = s + (separated and ' ' or '') + smb

    sign_pos = localeconv[val < 0 and 'n_sign_posn' or 'p_sign_posn']
    sign = localeconv[val < 0 and 'negative_sign' or 'positive_sign']

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


def amount_color(amount):
    if amount > 0:
        return settings.LEPRIKON_COLOR_POSITIVE
    elif amount < 0:
        return settings.LEPRIKON_COLOR_NEGATIVE
    else:
        return settings.LEPRIKON_COLOR_ZERO


def comma_separated(lst):
    lst = list(map(smart_text, lst))
    if len(lst) > 2:
        return _(', and ').join([', '.join(lst[:-1]), lst[-1]])
    else:
        return _(', and ').join(lst)


def get_rand_hash(length=32, stringset=string.ascii_letters + string.digits):
    return ''.join([stringset[i % len(stringset)] for i in [ord(x) for x in os.urandom(length)]])


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
    birth_num = birth_num.replace('/', '')
    y = int(birth_num[:2])
    if len(birth_num) == 9:
        # before 1954
        if y < 54:
            year = 1900 + y
        else:
            year = 1800 + y
    else:
        year = int(date.today().year / 100) * 100 + y
        if y > date.today().year % 100:
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


def first_upper(s):
    return s[0].upper() + s[1:] if s else ''


def merge_objects(source, target, attributes=None, exclude=[]):
    attributes = attributes or [f.name for f in source._meta.fields if f.name not in exclude]
    for attr in attributes:
        if not getattr(target, attr):
            setattr(target, attr, getattr(source, attr))
    return target


@transaction.atomic
def merge_users(source, target):
    target = merge_objects(source, target, ('first_name', 'last_name', 'email'))
    target.date_joined = min(source.date_joined, target.date_joined)
    target.last_login = max(source.last_login, target.last_login)

    try:
        leader = source.leprikon_leader
        leader.user = target
        leader.save()
    except ObjectDoesNotExist:
        pass
    except IntegrityError:
        # both users are leaders
        raise

    source.leprikon_registrations.update(user=target)

    for sp in source.leprikon_participants.all():
        tp = target.leprikon_participants.filter(birth_num=sp.birth_num).first()
        if tp:
            tp = merge_objects(sp, tp, exclude=('id', 'user', 'birth_num'))
            tp.save()
        else:
            sp.user = target
            sp.save()

    for sp in source.leprikon_parents.all():
        tp = target.leprikon_parents.filter(first_name=sp.first_name, last_name=sp.last_name).first()
        if tp:
            tp = merge_objects(sp, tp, exclude=('id', 'user'))
            tp.save()
        else:
            sp.user = target
            sp.save()

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


def spayd(*items):
    s = 'SPD*1.0*' + '*'.join(
        '%s:%s' % (k, unicodedata.normalize('NFKD', str(v).replace('*', '')).encode('ascii', 'ignore').upper().decode())
        for k, v in sorted(items)
    )
    s += '*CRC32:%x' % zlib.crc32(s.encode())
    return s.upper()
