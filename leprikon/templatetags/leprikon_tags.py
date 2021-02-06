import re
from traceback import print_exc

import requests
from django import template
from django.contrib.admin.templatetags.admin_list import result_list as _result_list
from django.contrib.staticfiles import finders
from django.core.cache import InvalidCacheBackendError, caches
from django.core.paginator import Paginator
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from lxml.html import fromstring, tostring

from ..conf import settings
from ..forms.schoolyear import SchoolYearForm
from ..utils import (
    comma_separated as _comma_separated,
    currency as _currency,
    current_url as _current_url,
    first_upper as _first_upper,
    url_back as _url_back,
    url_with_back as _url_with_back,
)

register = template.Library()


@register.filter
def currency(value):
    try:
        return _currency(value)
    except (ValueError, TypeError):
        return ""


@register.filter
def comma_separated(value):
    return _comma_separated(value)


@register.inclusion_tag("leprikon/admin/dashboard.html", takes_context=True)
def dashboard(context):
    from ..models.subjects import SubjectType

    context = context.__copy__()
    context["subject_types"] = SubjectType.objects.all()
    return context


@register.filter
def first_upper(value):
    return _first_upper(value)


@register.filter
def filter_current_school_year(value, school_year):
    return value.filter(school_year=school_year)


@register.filter
def lines(value):
    try:
        return value.strip().split("\n")
    except Exception:
        return []


@register.filter
def jsdate(d):
    try:
        return f"new Date({d.year},{d.month-1},{d.day})"
    except AttributeError:
        return "undefined"


@register.filter
def paginator(items, per_page=1):
    paginator = Paginator(items, per_page)
    return [paginator.page(page) for page in paginator.page_range]


@register.simple_tag
def param_back():
    return settings.LEPRIKON_PARAM_BACK


@register.simple_tag(takes_context=True)
def url_back(context):
    return _url_back(context["request"])


@register.simple_tag(takes_context=True)
def current_url(context):
    return _current_url(context["request"])


@register.inclusion_tag("leprikon/registration_links.html", takes_context=True)
def registration_links(context, subject):
    now = timezone.now()
    context = context.__copy__()
    context["subject"] = subject
    if context["request"].user.is_authenticated():
        context["registrations"] = subject.registrations.filter(user=context["request"].user, canceled=None)
    else:
        context["registrations"] = []

    try:
        registration_link = context["view"].registration_link
    except (AttributeError, KeyError):
        registration_link = None

    if registration_link:
        source = registration_link
        context["registration_url"] = _url_with_back(
            reverse("leprikon:registration_link_form", args=(registration_link.slug, subject.id)),
            current_url(context),
        )
    else:
        source = subject
        context["registration_url"] = _url_with_back(subject.get_registration_url(), current_url(context))

    context["registration_allowed"] = source.registration_allowed

    if context["registration_allowed"]:
        context["registration_message"] = ""
    else:
        context["registration_message"] = _("Registering is currently not allowed.")

    if subject.price and source.reg_to:
        context["registration_ended_message"] = _("Registering ended on {}").format(
            date_format(timezone.localtime(source.reg_to), "DATETIME_FORMAT")
        )
        if source.reg_to > now:
            context["registration_end_in"] = (source.reg_to - now).seconds
            context["registration_ends_message"] = _("Registering will end on {}.").format(
                date_format(timezone.localtime(source.reg_to), "DATETIME_FORMAT")
            )
            context["registration_message"] = context["registration_ends_message"]
        else:
            context["registration_message"] = context["registration_ended_message"]
    if subject.price and source.reg_from and source.reg_from > now:
        context["registration_start_in"] = (source.reg_from - now).seconds
        context["registration_starts_message"] = _("Registering will start on {}.").format(
            date_format(timezone.localtime(source.reg_from), "DATETIME_FORMAT")
        )
        context["registration_message"] = context["registration_starts_message"]
    return context


@register.inclusion_tag("leprikon/schoolyear_form.html", takes_context=True)
def school_year_form(context):
    context = context.__copy__()
    context["school_year_form"] = SchoolYearForm(context.get("request"))
    return context


@register.simple_tag
def upstream(url, xpath, *replacements):
    """
    If Leprikón is intended to look like another website (the main website of the organization),
    use this tag to include html snippet from the other site to always stay aligned with it.

    Following example includes tag <nav> (with all it's content) from https://example.com:

        {% load cache leprikon_tags %}
        {% cache 300 menu %}{% upstream 'https://example.com/' '//nav' %}{% endcache %}
        {% cache 300 menu %}{% upstream 'https://example.com/' '//nav' '|<br>|<br/>|' %}{% endcache %}
    """
    try:
        cache = caches["upstream_pages"]
    except InvalidCacheBackendError:
        cache = caches["default"]
    try:
        content = cache.get(url)
        if content is None:
            content = requests.get(url).content
            cache.set(url, content, 60)
        for replacement in replacements:
            try:
                replacement = replacement.encode("utf-8")
                pattern, repl = replacement[1:-1].split(replacement[:1])
            except (IndexError, ValueError):
                print_exc()
            else:
                content = re.sub(pattern, repl, content)
        return mark_safe(b"".join(tostring(node) for node in fromstring(content).xpath(xpath)))
    except Exception:
        print_exc()
        return ""


class URLWithBackNode(template.base.Node):
    def __init__(self, original_node):
        self.original_node = original_node

    def render(self, context):
        return _url_with_back(
            self.original_node.render(context),
            current_url(context),
        )


@register.tag
def url_with_back(parser, token):
    """
    Returns an absolute URL as built-in tag url does,
    but adds parameter back with current url.
    """
    return URLWithBackNode(template.defaulttags.url(parser, token))


@register.simple_tag(takes_context=True)
def query_string(context, key, value):
    get = context["request"].GET.copy()
    get[key] = value
    return get.urlencode()


@register.simple_tag
def font(name):
    return finders.find(name)


@register.inclusion_tag("admin/change_list_results.html")
def css_result_list(cl):
    context = _result_list(cl)
    if hasattr(cl.model_admin, "get_css"):
        for result, obj in zip(context["results"], cl.result_list):
            result.css = cl.model_admin.get_css(obj)
    return context
