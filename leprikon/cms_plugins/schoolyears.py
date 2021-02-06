from cms.plugin_pool import plugin_pool
from django.utils.translation import ugettext as _

from ..models.schoolyear import SchoolYearBlockPlugin
from .base import LeprikonPluginBase


@plugin_pool.register_plugin
class LeprikonSchoolYearBlockPlugin(LeprikonPluginBase):
    name = _("School year block")
    model = SchoolYearBlockPlugin
    allow_children = True
    filter_horizontal = ("school_years",)
    render_template = "leprikon/cms/school_year_block.html"
