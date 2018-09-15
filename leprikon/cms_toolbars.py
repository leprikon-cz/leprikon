from cms.cms_toolbars import ADMIN_MENU_IDENTIFIER
from cms.toolbar.items import SubMenu
from cms.toolbar_base import CMSToolbar
from cms.toolbar_pool import toolbar_pool
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _


@toolbar_pool.register
class LeprikonToolbar(CMSToolbar):

    def populate(self):
        # Articles item in main menu
        admin_menu = self.toolbar.get_or_create_menu(ADMIN_MENU_IDENTIFIER)
        position = admin_menu.get_alphabetical_insert_position(_('Leprikon'), SubMenu)
        url = reverse('admin:app_list', args=('leprikon',))
        admin_menu.add_sideframe_item(_('Leprikon'), url=url, position=position)
