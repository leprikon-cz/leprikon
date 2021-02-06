from cms.plugin_pool import plugin_pool
from django.utils.translation import ugettext as _

from ..models.orderables import FilteredOrderableListPlugin, OrderableListPlugin, OrderablePlugin
from .base import LeprikonPluginBase


@plugin_pool.register_plugin
class LeprikonOrderablePlugin(LeprikonPluginBase):
    name = _("Orderable event")
    model = OrderablePlugin
    raw_id_fields = ("orderable",)

    def get_render_template(self, context, instance, placeholder):
        return "leprikon/cms/orderable/%s.html" % instance.template


@plugin_pool.register_plugin
class LeprikonOrderableListPlugin(LeprikonPluginBase):
    name = _("Orderable list")
    model = OrderableListPlugin
    filter_horizontal = ("age_groups", "target_groups", "groups", "leaders")

    def get_render_template(self, context, instance, placeholder):
        return "leprikon/cms/orderable_list/%s.html" % instance.template


@plugin_pool.register_plugin
class LeprikonFilteredOrderableListPlugin(LeprikonPluginBase):
    name = _("Orderable list with search form")
    model = FilteredOrderableListPlugin
    render_template = "leprikon/cms/orderable_list_filtered.html"
