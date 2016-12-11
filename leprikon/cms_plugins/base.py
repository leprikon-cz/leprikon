from __future__ import unicode_literals

from cms.plugin_base import CMSPluginBase
from collections import namedtuple

from ..models.schoolyear import SchoolYear


Group = namedtuple('Group', ('group', 'objects'))


class ListPluginBase(CMSPluginBase):
    def get_school_year(self, context, instance):
        return (
            instance.school_year
            or getattr(context['request'], 'school_year', None)
            or SchoolYear.objects.get_current()
        )

