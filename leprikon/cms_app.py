from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.utils.translation import ugettext_lazy as _

from cms.app_base import CMSApp
from cms.apphook_pool import apphook_pool

from .menu import LeprikonMenu
from .urls import urlpatterns


class LeprikonApp(CMSApp):
    name = _('Leprikon')
    urls = [urlpatterns]
    app_name = 'leprikon'
    menus = [LeprikonMenu]

apphook_pool.register(LeprikonApp)

