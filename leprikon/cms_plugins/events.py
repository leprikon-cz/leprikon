from cms.plugin_pool import plugin_pool
from django.utils.translation import ugettext as _

from ..models.events import (
    EventListPlugin, EventPlugin, FilteredEventListPlugin,
)
from .base import LeprikonPluginBase


@plugin_pool.register_plugin
class LeprikonEventPlugin(LeprikonPluginBase):
    name    = _('Event')
    model   = EventPlugin
    raw_id_fields = ('event',)

    def get_render_template(self, context, instance, placeholder):
        return 'leprikon/cms/event/%s.html' % instance.template


@plugin_pool.register_plugin
class LeprikonEventListPlugin(LeprikonPluginBase):
    name    = _('Event list')
    model   = EventListPlugin
    filter_horizontal = ('age_groups', 'groups', 'leaders')

    def get_render_template(self, context, instance, placeholder):
        return 'leprikon/cms/event_list/%s.html' % instance.template


@plugin_pool.register_plugin
class LeprikonFilteredEventListPlugin(LeprikonPluginBase):
    name    = _('Event list with search form')
    model   = FilteredEventListPlugin
    render_template = 'leprikon/cms/event_list_filtered.html'
