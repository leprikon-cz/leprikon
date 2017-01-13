from __future__ import unicode_literals

from cms.menu_bases import CMSAttachMenu
from django.core.urlresolvers import reverse
from django.db.models.signals import post_delete, post_save
from django.utils.translation import ugettext_lazy as _
from menus.base import Modifier, NavigationNode
from menus.menu_pool import menu_pool

from .models.clubs import ClubType
from .models.events import EventType
from .utils import current_url, url_with_back


class LeprikonMenu(CMSAttachMenu):
    name = _('Leprikon')

    def get_nodes(self, request):
        """
        This method is used to build the menu tree.
        """
        nodes = []
        nodes.append(NavigationNode(
            _('Log in'),
            reverse('leprikon:user_login'),
            len(nodes),
            attr={'visible_for_authenticated': False, 'add_url_back': True},
        ))
        nodes.append(NavigationNode(
            _('Create account'),
            reverse('leprikon:user_create'),
            len(nodes),
            attr={'visible_for_authenticated': False},
        ))
        nodes.append(NavigationNode(
            _('Reset password'),
            reverse('leprikon:password_reset'),
            len(nodes),
            attr={'visible_for_authenticated': False},
        ))
        nodes.append(NavigationNode(
            _('Summary'),
            reverse('leprikon:summary'),
            len(nodes),
            attr={'visible_for_anonymous': False},
        ))
        nodes.append(NavigationNode(
            _('Messages'),
            reverse('leprikon:message_list'),
            len(nodes),
            attr={'visible_for_anonymous': False},
        ))
        nodes.append(NavigationNode(
            _('Registrations'),
            reverse('leprikon:registration_list'),
            len(nodes),
            attr={'visible_for_anonymous': False},
        ))
        nodes.append(NavigationNode(
            _('Participants'),
            reverse('leprikon:participant_list'),
            len(nodes),
            attr={'visible_for_anonymous': False},
        ))
        nodes.append(NavigationNode(
            _('Add participant'),
            reverse('leprikon:participant_create'),
            len(nodes),
            parent_id=len(nodes)-1,
            attr={'visible_for_anonymous': False, 'add_url_back': True},
        ))
        nodes.append(NavigationNode(
            _('Add parent'),
            reverse('leprikon:parent_create'),
            len(nodes),
            parent_id=len(nodes)-2,
            attr={'visible_for_anonymous': False, 'add_url_back': True},
        ))
        nodes.append(NavigationNode(
            _('My Clubs'),
            reverse('leprikon:club_list_mine'),
            len(nodes),
            attr={'require_leader': True},
        ))
        nodes.append(NavigationNode(
            _('Alternating'),
            reverse('leprikon:club_alternating'),
            len(nodes),
            parent_id=len(nodes)-1,
            attr={'require_leader': True},
        ))
        for club_type in ClubType.objects.all():
            nodes.append(NavigationNode(
                club_type.name,
                reverse('leprikon:club_list', kwargs={'club_type': club_type.slug}),
                len(nodes),
            ))
        nodes.append(NavigationNode(
            _('My Events'),
            reverse('leprikon:event_list_mine'),
            len(nodes),
            attr={'require_leader': True},
        ))
        for event_type in EventType.objects.all():
            nodes.append(NavigationNode(
                event_type.name,
                reverse('leprikon:event_list', kwargs={'event_type': event_type.slug}),
                len(nodes),
            ))
        nodes.append(NavigationNode(
            _('Leaders'),
            reverse('leprikon:leader_list'),
            len(nodes),
        ))
        nodes.append(NavigationNode(
            _('Timesheets'),
            reverse('leprikon:timesheet_list'),
            len(nodes),
            attr={'require_leader': True},
        ))
        nodes.append(NavigationNode(
            _('Add new entry'),
            reverse('leprikon:timesheetentry_create'),
            len(nodes),
            parent_id=len(nodes)-1,
            attr={'require_leader': True, 'add_url_back': True},
        ))
        nodes.append(NavigationNode(
            _('Reports'),
            reverse('leprikon:report_list'),
            len(nodes),
            attr={'require_staff': True},
        ))
        nodes.append(NavigationNode(
            _('Terms and Conditions'),
            reverse('leprikon:terms_conditions'),
            len(nodes),
        ))
        nodes.append(NavigationNode(
            _('Log out'),
            reverse('leprikon:user_logout'),
            len(nodes),
            attr={'visible_for_anonymous': False},
        ))
        return nodes

menu_pool.register_menu(LeprikonMenu)



class LeprikonModifier(Modifier):
    def modify(self, request, nodes, namespace, root_id, post_cut, breadcrumb):
        if post_cut or breadcrumb:
            return nodes
        final = []
        for node in nodes:
            if ((node.attr.get('require_leader', False) and not request.leader)
            or  (node.attr.get('require_staff', False)  and not request.user.is_staff)):
                if node.parent and node in node.parent.children:
                    node.parent.children.remove(node)
                continue
            else:
                if node.attr.get('add_url_back', False):
                    node.url = url_with_back(node.url, current_url(request))
                final.append(node)
        return final

menu_pool.register_modifier(LeprikonModifier)


# clear menu cache with each reload
try:
    menu_pool.clear()
except:
    # menu_pool.clear() uses database,
    # but this code may be executed
    # before the database is created
    pass


def invalidate_menu_cache(sender, **kwargs):
    menu_pool.clear()

post_save.connect(invalidate_menu_cache, sender=EventType)
post_delete.connect(invalidate_menu_cache, sender=EventType)

