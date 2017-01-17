from __future__ import unicode_literals

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import ugettext as _

from ..forms.leaders import LeaderFilterForm
from ..models.roles import (
    FilteredLeaderListPlugin, Leader, LeaderListPlugin, LeaderPlugin,
)
from .base import ListPluginBase


@plugin_pool.register_plugin
class LeprikonLeaderPlugin(CMSPluginBase):
    module  = _('Leprikon')
    name    = _('Leader')
    model   = LeaderPlugin
    cache   = False
    text_enabled = True
    raw_id_fields = ('leader',)

    def get_render_template(self, context, instance, placeholder):
        return 'leprikon/leader/%s.html' % instance.template



@plugin_pool.register_plugin
class LeprikonLeaderListPlugin(ListPluginBase):
    module  = _('Leprikon')
    name    = _('Leader list')
    model   = LeaderListPlugin
    cache   = False
    text_enabled = True
    filter_horizontal = ('age_groups', 'groups', 'leaders')

    def render(self, context, instance, placeholder):
        leaders = Leader.objects.all()
        if instance.course:
            leaders = leaders.filter(courses=instance.course)
        if instance.event:
            leaders = leaders.filter(events=instance.event)
        if instance.course is None and instance.event is None:
            leaders = self.get_school_year(context, instance).leaders.all()

        context.update({
            'leaders':        leaders,
            'instance':     instance,
            'placeholder':  placeholder,
        })
        return context

    def get_render_template(self, context, instance, placeholder):
        return 'leprikon/leader_list/%s.html' % instance.template



@plugin_pool.register_plugin
class LeprikonFilteredLeaderListPlugin(ListPluginBase):
    module  = _('Leprikon')
    name    = _('Leader list with search form')
    model   = FilteredLeaderListPlugin
    cache   = False
    render_template = 'leprikon/filtered_leader_list.html'

    def render(self, context, instance, placeholder):
        school_year = self.get_school_year(context, instance)
        form = LeaderFilterForm(
            request     = context['request'],
            school_year = school_year,
            data=context['request'].GET,
        )

        context.update({
            'school_year':  school_year,
            'form':         form,
            'leaders':      form.get_queryset(),
            'instance':     instance,
            'placeholder':  placeholder,
        })
        return context
