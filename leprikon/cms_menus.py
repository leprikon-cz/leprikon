from cms.menu_bases import CMSAttachMenu
from django.core.urlresolvers import NoReverseMatch, reverse
from django.db.models.signals import post_delete, post_save
from django.utils.translation import ugettext_lazy as _
from menus.base import Modifier, NavigationNode
from menus.menu_pool import menu_pool

from .models.subjects import SubjectType
from .utils import current_url, first_upper, url_with_back


@menu_pool.register_menu
class LeprikonMenu(CMSAttachMenu):
    name = _('Leprikon')

    def get_nodes(self, request):
        """
        This method is used to build the menu tree.
        """
        try:
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
                _('Reports'),
                reverse('leprikon:report_list'),
                len(nodes),
                attr={'require_staff': True},
            ))
            leader = len(nodes)
            nodes.append(NavigationNode(
                _('Leader'),
                reverse('leprikon:leader_summary'),
                len(nodes),
                attr={'require_leader': True},
            ))
            for subject_type in SubjectType.objects.all():
                nodes.append(NavigationNode(
                    first_upper(_('My {subject_type}').format(subject_type=subject_type.plural)),
                    reverse('leprikon:subject_list_mine', kwargs={'subject_type': subject_type.slug}),
                    len(nodes),
                    parent_id=leader,
                    attr={'require_leader': True},
                ))
            nodes.append(NavigationNode(
                _('Alternating'),
                reverse('leprikon:course_alternating'),
                len(nodes),
                parent_id=leader,
                attr={'require_leader': True},
            ))
            timesheets = len(nodes)
            nodes.append(NavigationNode(
                _('Timesheets'),
                reverse('leprikon:timesheet_list'),
                len(nodes),
                parent_id=leader,
                attr={'require_leader': True},
            ))
            nodes.append(NavigationNode(
                _('Add new entry'),
                reverse('leprikon:timesheetentry_create'),
                len(nodes),
                parent_id=timesheets,
                attr={'require_leader': True, 'add_url_back': True},
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
                _('Payments'),
                reverse('leprikon:payment_list'),
                len(nodes),
                attr={'visible_for_anonymous': False},
            ))
            participants = len(nodes)
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
                parent_id=participants,
                attr={'visible_for_anonymous': False, 'add_url_back': True},
            ))
            nodes.append(NavigationNode(
                _('Add parent'),
                reverse('leprikon:parent_create'),
                len(nodes),
                parent_id=participants,
                attr={'visible_for_anonymous': False, 'add_url_back': True},
            ))
            for subject_type in SubjectType.objects.all():
                nodes.append(NavigationNode(
                    first_upper(subject_type.plural),
                    reverse('leprikon:subject_list', kwargs={'subject_type': subject_type.slug}),
                    len(nodes),
                ))
            nodes.append(NavigationNode(
                _('Leaders'),
                reverse('leprikon:leader_list'),
                len(nodes),
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
        except NoReverseMatch:
            return []


@menu_pool.register_modifier
class LeprikonModifier(Modifier):
    def modify(self, request, nodes, namespace, root_id, post_cut, breadcrumb):
        if post_cut or breadcrumb:
            return nodes
        final = []
        for node in nodes:
            if (
                (node.attr.get('require_leader', False) and not request.leader) or
                (node.attr.get('require_staff', False) and not request.user.is_staff)
            ):
                if node.parent and node in node.parent.children:
                    node.parent.children.remove(node)
                continue
            else:
                if node.attr.get('add_url_back', False):
                    node.url = url_with_back(node.url, current_url(request))
                final.append(node)
        return final


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


post_save.connect(invalidate_menu_cache, sender=SubjectType)
post_delete.connect(invalidate_menu_cache, sender=SubjectType)
