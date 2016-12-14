from __future__ import unicode_literals

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import ugettext as _

from ..forms.clubs import ClubFilterForm
from ..models.clubs import (
    ClubGroup, ClubListPlugin, ClubPlugin, FilteredClubListPlugin,
)
from .base import Group, ListPluginBase


@plugin_pool.register_plugin
class LeprikonClubPlugin(CMSPluginBase):
    module  = _('Leprikon')
    name    = _('Club')
    model   = ClubPlugin
    cache   = False
    text_enabled = True
    raw_id_fields = ('club',)

    def get_render_template(self, context, instance, placeholder):
        return 'leprikon/club/%s.html' % instance.template



@plugin_pool.register_plugin
class LeprikonClubListPlugin(ListPluginBase):
    module  = _('Leprikon')
    name    = _('Club list')
    model   = ClubListPlugin
    cache   = False
    text_enabled = True
    filter_horizontal = ('age_groups', 'groups', 'leaders')

    def render(self, context, instance, placeholder):
        school_year = self.get_school_year(context, instance)
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



@plugin_pool.register_plugin
class LeprikonFilteredClubListPlugin(ListPluginBase):
    module  = _('Leprikon')
    name    = _('Club list with search form')
    model   = FilteredClubListPlugin
    cache   = False
    render_template = 'leprikon/filtered_club_list.html'

    def render(self, context, instance, placeholder):
        school_year = self.get_school_year(context, instance)
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

