from __future__ import unicode_literals

from cms.app_base import CMSApp
from cms.apphook_pool import apphook_pool
from django.utils.translation import ugettext_lazy as _

from .menu import LeprikonMenu
from .urls import urlpatterns


@apphook_pool.register
class LeprikonApp(CMSApp):
    name = _('Leprikon')
    urls = [urlpatterns]
    app_name = 'leprikon'
    menus = [LeprikonMenu]
