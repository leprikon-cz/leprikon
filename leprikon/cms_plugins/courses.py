from __future__ import unicode_literals

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import ugettext as _

from ..forms.courses import CourseFilterForm
from ..models.courses import (
    CourseGroup, CourseListPlugin, CoursePlugin, FilteredCourseListPlugin,
)
from .base import Group, ListPluginBase


@plugin_pool.register_plugin
class LeprikonCoursePlugin(CMSPluginBase):
    module  = _('Leprikon')
    name    = _('Course')
    model   = CoursePlugin
    cache   = False
    text_enabled = True
    raw_id_fields = ('course',)

    def get_render_template(self, context, instance, placeholder):
        return 'leprikon/course/%s.html' % instance.template



@plugin_pool.register_plugin
class LeprikonCourseListPlugin(ListPluginBase):
    module  = _('Leprikon')
    name    = _('Course list')
    model   = CourseListPlugin
    cache   = False
    text_enabled = True
    filter_horizontal = ('age_groups', 'groups', 'leaders')

    def render(self, context, instance, placeholder):
        school_year = self.get_school_year(context, instance)
        courses     = school_year.courses.filter(course_type=instance.course_type, public=True).distinct()

        if instance.age_groups.count():
            courses = courses.filter(age_groups__in = instance.age_groups.all())
        if instance.leaders.count():
            courses = courses.filter(leaders__in    = instance.leaders.all())
        if instance.groups.count():
            courses = courses.filter(groups__in     = instance.groups.all())
            groups = instance.groups.all()
        else:
            groups = CourseGroup.objects.all()

        context.update({
            'school_year':  school_year,
            'courses':      courses,
            'groups':       [
                Group(group = group, objects = courses.filter(groups=group))
                for group in groups
            ],
            'instance':     instance,
            'placeholder':  placeholder,
        })
        return context

    def get_render_template(self, context, instance, placeholder):
        return 'leprikon/course_list/%s.html' % instance.template



@plugin_pool.register_plugin
class LeprikonFilteredCourseListPlugin(ListPluginBase):
    module  = _('Leprikon')
    name    = _('Course list with search form')
    model   = FilteredCourseListPlugin
    cache   = False
    render_template = 'leprikon/filtered_course_list.html'

    def render(self, context, instance, placeholder):
        school_year = self.get_school_year(context, instance)
        form = CourseFilterForm(
            request     = context['request'],
            school_year = school_year,
            course_types= instance.course_types.all(),
            data=context['request'].GET,
        )
        context.update({
            'school_year':  school_year,
            'form':         form,
            'courses':      form.get_queryset(),
            'instance':     instance,
            'placeholder':  placeholder,
        })
        return context

