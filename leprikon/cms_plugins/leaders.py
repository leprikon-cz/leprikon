from cms.plugin_pool import plugin_pool
from django.utils.translation import ugettext as _

from ..models.roles import FilteredLeaderListPlugin, LeaderListPlugin, LeaderPlugin
from .base import LeprikonPluginBase


@plugin_pool.register_plugin
class LeprikonLeaderPlugin(LeprikonPluginBase):
    name = _("Leader")
    model = LeaderPlugin
    raw_id_fields = ("leader",)

    def get_render_template(self, context, instance, placeholder):
        return "leprikon/cms/leader/%s.html" % instance.template


@plugin_pool.register_plugin
class LeprikonLeaderListPlugin(LeprikonPluginBase):
    name = _("Leader list")
    model = LeaderListPlugin

    def get_render_template(self, context, instance, placeholder):
        return "leprikon/cms/leader_list/%s.html" % instance.template


@plugin_pool.register_plugin
class LeprikonFilteredLeaderListPlugin(LeprikonPluginBase):
    name = _("Leader list with search form")
    model = FilteredLeaderListPlugin
    render_template = "leprikon/cms/leader_list_filtered.html"
