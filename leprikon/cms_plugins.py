from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from collections import namedtuple
from django.utils.translation import ugettext as _

from .forms.clubs import ClubFilterForm
from .forms.events import EventFilterForm
from .models import (
    LeprikonClubListPlugin, LeprikonFilteredClubListPlugin, ClubGroup,
    LeprikonEventListPlugin, LeprikonFilteredEventListPlugin, EventGroup,
)


Group = namedtuple('Group', ('group', 'objects'))



class LeprikonClubListPlugin(CMSPluginBase):
    module  = _('Leprikon')
    name    = _('Club list')
    model   = LeprikonClubListPlugin
    cache   = False
    text_enabled = True
    filter_horizontal = ('age_groups', 'groups', 'leaders')

    def render(self, context, instance, placeholder):
        school_year = instance.school_year or context['request'].school_year
        clubs       = school_year.clubs.filter(public=True).distinct()

        if instance.age_groups.count():
            clubs = clubs.filter(age_groups__in = instance.age_groups.all())
        if instance.leaders.count():
            clubs = clubs.filter(leaders__in    = instance.leaders.all())
        if instance.groups.count():
            clubs = clubs.filter(groups__in     = instance.groups.all())
            groups = instance.groups.all()
        else:
            groups = ClubGroup.objects.all()

        context.update({
            'school_year':  school_year,
            'clubs':        clubs,
            'groups':       [
                Group(group = group, objects = clubs.filter(groups = group))
                for group in groups
            ],
            'instance':     instance,
            'placeholder':  placeholder,
        })
        return context

    def get_render_template(self, context, instance, placeholder):
        return 'leprikon/club_list/%s.html' % instance.template



class LeprikonFilteredClubListPlugin(CMSPluginBase):
    module  = _('Leprikon')
    name    = _('Club list with filter form')
    model   = LeprikonFilteredClubListPlugin
    cache   = False
    render_template = 'leprikon/filtered_club_list.html'

    def render(self, context, instance, placeholder):
        school_year = instance.school_year or context['request'].school_year
        form = ClubFilterForm(
            request     = context['request'],
            school_year = school_year,
            data=context['request'].GET,
        )

        context.update({
            'school_year':  school_year,
            'form':         form,
            'clubs':        form.get_queryset(),
            'instance':     instance,
            'placeholder':  placeholder,
        })
        return context



class LeprikonEventListPlugin(CMSPluginBase):
    module  = _('Leprikon')
    name    = _('Event list')
    model   = LeprikonEventListPlugin
    cache   = False
    text_enabled = True
    filter_horizontal = ('age_groups', 'groups', 'leaders')

    def render(self, context, instance, placeholder):
        school_year = instance.school_year or context['request'].school_year
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



class LeprikonFilteredEventListPlugin(CMSPluginBase):
    module  = _('Leprikon')
    name    = _('Event list with filter form')
    model   = LeprikonFilteredEventListPlugin
    cache   = False
    render_template = 'leprikon/filtered_event_list.html'

    def render(self, context, instance, placeholder):
        school_year = instance.school_year or context['request'].school_year
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


plugin_pool.register_plugin(LeprikonClubListPlugin)
plugin_pool.register_plugin(LeprikonFilteredClubListPlugin)
plugin_pool.register_plugin(LeprikonEventListPlugin)
plugin_pool.register_plugin(LeprikonFilteredEventListPlugin)

