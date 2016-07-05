from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from cms.plugin_base import CMSPluginBase
from collections import namedtuple

from ..models import SchoolYear


Group = namedtuple('Group', ('group', 'objects'))


class ListPluginBase(CMSPluginBase):
    def get_school_year(self, context, instance):
        return (
            instance.school_year
            or getattr(context['request'], 'school_year', None)
            or SchoolYear.objects.get_current()
        )

