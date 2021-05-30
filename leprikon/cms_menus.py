from cms.menu_bases import CMSAttachMenu
from django.db.models.signals import post_delete, post_save
from django.urls import NoReverseMatch, reverse
from django.utils.translation import ugettext_lazy as _
from menus.base import Menu, Modifier, NavigationNode
from menus.menu_pool import menu_pool
from social_django.context_processors import backends

from .models.subjects import SubjectType
from .utils import current_url, first_upper, url_with_back


@menu_pool.register_menu
class LeprikonMenu(CMSAttachMenu):
    name = _("Leprikon")

    def get_nodes(self, request):
        """
        This method is used to build the menu tree.
        """
        try:
            nodes = []
            nodes.append(
                NavigationNode(
                    _("Summary"),
                    reverse("leprikon:summary"),
                    len(nodes),
                    attr={"visible_for_anonymous": False},
                )
            )
            nodes.append(
                NavigationNode(
                    _("Reports"),
                    reverse("leprikon:report_list"),
                    len(nodes),
                    attr={"require_staff": True},
                )
            )
            nodes.append(
                NavigationNode(
                    _("Leader"),
                    reverse("leprikon:leader_summary"),
                    len(nodes),
                    attr={"require_leader": True},
                )
            )
            for subject_type in SubjectType.objects.all():
                nodes.append(
                    NavigationNode(
                        first_upper(_("My {subject_type}").format(subject_type=subject_type.plural)),
                        reverse("leprikon:subject_list_mine", kwargs={"subject_type": subject_type.slug}),
                        len(nodes),
                        attr={"require_leader": True},
                    )
                )
            nodes.append(
                NavigationNode(
                    _("Alternating"),
                    reverse("leprikon:alternating"),
                    len(nodes),
                    attr={"require_leader": True},
                )
            )
            nodes.append(
                NavigationNode(
                    _("Timesheets"),
                    reverse("leprikon:timesheet_list"),
                    len(nodes),
                    attr={"require_leader": True},
                )
            )
            nodes.append(
                NavigationNode(
                    _("Messages"),
                    reverse("leprikon:message_list"),
                    len(nodes),
                    attr={"visible_for_anonymous": False},
                )
            )
            nodes.append(
                NavigationNode(
                    _("Registrations"),
                    reverse("leprikon:registration_list"),
                    len(nodes),
                    attr={"visible_for_anonymous": False},
                )
            )
            nodes.append(
                NavigationNode(
                    _("Payments"),
                    reverse("leprikon:payment_list"),
                    len(nodes),
                    attr={"visible_for_anonymous": False},
                )
            )
            nodes.append(
                NavigationNode(
                    _("Donations"),
                    reverse("leprikon:donation_list"),
                    len(nodes),
                    attr={"visible_for_anonymous": False},
                )
            )
            nodes.append(
                NavigationNode(
                    _("Participants"),
                    reverse("leprikon:participant_list"),
                    len(nodes),
                    attr={"visible_for_anonymous": False},
                )
            )
            nodes.append(
                NavigationNode(
                    _("Billing information"),
                    reverse("leprikon:billing_info_list"),
                    len(nodes),
                    attr={"visible_for_anonymous": False},
                )
            )
            return nodes
        except NoReverseMatch:
            return []


@menu_pool.register_menu
class UserMenu(Menu):
    def get_nodes(self, request):
        """
        This method is used to build the menu tree.
        """
        nodes = []

        # anonymous user
        nodes.append(
            NavigationNode(
                _("Log in"),
                reverse("leprikon:user_login"),
                len(nodes),
                attr={"visible_for_authenticated": False, "add_url_back": True},
            )
        )
        nodes.append(
            NavigationNode(
                _("Create account"),
                reverse("leprikon:user_create"),
                len(nodes),
                attr={"visible_for_authenticated": False, "add_url_back": True},
            )
        )
        nodes.append(
            NavigationNode(
                _("Reset password"),
                reverse("leprikon:password_reset"),
                len(nodes),
                attr={"visible_for_authenticated": False, "add_url_back": True},
            )
        )

        # user settings
        nodes.append(
            NavigationNode(
                _("Change user details"),
                reverse("leprikon:user_update"),
                len(nodes),
                attr={"visible_for_anonymous": False, "add_url_back": True},
            )
        )
        nodes.append(
            NavigationNode(
                _("Change e-mail"),
                reverse("leprikon:user_email"),
                len(nodes),
                attr={"visible_for_anonymous": False, "add_url_back": True},
            )
        )
        nodes.append(
            NavigationNode(
                _("Change password"),
                reverse("leprikon:user_password"),
                len(nodes),
                attr={"visible_for_anonymous": False, "add_url_back": True},
            )
        )
        nodes.append(
            NavigationNode(
                _("Link with Google account"),
                reverse("social:begin", args=("google-oauth2",)),
                len(nodes),
                attr={
                    "visible_for_anonymous": False,
                    "add_url_back": True,
                    "social_backend": "google-oauth2",
                    "social_btn": "google",
                },
            )
        )
        nodes.append(
            NavigationNode(
                _("Link with Facebook account"),
                reverse("social:begin", args=("facebook",)),
                len(nodes),
                attr={
                    "visible_for_anonymous": False,
                    "add_url_back": True,
                    "social_backend": "facebook",
                    "social_btn": "facebook",
                },
            )
        )
        nodes.append(
            NavigationNode(
                _("Log out"),
                reverse("leprikon:user_logout"),
                len(nodes),
                attr={"visible_for_anonymous": False},
            )
        )
        return nodes


@menu_pool.register_modifier
class LeprikonModifier(Modifier):
    def modify(self, request, nodes, namespace, root_id, post_cut, breadcrumb):
        if post_cut or breadcrumb:
            return nodes
        final = []
        backends_not_associated = backends(request)["backends"]["not_associated"]
        for node in nodes:
            show = True
            if node.attr.get("require_leader", False):
                if not request.leader or not request.leader.school_years.filter(id=request.school_year.id).exists():
                    show = False
            if node.attr.get("require_staff", False) and not request.user.is_staff:
                show = False
            if node.attr.get("social_backend") and (node.attr.get("social_backend") not in backends_not_associated):
                show = False
            if show:
                if node.attr.get("add_url_back", False):
                    node.url = url_with_back(node.url, current_url(request))
                final.append(node)
            else:
                if node.parent and node in node.parent.children:
                    node.parent.children.remove(node)
                continue
        return final


@menu_pool.register_modifier
class NamespaceModifier(Modifier):
    def modify(self, request, nodes, namespace, root_id, post_cut, breadcrumb):
        if namespace and not (post_cut or breadcrumb):
            namespaces = namespace.split(",")
            return [node for node in nodes if node.namespace.split(":")[0] in namespaces]
        else:
            return nodes


# clear menu cache with each reload
try:
    menu_pool.clear()
except Exception:
    # menu_pool.clear() uses database,
    # but this code may be executed
    # before the database is created
    pass


def invalidate_menu_cache(sender, **kwargs):
    menu_pool.clear()


post_save.connect(invalidate_menu_cache, sender=SubjectType)
post_delete.connect(invalidate_menu_cache, sender=SubjectType)
