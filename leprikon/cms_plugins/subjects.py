from __future__ import unicode_literals

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import ugettext as _

from ..forms.subjects import SubjectFilterForm
from ..models.subjects import (
    FilteredSubjectListPlugin, SubjectListPlugin, SubjectPlugin,
)
from .base import Group, ListPluginBase


@plugin_pool.register_plugin
class LeprikonSubjectPlugin(CMSPluginBase):
    module  = _('Leprikon')
    name    = _('Subject')
    model   = SubjectPlugin
    cache   = False
    text_enabled = True
    raw_id_fields = ('subject',)

    def get_render_template(self, context, instance, placeholder):
        return 'cms/leprikon/subject/%s.html' % instance.template



@plugin_pool.register_plugin
class LeprikonSubjectListPlugin(ListPluginBase):
    module  = _('Leprikon')
    name    = _('Subject list')
    model   = SubjectListPlugin
    cache   = False
    text_enabled = True
    filter_horizontal = ('age_groups', 'groups', 'leaders')

    def render(self, context, instance, placeholder):
        school_year = self.get_school_year(context, instance)
        subjects    = school_year.subjects.filter(subject_type=instance.subject_type, public=True).distinct()

        if instance.age_groups.count():
            subjects = subjects.filter(age_groups__in = instance.age_groups.all())
        if instance.leaders.count():
            subjects = subjects.filter(leaders__in    = instance.leaders.all())
        if instance.groups.count():
            subjects = subjects.filter(groups__in     = instance.groups.all())
            groups = instance.groups.all()
        else:
            groups = instance.subject_type.groups.objects.all()

        context.update({
            'school_year':  school_year,
            'subjects':     subjects,
            'groups':       (
                Group(group = group, objects = subjects.filter(groups=group))
                for group in groups
            ),
            'instance':     instance,
            'placeholder':  placeholder,
        })
        return context

    def get_render_template(self, context, instance, placeholder):
        return 'cms/leprikon/subject_list/%s.html' % instance.template



@plugin_pool.register_plugin
class LeprikonFilteredSubjectListPlugin(ListPluginBase):
    module  = _('Leprikon')
    name    = _('Subject list with search form')
    model   = FilteredSubjectListPlugin
    cache   = False
    render_template = 'leprikon/filtered_subject_list.html'

    def render(self, context, instance, placeholder):
        school_year = self.get_school_year(context, instance)
        form = SubjectFilterForm(
            request     = context['request'],
            subject_type= instance.subject_type,
            school_year = school_year,
            data=context['request'].GET,
        )
        context.update({
            'school_year':  school_year,
            'form':         form,
            'subjects':     form.get_queryset(),
            'instance':     instance,
            'placeholder':  placeholder,
        })
        return context

