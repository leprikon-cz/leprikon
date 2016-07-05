from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from collections import namedtuple
from django.utils.translation import ugettext as _

from ..forms.events import EventFilterForm
from ..models.events import EventPlugin, EventListPlugin, FilteredEventListPlugin, EventGroup
from ..models.schoolyear import SchoolYear

from .base import Group, ListPluginBase


@plugin_pool.register_plugin
class LeprikonEventPlugin(CMSPluginBase):
    module  = _('Leprikon')
    name    = _('Event')
    model   = EventPlugin
    cache   = False
    text_enabled = True
    raw_id_fields = ('event',)

    def get_render_template(self, context, instance, placeholder):
        return 'leprikon/event/%s.html' % instance.template



@plugin_pool.register_plugin
class LeprikonEventListPlugin(ListPluginBase):
    module  = _('Leprikon')
    name    = _('Event list')
    model   = EventListPlugin
    cache   = False
    text_enabled = True
    filter_horizontal = ('age_groups', 'groups', 'leaders')

    def render(self, context, instance, placeholder):
        school_year = self.get_school_year(context, instance)
        events      = school_year.events.filter(event_type=instance.event_type, public=True).distinct()

        if instance.age_groups.count():
            events = events.filter(age_groups__in = instance.age_groups.all())
        if instance.leaders.count():
            events = events.filter(leaders__in    = instance.leaders.all())
        if instance.groups.count():
            events = events.filter(groups__in     = instance.groups.all())
            groups = instance.groups.all()
        else:
            groups = EventGroup.objects.all()

        context.update({
            'school_year':  school_year,
            'events':       events,
            'groups':       [
                Group(group = group, objects = events.filter(groups = group))
                for group in groups
            ],
            'instance':     instance,
            'placeholder':  placeholder,
        })
        return context

    def get_render_template(self, context, instance, placeholder):
        return 'leprikon/event_list/%s.html' % instance.template



@plugin_pool.register_plugin
class LeprikonFilteredEventListPlugin(ListPluginBase):
    module  = _('Leprikon')
    name    = _('Event list with filter form')
    model   = FilteredEventListPlugin
    cache   = False
    render_template = 'leprikon/filtered_event_list.html'

    def render(self, context, instance, placeholder):
        school_year = self.get_school_year(context, instance)
        form = EventFilterForm(
            request     = context['request'],
            school_year = school_year,
            event_types = instance.event_types.all(),
            data=context['request'].GET,
        )
        context.update({
            'school_year':  school_year,
            'form':         form,
            'events':       form.get_queryset(),
            'instance':     instance,
            'placeholder':  placeholder,
        })
        return context

