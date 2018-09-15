from cms.plugin_pool import plugin_pool
from django.utils.translation import ugettext as _

from ..models.courses import (
    CourseListPlugin, CoursePlugin, FilteredCourseListPlugin,
)
from .base import LeprikonPluginBase


@plugin_pool.register_plugin
class LeprikonCoursePlugin(LeprikonPluginBase):
    name    = _('Course')
    model   = CoursePlugin
    raw_id_fields = ('course',)

    def get_render_template(self, context, instance, placeholder):
        return 'leprikon/cms/course/%s.html' % instance.template


@plugin_pool.register_plugin
class LeprikonCourseListPlugin(LeprikonPluginBase):
    name    = _('Course list')
    model   = CourseListPlugin
    filter_horizontal = ('age_groups', 'groups', 'leaders')

    def get_render_template(self, context, instance, placeholder):
        return 'leprikon/cms/course_list/%s.html' % instance.template


@plugin_pool.register_plugin
class LeprikonFilteredCourseListPlugin(LeprikonPluginBase):
    name    = _('Course list with search form')
    model   = FilteredCourseListPlugin
    render_template = 'leprikon/cms/course_list_filtered.html'
